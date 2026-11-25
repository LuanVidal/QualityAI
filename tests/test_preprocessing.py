import cv2
import numpy as np

from qualityai.camera import CameraError, mirror_frame
from qualityai.preprocessing import (
    PreprocessingConfig,
    apply_filters,
    crop_roi,
    draw_roi_overlay,
    visual_similarity,
)


def test_roi_is_normalized_and_cropped() -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    config = PreprocessingConfig(roi_x=0.25, roi_y=0.20, roi_width=0.50, roi_height=0.60)

    cropped = crop_roi(frame, config)

    assert cropped.shape == (60, 100, 3)


def test_filters_keep_three_channels() -> None:
    gradient = np.tile(np.arange(0, 200, dtype=np.uint8), (100, 1))
    frame = cv2.merge((gradient, gradient, gradient))
    config = PreprocessingConfig(
        grayscale=True,
        clahe=True,
        denoise=True,
        sharpen=True,
        brightness=10,
        contrast=1.2,
    )

    processed = apply_filters(frame, config)

    assert processed.ndim == 3
    assert processed.shape[2] == 3
    assert processed.dtype == np.uint8


def test_invalid_roi_values_are_clamped() -> None:
    config = PreprocessingConfig(
        roi_x=-1,
        roi_y=2,
        roi_width=9,
        roi_height=-4,
        brightness=1000,
        contrast=9,
    ).normalized()

    assert 0 <= config.roi_x < 1
    assert 0 <= config.roi_y < 1
    assert 0.05 <= config.roi_width <= 1
    assert 0.05 <= config.roi_height <= 1
    assert config.brightness == 100
    assert config.contrast == 2.0


def test_similarity_detects_duplicate_and_different_frames() -> None:
    first = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(first, (20, 20), (80, 80), (255, 255, 255), -1)
    different = np.zeros_like(first)
    cv2.circle(different, (50, 50), 15, (255, 255, 255), -1)
    config = PreprocessingConfig(roi_x=0, roi_y=0, roi_width=1, roi_height=1, clahe=False)

    assert visual_similarity(first, first.copy(), config) > 0.99
    assert visual_similarity(first, different, config) < 0.95


def test_roi_overlay_preserves_center_and_dims_outside() -> None:
    frame = np.full((100, 200, 3), 200, dtype=np.uint8)
    config = PreprocessingConfig(roi_x=0.25, roi_y=0.20, roi_width=0.50, roi_height=0.60)

    preview = draw_roi_overlay(frame, config)

    assert preview.shape == frame.shape
    assert np.array_equal(preview[70, 140], frame[70, 140])
    assert preview[5, 5].mean() < frame[5, 5].mean()


def test_camera_frame_is_mirrored_horizontally() -> None:
    frame = np.zeros((2, 4, 3), dtype=np.uint8)
    frame[:, :2] = (255, 0, 0)
    frame[:, 2:] = (0, 255, 0)

    mirrored = mirror_frame(frame)

    assert np.array_equal(mirrored[:, :2], frame[:, 2:])
    assert np.array_equal(mirrored[:, 2:], frame[:, :2])


def test_empty_camera_frame_is_rejected() -> None:
    with np.testing.assert_raises(CameraError):
        mirror_frame(np.empty((0, 0, 3), dtype=np.uint8))
