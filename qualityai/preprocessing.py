"""ROI e filtros reproduzíveis para treino e inspeção."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np


@dataclass
class PreprocessingConfig:
    """Parâmetros salvos junto ao modelo para impedir divergência de imagem."""

    roi_x: float = 0.10
    roi_y: float = 0.10
    roi_width: float = 0.80
    roi_height: float = 0.80
    grayscale: bool = False
    clahe: bool = True
    denoise: bool = False
    sharpen: bool = False
    brightness: int = 0
    contrast: float = 1.0

    def normalized(self) -> "PreprocessingConfig":
        x = min(max(float(self.roi_x), 0.0), 0.95)
        y = min(max(float(self.roi_y), 0.0), 0.95)
        width = min(max(float(self.roi_width), 0.05), 1.0 - x)
        height = min(max(float(self.roi_height), 0.05), 1.0 - y)
        return PreprocessingConfig(
            roi_x=x,
            roi_y=y,
            roi_width=width,
            roi_height=height,
            grayscale=bool(self.grayscale),
            clahe=bool(self.clahe),
            denoise=bool(self.denoise),
            sharpen=bool(self.sharpen),
            brightness=int(min(max(self.brightness, -100), 100)),
            contrast=float(min(max(self.contrast, 0.5), 2.0)),
        )

    def to_dict(self) -> dict:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, values: dict | None) -> "PreprocessingConfig":
        if not values:
            return cls()
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in values.items() if key in allowed}).normalized()


def crop_roi(frame: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
    if frame is None or frame.size == 0:
        raise ValueError("Imagem vazia.")
    cfg = config.normalized()
    height, width = frame.shape[:2]
    x1 = int(round(cfg.roi_x * width))
    y1 = int(round(cfg.roi_y * height))
    x2 = int(round((cfg.roi_x + cfg.roi_width) * width))
    y2 = int(round((cfg.roi_y + cfg.roi_height) * height))
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        raise ValueError("A ROI selecionada não contém pixels.")
    return roi.copy()


def apply_filters(frame: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
    """Aplica ROI e filtros mantendo uma saída BGR de três canais."""

    cfg = config.normalized()
    image = crop_roi(frame, cfg)

    if cfg.grayscale:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if cfg.clahe:
            gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    elif cfg.clahe:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, channel_a, channel_b = cv2.split(lab)
        lightness = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
        image = cv2.cvtColor(
            cv2.merge((lightness, channel_a, channel_b)), cv2.COLOR_LAB2BGR
        )

    if cfg.denoise:
        image = cv2.GaussianBlur(image, (3, 3), 0)

    if cfg.sharpen:
        blurred = cv2.GaussianBlur(image, (0, 0), 1.0)
        image = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

    image = cv2.convertScaleAbs(image, alpha=cfg.contrast, beta=cfg.brightness)
    return image


def draw_roi_overlay(frame: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
    """Desenha uma ROI com identidade visual sem modificar a imagem persistida."""

    output = frame.copy()
    cfg = config.normalized()
    height, width = output.shape[:2]
    x1, y1 = int(cfg.roi_x * width), int(cfg.roi_y * height)
    x2 = min(int((cfg.roi_x + cfg.roi_width) * width), width - 1)
    y2 = min(int((cfg.roi_y + cfg.roi_height) * height), height - 1)

    # Mantém a área útil nítida e reduz a atenção sobre tudo que ficará fora do modelo.
    navy_layer = np.full_like(output, (36, 24, 7))
    preview = cv2.addWeighted(output, 0.38, navy_layer, 0.62, 0)
    preview[y1 : y2 + 1, x1 : x2 + 1] = output[y1 : y2 + 1, x1 : x2 + 1]

    # Um contorno fino e cantos reforçados substituem a caixa amarela convencional.
    accent = (178, 195, 0)  # #00c3b2 em BGR
    cv2.rectangle(preview, (x1, y1), (x2, y2), accent, 2, cv2.LINE_AA)
    corner = max(12, min(30, (x2 - x1) // 6, (y2 - y1) // 6))
    thickness = 5
    for start, end in (
        ((x1, y1 + corner), (x1, y1)),
        ((x1, y1), (x1 + corner, y1)),
        ((x2 - corner, y1), (x2, y1)),
        ((x2, y1), (x2, y1 + corner)),
        ((x1, y2 - corner), (x1, y2)),
        ((x1, y2), (x1 + corner, y2)),
        ((x2 - corner, y2), (x2, y2)),
        ((x2, y2 - corner), (x2, y2)),
    ):
        cv2.line(preview, start, end, accent, thickness, cv2.LINE_AA)

    # Selo compacto dentro da seleção para não competir visualmente com a peça.
    font = cv2.FONT_HERSHEY_SIMPLEX
    label = "ROI"
    scale = 0.58
    text_size, baseline = cv2.getTextSize(label, font, scale, 2)
    badge_x = min(x1 + 12, max(x1, x2 - text_size[0] - 22))
    badge_y = min(y1 + 12, max(y1, y2 - text_size[1] - baseline - 16))
    badge_right = badge_x + text_size[0] + 18
    badge_bottom = badge_y + text_size[1] + baseline + 12
    cv2.rectangle(
        preview,
        (badge_x, badge_y),
        (badge_right, badge_bottom),
        (49, 29, 11),
        -1,
        cv2.LINE_AA,
    )
    cv2.rectangle(
        preview,
        (badge_x, badge_y),
        (badge_right, badge_bottom),
        accent,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        preview,
        label,
        (badge_x + 9, badge_y + text_size[1] + 5),
        font,
        scale,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return preview


def visual_similarity(
    first: np.ndarray, second: np.ndarray, config: PreprocessingConfig
) -> float:
    """Estima similaridade para alertar sobre capturas quase duplicadas."""

    prepared: list[np.ndarray] = []
    for frame in (first, second):
        image = apply_filters(frame, config)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
        prepared.append(gray.astype(np.float32))
    correlation = cv2.matchTemplate(
        prepared[0], prepared[1], cv2.TM_CCOEFF_NORMED
    )[0, 0]
    if np.isnan(correlation):
        difference = np.mean(np.abs(prepared[0] - prepared[1])) / 255.0
        return float(1.0 - difference)
    return float(min(max(correlation, 0.0), 1.0))
