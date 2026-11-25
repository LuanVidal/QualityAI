from pathlib import Path

from qualityai.database import QualityDatabase


def test_database_creates_complete_schema(tmp_path: Path) -> None:
    database = QualityDatabase(tmp_path / "qualityai.db")

    with database.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == 1
    assert {
        "recipes",
        "dataset_versions",
        "image_samples",
        "training_runs",
        "model_versions",
        "inspections",
        "human_reviews",
        "audit_events",
    }.issubset(tables)


def test_database_records_traceable_inspection_flow(tmp_path: Path) -> None:
    database = QualityDatabase(tmp_path / "qualityai.db")
    recipe_root = tmp_path / "projects" / "gear"
    metadata = {
        "recipe_id": "gear",
        "name": "Engrenagem",
        "part_type": "Aço usinado",
        "description": "Inspeção de dentes",
    }
    database.sync_recipe(metadata, recipe_root)
    database.set_active_recipe("gear")

    sample = tmp_path / "sample.jpg"
    sample.write_bytes(b"image")
    sample_id = database.register_image("gear", sample, "ok", "camera", 640, 480)
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")
    database.record_training_and_model(
        "gear",
        version="v1",
        model_path=model,
        total_images=20,
        folds=5,
        metrics={"balanced_accuracy": 0.95},
        confidence_threshold=0.70,
    )
    inspection_file = tmp_path / "inspection.jpg"
    inspection_file.write_bytes(b"inspection")
    inspection_id = database.record_inspection(
        "gear",
        model_id="v1",
        file_path=inspection_file,
        predicted_label="ok",
        confidence=0.96,
        requires_review=False,
    )
    database.record_review(inspection_id, "ok", False, sample_id)

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM image_samples").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM training_runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM model_versions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM inspections").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM human_reviews").fetchone()[0] == 1
        assert database.active_recipe_id() == "gear"
