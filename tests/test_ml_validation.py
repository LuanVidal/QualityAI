from pathlib import Path

import pytest

from qualityai.ml import TrainingError, validate_labeled_images


def _files(tmp_path: Path, label: str, amount: int) -> list[tuple[Path, str]]:
    result = []
    for index in range(amount):
        path = tmp_path / f"{label}-{index}.jpg"
        path.write_bytes(b"sample")
        result.append((path, label))
    return result


def test_validation_accepts_ten_images_per_class(tmp_path: Path) -> None:
    images = _files(tmp_path, "ok", 10) + _files(tmp_path, "nok", 10)

    assert validate_labeled_images(images) == {"ok": 10, "nok": 10}


def test_validation_explains_missing_class(tmp_path: Path) -> None:
    images = _files(tmp_path, "ok", 10) + _files(tmp_path, "nok", 3)

    with pytest.raises(TrainingError, match="NOK: 3/10"):
        validate_labeled_images(images)
