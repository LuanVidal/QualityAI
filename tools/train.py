"""Treina o modelo leve do QualityAI a partir de pastas ok/ e nok/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qualityai.ml import train_lightweight_model
from qualityai.preprocessing import PreprocessingConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Pasta contendo ok/ e nok/")
    parser.add_argument("--output", type=Path, default=Path("models/qualityai_model.pt"))
    parser.add_argument("--sem-clahe", action="store_true", help="Desativa normalização CLAHE")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    images: list[tuple[Path, str]] = []
    for label in ("ok", "nok"):
        folder = args.dataset / label
        if folder.is_dir():
            images.extend((path, label) for path in folder.iterdir() if path.is_file())

    def progress(percent: int, message: str) -> None:
        print(f"[{percent:3d}%] {message}", flush=True)

    report = train_lightweight_model(
        images,
        args.output,
        preprocessing=PreprocessingConfig(clahe=not args.sem_clahe),
        progress=progress,
    )
    print(f"Modelo: {report.model_path}")
    print(f"Acurácia balanceada (validação cruzada): {report.balanced_accuracy:.1%}")
    print(f"F1: {report.f1:.1%} | ROC AUC: {report.roc_auc:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
