from __future__ import annotations

from PIL import Image


def preview_on_background(img: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (*color, 255))
    bg.alpha_composite(rgba)
    return bg.convert("RGB")
