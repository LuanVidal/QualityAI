"""Treinamento leve e inferência consistente para o QualityAI."""

from __future__ import annotations

import json
import hashlib
import uuid
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable, Sequence

import cv2
import numpy as np
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from qualityai.config import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    IMAGE_SIZE,
    MIN_IMAGES_PER_CLASS,
)
from qualityai.preprocessing import PreprocessingConfig, apply_filters


ProgressCallback = Callable[[int, str], None]


class TrainingError(RuntimeError):
    pass


class TrainingCancelled(TrainingError):
    pass


@dataclass(frozen=True)
class TrainingReport:
    model_path: Path
    total_images: int
    ok_images: int
    nok_images: int
    folds: int
    accuracy: float
    balanced_accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    confusion_matrix: list[list[int]]
    trained_at: str
    model_version: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["model_path"] = str(self.model_path)
        return data


@dataclass(frozen=True)
class InferenceResult:
    label: str
    confidence: float
    probability_ok: float
    requires_review: bool
    model_version: str


def _emit(callback: ProgressCallback | None, percent: int, message: str) -> None:
    if callback:
        callback(int(min(max(percent, 0), 100)), message)


def _check_cancelled(cancel_event: Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise TrainingCancelled("Treinamento cancelado com segurança pelo usuário.")


def validate_labeled_images(
    labeled_images: Sequence[tuple[Path, str]], minimum: int = MIN_IMAGES_PER_CLASS
) -> dict[str, int]:
    counts = {"ok": 0, "nok": 0}
    for path, label in labeled_images:
        normalized = label.lower()
        if normalized not in counts:
            raise TrainingError(f"Rótulo desconhecido: {label}")
        if Path(path).is_file():
            counts[normalized] += 1
    missing = [f"{label.upper()}: {count}/{minimum}" for label, count in counts.items() if count < minimum]
    if missing:
        raise TrainingError(
            "Dataset insuficiente. Complete as duas classes antes de treinar ("
            + ", ".join(missing)
            + ")."
        )
    return counts


def _feature_extractor(weights: MobileNet_V3_Small_Weights | None):
    model = mobilenet_v3_small(weights=weights)
    model.classifier = torch.nn.Identity()
    model.requires_grad_(False)
    return model.eval()


def _frame_to_tensor(frame: np.ndarray, transform) -> torch.Tensor:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    return transform(image).unsqueeze(0)


def _read_and_prepare(path: Path, config: PreprocessingConfig) -> np.ndarray:
    frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        raise TrainingError(f"Imagem inválida ou ilegível: {path.name}")
    return apply_filters(frame, config)


def train_lightweight_model(
    labeled_images: Sequence[tuple[Path, str]],
    model_path: Path,
    preprocessing: PreprocessingConfig | None = None,
    progress: ProgressCallback | None = None,
    cancel_event: Event | None = None,
    random_seed: int = 42,
) -> TrainingReport:
    """Treina apenas um classificador linear sobre atributos visuais congelados."""

    config = (preprocessing or PreprocessingConfig()).normalized()
    counts = validate_labeled_images(labeled_images)
    ordered = sorted((Path(path), label.lower()) for path, label in labeled_images)
    labels = np.array([1 if label == "ok" else 0 for _, label in ordered], dtype=np.int64)

    _check_cancelled(cancel_event)
    _emit(progress, 2, "Carregando o extrator visual MobileNetV3-Small…")
    weights = MobileNet_V3_Small_Weights.DEFAULT
    transform = weights.transforms(crop_size=IMAGE_SIZE, resize_size=232)
    extractor = _feature_extractor(weights)
    extractor.to("cpu")
    cache_dir = Path(model_path).parent / "atributos"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_config = json.dumps(config.to_dict(), sort_keys=True)

    features: list[np.ndarray] = []
    total = len(ordered)
    with torch.inference_mode():
        for index, (path, _) in enumerate(ordered, start=1):
            _check_cancelled(cancel_event)
            signature = hashlib.sha256(
                path.read_bytes() + cache_config.encode() + b"mobilenet-v3-small-default-224-232-v1"
            ).hexdigest()
            cached = cache_dir / f"{signature}.npy"
            embedding = None
            if cached.is_file():
                try:
                    candidate = np.load(cached, allow_pickle=False)
                    if candidate.shape == (576,) and np.isfinite(candidate).all():
                        embedding = candidate
                except (OSError, ValueError):
                    pass
            if embedding is None:
                prepared = _read_and_prepare(path, config)
                tensor = _frame_to_tensor(prepared, transform)
                embedding = extractor(tensor).cpu().numpy().reshape(-1)
                np.save(cached, embedding, allow_pickle=False)
            features.append(embedding)
            percent = 5 + round(58 * index / total)
            _emit(progress, percent, f"Extraindo atributos: {index}/{total} imagens")

    feature_matrix = np.vstack(features).astype(np.float32)
    folds = min(5, counts["ok"], counts["nok"])
    if folds < 2:
        raise TrainingError("São necessárias pelo menos duas imagens por classe para validar.")

    _check_cancelled(cancel_event)
    _emit(progress, 68, f"Validando o classificador em {folds} divisões estratificadas…")
    estimator = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    solver="liblinear",
                    random_state=random_seed,
                ),
            ),
        ]
    )
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_seed)
    # Busca somente três forças de regularização, sem treinar a rede visual.
    # A seleção ocorre DENTRO de cada divisão externa para evitar viés nas métricas.
    selection = GridSearchCV(
        estimator,
        {"classifier__C": [0.01, 0.1, 1.0]},
        scoring="balanced_accuracy",
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=random_seed),
        n_jobs=1,
    )
    probabilities = cross_val_predict(
        selection,
        feature_matrix,
        labels,
        cv=splitter,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]
    predictions = (probabilities >= 0.5).astype(np.int64)

    metrics = {
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
    }

    _check_cancelled(cancel_event)
    _emit(progress, 82, "Treinando a versão final com todas as imagens confirmadas…")
    selection.fit(feature_matrix, labels)
    estimator = selection.best_estimator_
    scaler: StandardScaler = estimator.named_steps["scaler"]
    classifier: LogisticRegression = estimator.named_steps["classifier"]

    trained_at = datetime.now(timezone.utc).isoformat()
    version = datetime.now().strftime("%Y.%m.%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    payload = {
        "format_version": 1,
        "model_type": "mobilenet_v3_small_frozen_logistic",
        "model_version": version,
        "trained_at": trained_at,
        "image_size": IMAGE_SIZE,
        "classes": ["NOK", "OK"],
        "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
        "preprocessing": config.to_dict(),
        "dataset": {"ok": counts["ok"], "nok": counts["nok"]},
        "metrics": metrics,
        "regularization_c": float(selection.best_params_["classifier__C"]),
        "validation_method": "nested_stratified_5_outer_3_inner",
        "feature_state_dict": extractor.state_dict(),
        "scaler_mean": torch.tensor(scaler.mean_, dtype=torch.float32),
        "scaler_scale": torch.tensor(scaler.scale_, dtype=torch.float32),
        "classifier_coef": torch.tensor(classifier.coef_[0], dtype=torch.float32),
        "classifier_intercept": torch.tensor(float(classifier.intercept_[0]), dtype=torch.float32),
    }

    _check_cancelled(cancel_event)
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = model_path.with_suffix(model_path.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(model_path)
    versioned_path = model_path.parent / f"model-{version}.pt"
    shutil.copy2(model_path, versioned_path)

    report = TrainingReport(
        model_path=model_path,
        total_images=total,
        ok_images=counts["ok"],
        nok_images=counts["nok"],
        folds=folds,
        accuracy=metrics["accuracy"],
        balanced_accuracy=metrics["balanced_accuracy"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        roc_auc=metrics["roc_auc"],
        confusion_matrix=metrics["confusion_matrix"],
        trained_at=trained_at,
        model_version=version,
    )
    report_path = model_path.with_suffix(".metrics.json")
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    versioned_report = model_path.parent / f"model-{version}.metrics.json"
    shutil.copy2(report_path, versioned_report)
    _emit(progress, 100, "Modelo leve treinado e validado com sucesso.")
    return report


class QualityPredictor:
    """Carrega o mesmo artefato produzido pelo treinamento para inferência."""

    def __init__(self, model_path: Path) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Modelo não encontrado: {self.model_path}")
        try:
            payload = torch.load(self.model_path, map_location="cpu", weights_only=True)
        except TypeError:
            payload = torch.load(self.model_path, map_location="cpu")
        if payload.get("format_version") != 1:
            raise TrainingError("Formato de modelo incompatível.")

        self.payload = payload
        self.preprocessing = PreprocessingConfig.from_dict(payload.get("preprocessing"))
        self.threshold = float(payload.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD))
        self.version = str(payload.get("model_version", "desconhecida"))
        self.extractor = _feature_extractor(weights=None)
        self.extractor.load_state_dict(payload["feature_state_dict"])
        self.extractor.eval().to("cpu")
        self.transform = MobileNet_V3_Small_Weights.DEFAULT.transforms(
            crop_size=int(payload.get("image_size", IMAGE_SIZE)), resize_size=232
        )

    @property
    def metrics(self) -> dict:
        return dict(self.payload.get("metrics", {}))

    def predict(self, frame: np.ndarray) -> InferenceResult:
        prepared = apply_filters(frame, self.preprocessing)
        tensor = _frame_to_tensor(prepared, self.transform)
        with torch.inference_mode():
            embedding = self.extractor(tensor).reshape(-1)

        mean = self.payload["scaler_mean"]
        scale = torch.clamp(self.payload["scaler_scale"], min=1e-8)
        normalized = (embedding - mean) / scale
        logit = torch.dot(self.payload["classifier_coef"], normalized) + self.payload[
            "classifier_intercept"
        ]
        probability_ok = float(torch.sigmoid(logit).item())
        if probability_ok >= 0.5:
            label = "OK"
            confidence = probability_ok
        else:
            label = "NOK"
            confidence = 1.0 - probability_ok
        return InferenceResult(
            label=label,
            confidence=confidence,
            probability_ok=probability_ok,
            requires_review=confidence < self.threshold,
            model_version=self.version,
        )
