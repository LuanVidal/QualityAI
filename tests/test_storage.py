from pathlib import Path

import numpy as np

from qualityai.config import ProjectPaths
from qualityai.storage import DatasetStore, RecipeCatalog


def test_store_saves_and_counts_frames(tmp_path: Path) -> None:
    store = DatasetStore(ProjectPaths(tmp_path / "project"))
    frame = np.full((48, 64, 3), 128, dtype=np.uint8)

    ok_path = store.save_frame(frame, "ok")
    nok_path = store.save_frame(frame, "nok")

    assert ok_path.is_file()
    assert nok_path.is_file()
    assert store.counts() == {"ok": 1, "nok": 1}


def test_store_rejects_path_outside_dataset(tmp_path: Path) -> None:
    store = DatasetStore(ProjectPaths(tmp_path / "project"))
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"not-an-image")

    try:
        store.delete_image(outside)
    except ValueError as error:
        assert "não pertence" in str(error)
    else:
        raise AssertionError("Era esperado ValueError para caminho externo")


def test_import_skips_invalid_images(tmp_path: Path) -> None:
    store = DatasetStore(ProjectPaths(tmp_path / "project"))
    invalid = tmp_path / "invalid.jpg"
    invalid.write_text("invalid", encoding="utf-8")

    imported = store.import_images([invalid], "ok")

    assert imported == []
    assert store.counts()["ok"] == 0


def test_recipes_keep_datasets_isolated(tmp_path: Path) -> None:
    catalog = RecipeCatalog(tmp_path / "projects")
    first = catalog.active_store()
    frame = np.full((20, 30, 3), 90, dtype=np.uint8)
    first.save_frame(frame, "ok")

    second = catalog.create("Engrenagem", "Aço usinado", "Detectar dentes quebrados")
    second.save_frame(frame, "nok")

    assert first.counts() == {"ok": 1, "nok": 0}
    assert second.counts() == {"ok": 0, "nok": 1}
    assert catalog.active_recipe_id() == second.read_metadata()["recipe_id"]


def test_clear_images_archives_current_model(tmp_path: Path) -> None:
    store = DatasetStore(ProjectPaths(tmp_path / "project"))
    frame = np.full((20, 30, 3), 120, dtype=np.uint8)
    store.save_frame(frame, "ok")
    store.save_frame(frame, "nok")
    store.paths.model.write_bytes(b"model")

    removed, archived_model = store.clear_images()

    assert removed == 2
    assert store.counts() == {"ok": 0, "nok": 0}
    assert not store.paths.model.exists()
    assert archived_model is not None and archived_model.read_bytes() == b"model"
