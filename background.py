from __future__ import annotations

from io import BytesIO
from PIL import Image, ImageOps

MAX_PIXELS = 9000 * 9000


def open_uploaded_image(uploaded_file) -> Image.Image:
    """Open a Streamlit uploaded image safely as RGBA."""
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    img.load()
    if img.width * img.height > MAX_PIXELS:
        raise ValueError("La imagen es demasiado grande. Usa una imagen menor a 9000×9000 px.")
    return img.convert("RGBA")


def resize_for_ai(img: Image.Image, max_side: int = 1800) -> Image.Image:
    """Downscale large images before AI processing for speed."""
    if max_side <= 0:
        return img
    w, h = img.size
    if max(w, h) <= max_side:
        return img.copy()
    scale = max_side / max(w, h)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def image_to_png_bytes(img: Image.Image, dpi: int = 300) -> bytes:
    buffer = BytesIO()
    img.save(buffer, format="PNG", dpi=(dpi, dpi))
    return buffer.getvalue()


def image_to_pdf_bytes(img: Image.Image, dpi: int = 300, white_background: bool = True) -> bytes:
    buffer = BytesIO()
    rgba = img.convert("RGBA")
    if white_background:
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.getchannel("A"))
    else:
        bg = rgba.convert("RGB")
    bg.save(buffer, format="PDF", resolution=dpi)
    return buffer.getvalue()


def add_print_canvas(img: Image.Image, width_cm: float, height_cm: float, dpi: int = 300) -> Image.Image:
    if width_cm <= 0 or height_cm <= 0:
        return img
    px_w = int(width_cm / 2.54 * dpi)
    px_h = int(height_cm / 2.54 * dpi)
    if px_w <= 0 or px_h <= 0:
        return img
    copy = img.copy()
    copy.thumbnail((px_w, px_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (px_w, px_h), (255, 255, 255, 0))
    x = (px_w - copy.width) // 2
    y = (px_h - copy.height) // 2
    canvas.alpha_composite(copy, (x, y))
    return canvas


def upscale_lanczos(img: Image.Image, scale: int = 1) -> Image.Image:
    scale = max(1, min(int(scale), 4))
    if scale == 1:
        return img
    return img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
