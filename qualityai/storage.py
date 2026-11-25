"""Armazenamento local das imagens e dos metadados do projeto."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from qualityai.config import ProjectPaths, SUPPORTED_EXTENSIONS
from qualityai.database import QualityDatabase


VALID_LABELS = ("ok", "nok")


@dataclass(frozen=True)
class RecipeInfo:
    recipe_id: str
    name: str
    part_type: str
    description: str
    root: Path


class RecipeCatalog:
    """Descobre e seleciona receitas independentes armazenadas no notebook."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.root.parent / "settings.json"
        self.database = QualityDatabase(self.root.parent / "qualityai.db")
        if not any(path.is_dir() for path in self.root.iterdir()):
            self._create_default()
        else:
            self._migrate_existing_recipes()

    def _create_default(self) -> None:
        store = DatasetStore(ProjectPaths(self.root / "projeto-principal"), self.database)
        store.update_metadata(
            recipe_id="projeto-principal",
            name="Projeto principal",
            part_type="Peça demonstrativa",
            description="Receita inicial de inspeção visual OK/NOK.",
        )
        self.activate("projeto-principal")

    def _migrate_existing_recipes(self) -> None:
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            metadata_path = directory / "project.json"
            if not metadata_path.is_file():
                continue
            store = DatasetStore(ProjectPaths(directory), self.database)
            metadata = store.read_metadata()
            missing: dict[str, str] = {}
            if not metadata.get("recipe_id"):
                missing["recipe_id"] = directory.name
            if not metadata.get("part_type"):
                missing["part_type"] = "Peça não informada"
            if "description" not in metadata:
                missing["description"] = ""
            if missing:
                store.update_metadata(**missing)
            else:
                self.database.sync_recipe(store.read_metadata(), directory)
            for path, label in store.all_labeled_images():
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                height, width = image.shape[:2] if image is not None else (None, None)
                self.database.register_image(
                    str(store.read_metadata()["recipe_id"]),
                    path,
                    label,
                    "migration",
                    width,
                    height,
                )

    def list_recipes(self) -> list[RecipeInfo]:
        return [
            RecipeInfo(
                recipe_id=str(row["id"]),
                name=str(row["name"]),
                part_type=str(row["part_type"]),
                description=str(row["description"]),
                root=Path(str(row["root_path"])),
            )
            for row in self.database.list_recipes()
        ]

    def active_recipe_id(self) -> str:
        recipes = self.list_recipes()
        if not recipes:
            self._create_default()
            recipes = self.list_recipes()
        selected = self.database.active_recipe_id() or ""
        if not selected:
            try:
                settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
                selected = str(settings.get("active_recipe_id", ""))
            except (OSError, json.JSONDecodeError):
                selected = ""
        valid_ids = {recipe.recipe_id for recipe in recipes}
        return selected if selected in valid_ids else recipes[0].recipe_id

    def activate(self, recipe_id: str) -> DatasetStore:
        recipe = self.get(recipe_id)
        self.settings_path.write_text(
            json.dumps({"active_recipe_id": recipe.recipe_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.database.set_active_recipe(recipe.recipe_id)
        return DatasetStore(ProjectPaths(recipe.root), self.database)

    def active_store(self) -> DatasetStore:
        return self.activate(self.active_recipe_id())

    def get(self, recipe_id: str) -> RecipeInfo:
        for recipe in self.list_recipes():
            if recipe.recipe_id == recipe_id:
                return recipe
        raise KeyError(f"Receita não encontrada: {recipe_id}")

    def create(self, name: str, part_type: str, description: str) -> DatasetStore:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Informe um nome para a receita.")
        recipe_id = f"receita-{uuid.uuid4().hex[:10]}"
        store = DatasetStore(ProjectPaths(self.root / recipe_id), self.database)
        store.update_metadata(
            recipe_id=recipe_id,
            name=clean_name,
            part_type=part_type.strip() or "Peça não informada",
            description=description.strip(),
        )
        store.log_event("recipe_created", name=clean_name)
        self.activate(recipe_id)
        return store

    def update(self, recipe_id: str, name: str, part_type: str, description: str) -> None:
        recipe = self.get(recipe_id)
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Informe um nome para a receita.")
        store = DatasetStore(ProjectPaths(recipe.root), self.database)
        store.update_metadata(
            name=clean_name,
            part_type=part_type.strip() or "Peça não informada",
            description=description.strip(),
        )
        store.log_event("recipe_updated")


class DatasetStore:
    """Gerencia o dataset do projeto sem acoplar a interface ao filesystem."""

    def __init__(self, paths: ProjectPaths, database: QualityDatabase | None = None) -> None:
        self.paths = paths.ensure()
        self.database = database
        if not self.paths.metadata.exists():
            self._write_metadata(
                {
                    "name": "Projeto principal",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    def _label_dir(self, label: str) -> Path:
        normalized = label.lower()
        if normalized not in VALID_LABELS:
            raise ValueError(f"Rótulo inválido: {label}")
        return self.paths.ok if normalized == "ok" else self.paths.nok

    def _write_metadata(self, data: dict) -> None:
        self.paths.metadata.parent.mkdir(parents=True, exist_ok=True)
        self.paths.metadata.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def read_metadata(self) -> dict:
        return json.loads(self.paths.metadata.read_text(encoding="utf-8"))

    def update_metadata(self, **values) -> None:
        data = self.read_metadata()
        data.update(values)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_metadata(data)
        if self.database is not None and data.get("recipe_id"):
            self.database.sync_recipe(data, self.paths.root)

    def log_event(self, event_type: str, **details) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **details,
        }
        event_file = self.paths.root / "events.jsonl"
        with event_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        if self.database is not None:
            self.database.log_event(self.recipe_id, event_type, details)

    @property
    def recipe_id(self) -> str | None:
        return str(self.read_metadata().get("recipe_id")) if self.paths.metadata.exists() else None

    def counts(self) -> dict[str, int]:
        return {label: len(self.list_images(label)) for label in VALID_LABELS}

    def list_images(self, label: str) -> list[Path]:
        directory = self._label_dir(label)
        return sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    def all_labeled_images(self) -> list[tuple[Path, str]]:
        items: list[tuple[Path, str]] = []
        for label in VALID_LABELS:
            items.extend((path, label) for path in self.list_images(label))
        return items

    def save_frame(self, frame: np.ndarray, label: str, source: str = "camera") -> Path:
        if frame is None or frame.size == 0:
            raise ValueError("A câmera não forneceu uma imagem válida.")
        destination = self._new_destination(label, ".jpg")
        if not cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            raise OSError("Não foi possível salvar a imagem capturada.")
        if self.database is not None and self.recipe_id:
            height, width = frame.shape[:2]
            self.database.register_image(
                self.recipe_id, destination, label.lower(), source, width, height
            )
        self.touch()
        return destination

    def import_images(self, sources: Iterable[Path], label: str) -> list[Path]:
        imported: list[Path] = []
        for source in sources:
            source = Path(source)
            if not source.is_file() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            image = cv2.imread(str(source))
            if image is None or image.size == 0:
                continue
            destination = self._new_destination(label, source.suffix.lower())
            shutil.copy2(source, destination)
            imported.append(destination)
            if self.database is not None and self.recipe_id:
                height, width = image.shape[:2]
                self.database.register_image(
                    self.recipe_id, destination, label.lower(), "import", width, height
                )
        if imported:
            self.touch()
        return imported

    def delete_image(self, image_path: Path) -> None:
        resolved = Path(image_path).resolve()
        allowed = {self.paths.ok.resolve(), self.paths.nok.resolve()}
        if resolved.parent not in allowed:
            raise ValueError("A imagem não pertence ao dataset atual.")
        if self.database is not None:
            self.database.mark_image_deleted(resolved)
        resolved.unlink(missing_ok=True)
        self.touch()

    def clear_images(self) -> tuple[int, Path | None]:
        """Apaga as amostras e arquiva o modelo que deixou de representar o dataset."""

        images = [path for label in VALID_LABELS for path in self.list_images(label)]
        for path in images:
            path.unlink()

        archived_model: Path | None = None
        if self.paths.model.is_file():
            archive = self.paths.models / "arquivados"
            archive.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            archived_model = archive / f"qualityai_model_{timestamp}.pt"
            shutil.move(str(self.paths.model), str(archived_model))

        if self.database is not None and self.recipe_id:
            self.database.archive_dataset(self.recipe_id)

        self.update_metadata(dataset_cleared_at=datetime.now(timezone.utc).isoformat())
        self.log_event(
            "dataset_cleared",
            images_removed=len(images),
            archived_model=archived_model.name if archived_model else None,
        )
        return len(images), archived_model

    def touch(self) -> None:
        self.update_metadata()

    def _new_destination(self, label: str, suffix: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = f"{timestamp}-{uuid.uuid4().hex[:8]}{suffix}"
        return self._label_dir(label) / name
