"""Controle simples e robusto de webcam/câmera USB."""

from __future__ import annotations

import platform

import cv2
import numpy as np


class CameraError(RuntimeError):
    pass


def mirror_frame(frame: np.ndarray) -> np.ndarray:
    """Espelha a câmera horizontalmente para uma interação natural com a prévia."""

    if frame is None or frame.size == 0:
        raise CameraError("A câmera forneceu uma imagem vazia.")
    return cv2.flip(frame, 1)


class CameraController:
    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self.index: int | None = None

    @property
    def is_open(self) -> bool:
        return bool(self._capture is not None and self._capture.isOpened())

    def open(self, index: int = 0) -> None:
        self.release()
        backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
        capture = cv2.VideoCapture(index, backend)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"Não foi possível abrir a câmera {index}. Verifique o cabo USB e as permissões do Windows."
            )
        self._capture = capture
        self.index = index

    def read(self) -> np.ndarray:
        if not self.is_open or self._capture is None:
            raise CameraError("Nenhuma câmera está conectada.")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError("A câmera parou de fornecer imagens.")
        return frame

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self.index = None
