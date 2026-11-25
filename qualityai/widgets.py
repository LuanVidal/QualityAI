"""Widgets reutilizáveis da interface."""

from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np
from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from qualityai.preprocessing import PreprocessingConfig, apply_filters, draw_roi_overlay


class StatCard(QFrame):
    def __init__(self, caption: str, value: str = "—", detail: str = "") -> None:
        super().__init__()
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)
        title = QLabel(caption)
        title.setObjectName("CardCaption")
        self.value = QLabel(value)
        self.value.setObjectName("CardValue")
        self.detail = QLabel(detail)
        self.detail.setObjectName("Muted")
        self.detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_data(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)


class VideoView(QLabel):
    """Mostra o vídeo e permite delimitar a ROI arrastando o mouse."""

    roiChanged = Signal(float, float, float, float)

    def __init__(self, text: str = "Conecte uma câmera USB") -> None:
        super().__init__(text)
        self.setObjectName("VideoView")
        self.setMinimumSize(640, 390)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self._frame: np.ndarray | None = None
        self._config = PreprocessingConfig()
        self._processed_preview = False
        self._drag_start: tuple[float, float] | None = None
        self._display_rect = QRect()

    def set_processed_preview(self, enabled: bool) -> None:
        self._processed_preview = enabled
        self._render()

    def set_source(self, frame: np.ndarray, config: PreprocessingConfig) -> None:
        self._frame = frame.copy()
        self._config = config.normalized()
        self._render()

    def clear_source(self, message: str = "Conecte uma câmera USB") -> None:
        self._frame = None
        self.clear()
        self.setText(message)

    def _render(self) -> None:
        if self._frame is None:
            return
        if self._processed_preview:
            display = apply_filters(self._frame, self._config)
        else:
            display = draw_roi_overlay(self._frame, self._config)
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        image = QImage(rgb.data, width, height, channels * width, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        left = (self.width() - pixmap.width()) // 2
        top = (self.height() - pixmap.height()) // 2
        self._display_rect = QRect(left, top, pixmap.width(), pixmap.height())
        self.setPixmap(pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render()

    def _normalized_position(self, event: QMouseEvent) -> tuple[float, float] | None:
        if self._frame is None or not self._display_rect.contains(event.position().toPoint()):
            return None
        x = (event.position().x() - self._display_rect.left()) / max(self._display_rect.width(), 1)
        y = (event.position().y() - self._display_rect.top()) / max(self._display_rect.height(), 1)
        return min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._processed_preview:
            self._drag_start = self._normalized_position(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            current = self._normalized_position(event)
            if current is not None:
                x1, y1 = self._drag_start
                x2, y2 = current
                x, y = min(x1, x2), min(y1, y2)
                width, height = abs(x2 - x1), abs(y2 - y1)
                if width >= 0.05 and height >= 0.05:
                    self._config = replace(
                        self._config,
                        roi_x=x,
                        roi_y=y,
                        roi_width=width,
                        roi_height=height,
                    ).normalized()
                    self.roiChanged.emit(x, y, width, height)
                    self._render()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(event)
