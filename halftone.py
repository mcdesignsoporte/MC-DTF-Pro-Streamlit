from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageFilter


def clean_alpha(img: Image.Image, alpha_cut: int = 80, despeckle_area: int = 3, edge_contract: int = 0) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    alpha = np.where(alpha >= alpha_cut, 255, 0).astype(np.uint8)

    kernel = np.ones((3, 3), np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel, iterations=1)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel, iterations=1)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(alpha, 8)
    cleaned = np.zeros_like(alpha)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= despeckle_area:
            cleaned[labels == i] = 255
    alpha = cleaned

    if edge_contract > 0:
        alpha = cv2.erode(alpha, kernel, iterations=edge_contract)

    arr[:, :, :3] = rgb
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, "RGBA")


def sharpen(img: Image.Image, radius: float = 1.0, percent: int = 90, threshold: int = 3) -> Image.Image:
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def preset_values(preset: str) -> tuple[int, int, int]:
    presets = {
        "Caricatura / detalle fino": (70, 2, 0),
        "Diseño normal DTF": (90, 3, 0),
        "Logo fuerte / borde duro": (140, 8, 1),
    }
    return presets.get(preset, presets["Diseño normal DTF"])
