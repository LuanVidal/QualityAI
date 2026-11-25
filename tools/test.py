"""Executa uma inferência com o mesmo artefato produzido pelo treinamento."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qualityai.ml import QualityPredictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if frame is None:
        raise SystemExit(f"Imagem inválida: {args.image}")
    result = QualityPredictor(args.model).predict(frame)
    status = "REVISÃO" if result.requires_review else result.label
    print(f"Resultado: {status}")
    print(f"Confiança: {result.confidence:.1%}")
    print(f"Probabilidade OK: {result.probability_ok:.1%}")
    print(f"Modelo: {result.model_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
