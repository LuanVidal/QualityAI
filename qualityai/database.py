"""Banco SQLite local para metadados, rastreabilidade e versionamento."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class QualityDatabase:
    """Camada pequena e transacional sobre o SQLite do QualityAI."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema)

    def sync_recipe(self, metadata: dict, root: Path) -> None:
        recipe_id = str(metadata["recipe_id"])
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO recipes (
                    id, name, part_type, description, root_path,
                    preprocessing_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    part_type = excluded.part_type,
                    description = excluded.description,
                    root_path = excluded.root_path,
                    preprocessing_json = excluded.preprocessing_json,
                    updated_at = excluded.updated_at
                """,
                (
                    recipe_id,
                    str(metadata.get("name") or recipe_id),
                    str(metadata.get("part_type") or "Peça não informada"),
                    str(metadata.get("description") or ""),
                    str(Path(root).resolve()),
                    json.dumps(metadata.get("preprocessing") or {}, ensure_ascii=False),
                    str(metadata.get("created_at") or now),
                    str(metadata.get("updated_at") or now),
                ),
            )
            active = connection.execute(
                "SELECT id FROM dataset_versions WHERE recipe_id = ? AND status = 'active'",
                (recipe_id,),
            ).fetchone()
            if active is None:
                last = connection.execute(
                    "SELECT COALESCE(MAX(version_number), 0) FROM dataset_versions WHERE recipe_id = ?",
                    (recipe_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO dataset_versions
                       (recipe_id, version_number, status, created_at)
                       VALUES (?, ?, 'active', ?)""",
                    (recipe_id, int(last) + 1, now),
                )

    def list_recipes(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM recipes ORDER BY name COLLATE NOCASE"
            ).fetchall()

    def set_active_recipe(self, recipe_id: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO app_settings(key, value, updated_at)
                   VALUES ('active_recipe_id', ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value = excluded.value, updated_at = excluded.updated_at""",
                (recipe_id, utc_now()),
            )

    def active_recipe_id(self) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_settings WHERE key = 'active_recipe_id'"
            ).fetchone()
        return str(row[0]) if row else None

    def active_dataset_version_id(self, recipe_id: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM dataset_versions WHERE recipe_id = ? AND status = 'active'",
                (recipe_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError(f"Receita sem versão ativa de dataset: {recipe_id}")
        return int(row[0])

    def register_image(
        self,
        recipe_id: str,
        file_path: Path,
        label: str,
        source: str,
        width: int | None = None,
        height: int | None = None,
    ) -> str:
        image_id = uuid.uuid4().hex
        resolved = Path(file_path).resolve()
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM image_samples WHERE file_path = ?", (str(resolved),)
            ).fetchone()
        if existing is not None:
            return str(existing[0])
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved.is_file() else None
        with self.transaction() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO image_samples
                   (id, recipe_id, dataset_version_id, label, file_path, source,
                    width, height, sha256, captured_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    image_id,
                    recipe_id,
                    self.active_dataset_version_id(recipe_id),
                    label,
                    str(resolved),
                    source,
                    width,
                    height,
                    digest,
                    utc_now(),
                ),
            )
            row = connection.execute(
                "SELECT id FROM image_samples WHERE file_path = ?", (str(resolved),)
            ).fetchone()
        return str(row[0])

    def mark_image_deleted(self, file_path: Path) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE image_samples SET deleted_at = ? WHERE file_path = ?",
                (utc_now(), str(Path(file_path).resolve())),
            )

    def image_id_for_path(self, file_path: Path) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM image_samples WHERE file_path = ?",
                (str(Path(file_path).resolve()),),
            ).fetchone()
        return str(row[0]) if row else None

    def archive_dataset(self, recipe_id: str) -> None:
        now = utc_now()
        with self.transaction() as connection:
            active = connection.execute(
                """SELECT id, version_number FROM dataset_versions
                   WHERE recipe_id = ? AND status = 'active'""",
                (recipe_id,),
            ).fetchone()
            if active:
                connection.execute(
                    "UPDATE dataset_versions SET status = 'archived', closed_at = ? WHERE id = ?",
                    (now, int(active["id"])),
                )
                connection.execute(
                    "UPDATE image_samples SET deleted_at = COALESCE(deleted_at, ?) WHERE dataset_version_id = ?",
                    (now, int(active["id"])),
                )
                next_version = int(active["version_number"]) + 1
            else:
                next_version = 1
            connection.execute(
                """INSERT INTO dataset_versions
                   (recipe_id, version_number, status, created_at)
                   VALUES (?, ?, 'active', ?)""",
                (recipe_id, next_version, now),
            )
            connection.execute(
                """UPDATE model_versions SET active = 0, archived_at = COALESCE(archived_at, ?)
                   WHERE recipe_id = ? AND active = 1""",
                (now, recipe_id),
            )

    def log_event(self, recipe_id: str | None, event_type: str, details: dict) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO audit_events(recipe_id, event_type, details_json, created_at)
                   VALUES (?, ?, ?, ?)""",
                (recipe_id, event_type, json.dumps(details, ensure_ascii=False), utc_now()),
            )

    def record_training_and_model(
        self,
        recipe_id: str,
        *,
        version: str,
        model_path: Path,
        total_images: int,
        folds: int,
        metrics: dict,
        confidence_threshold: float,
    ) -> None:
        training_id = uuid.uuid4().hex
        dataset_version_id = self.active_dataset_version_id(recipe_id)
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO training_runs
                   (id, recipe_id, dataset_version_id, status, total_images,
                    folds, metrics_json, finished_at)
                   VALUES (?, ?, ?, 'completed', ?, ?, ?, ?)""",
                (
                    training_id,
                    recipe_id,
                    dataset_version_id,
                    total_images,
                    folds,
                    json.dumps(metrics, ensure_ascii=False),
                    now,
                ),
            )
            connection.execute(
                "UPDATE model_versions SET active = 0, archived_at = ? WHERE recipe_id = ? AND active = 1",
                (now, recipe_id),
            )
            connection.execute(
                """INSERT INTO model_versions
                   (id, recipe_id, dataset_version_id, training_run_id, file_path,
                    model_type, confidence_threshold, metrics_json, active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    version,
                    recipe_id,
                    dataset_version_id,
                    training_id,
                    str(Path(model_path).resolve()),
                    "mobilenet_v3_small_frozen_logistic",
                    confidence_threshold,
                    json.dumps(metrics, ensure_ascii=False),
                    now,
                ),
            )

    def record_inspection(
        self,
        recipe_id: str,
        *,
        model_id: str | None,
        file_path: Path,
        predicted_label: str,
        confidence: float,
        requires_review: bool,
    ) -> str:
        inspection_id = uuid.uuid4().hex
        with self.transaction() as connection:
            if model_id is not None:
                known_model = connection.execute(
                    "SELECT 1 FROM model_versions WHERE id = ?", (model_id,)
                ).fetchone()
                if known_model is None:
                    model_id = None
            connection.execute(
                """INSERT INTO inspections
                   (id, recipe_id, model_id, file_path, predicted_label,
                    confidence, requires_review, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    inspection_id,
                    recipe_id,
                    model_id,
                    str(Path(file_path).resolve()),
                    predicted_label,
                    float(confidence),
                    int(requires_review),
                    utc_now(),
                ),
            )
        return inspection_id

    def record_review(
        self,
        inspection_id: str,
        human_label: str,
        corrected: bool,
        dataset_image_id: str | None = None,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO human_reviews
                   (id, inspection_id, human_label, corrected, dataset_image_id, reviewed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    uuid.uuid4().hex,
                    inspection_id,
                    human_label,
                    int(corrected),
                    dataset_image_id,
                    utc_now(),
                ),
            )
