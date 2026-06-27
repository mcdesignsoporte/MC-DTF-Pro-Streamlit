import io
import time
from dataclasses import dataclass

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageFilter, ImageOps

st.set_page_config(page_title="MC DTF Pro", page_icon="🎨", layout="wide")


@dataclass
class Preset:
    alpha_cut: int
    despeckle_area: int
    edge_contract: int
    max_ai_side: int
    upscale: int


PRESETS = {
    "Rápido": Preset(alpha_cut=80, despeckle_area=3, edge_contract=0, max_ai_side=1400, upscale=1),
    "Calidad": Preset(alpha_cut=70, despeckle_area=2, edge_contract=0, max_ai_side=1900, upscale=1),
    "Logo fuerte": Preset(alpha_cut=120, despeckle_area=10, edge_contract=1, max_ai_side=1800, upscale=1),
    "PNG transparente": Preset(alpha_cut=60, despeckle_area=2, edge_contract=0, max_ai_side=2200, upscale=1),
}


@st.cache_resource(show_spinner=False)
def load_rembg_session():
    from rembg import new_session
    return new_session("u2net")


def open_uploaded_image(uploaded_file) -> Image.Image:
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    img.load()
    return img.convert("RGBA")


def resize_for_ai(img: Image.Image, max_side: int) -> Image.Image:
    img = img.copy()
    w, h = img.size
    if max(w, h) <= max_side:
        return img
    scale = max_side / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def remove_background(img: Image.Image) -> Image.Image:
    from rembg import remove
    session = load_rembg_session()
    return remove(img, session=session).convert("RGBA")


def clean_alpha(img: Image.Image, alpha_cut: int, despeckle_area: int, edge_contract: int) -> Image.Image:
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

    if edge_contract > 0:
        kernel2 = np.ones((3, 3), np.uint8)
        cleaned = cv2.erode(cleaned, kernel2, iterations=edge_contract)

    arr[:, :, :3] = rgb
    arr[:, :, 3] = cleaned
    return Image.fromarray(arr, "RGBA")


def upscale_and_sharpen(img: Image.Image, scale: int) -> Image.Image:
    scale = max(1, min(int(scale), 4))
    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
    return img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=110, threshold=3))


def add_print_canvas(img: Image.Image, width_cm: float, height_cm: float, dpi: int) -> Image.Image:
    if width_cm <= 0 or height_cm <= 0:
        return img
    px_w = int(width_cm / 2.54 * dpi)
    px_h = int(height_cm / 2.54 * dpi)
    if px_w <= 0 or px_h <= 0:
        return img
    work = img.copy()
    work.thumbnail((px_w, px_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (px_w, px_h), (255, 255, 255, 0))
    canvas.alpha_composite(work, ((px_w - work.width) // 2, (px_h - work.height) // 2))
    return canvas


def make_halftone(img: Image.Image, dot_size: int, angle: float, invert: bool) -> Image.Image:
    rgba = img.convert("RGBA")
    alpha = np.array(rgba)[:, :, 3]
    base = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    base.alpha_composite(rgba)
    gray = ImageOps.grayscale(base)
    rotated = gray.rotate(angle, expand=True, fillcolor=255)
    pixels = np.array(rotated)
    h, w = pixels.shape
    step = max(4, int(dot_size))
    draw_arr = np.ones((h, w), dtype=np.uint8) * 255

    for y in range(0, h, step):
        for x in range(0, w, step):
            block = pixels[y:min(y + step, h), x:min(x + step, w)]
            if block.size == 0:
                continue
            darkness = 255 - float(block.mean())
            radius = (darkness / 255.0) * (step / 2)
            bh, bw = block.shape
            yy, xx = np.ogrid[:bh, :bw]
            mask = (yy - bh / 2) ** 2 + (xx - bw / 2) ** 2 <= radius ** 2
            draw_arr[y:y + bh, x:x + bw][mask] = 0

    out = Image.fromarray(draw_arr, "L")
    out = out.rotate(-angle, expand=True, fillcolor=255)
    left = (out.width - img.width) // 2
    top = (out.height - img.height) // 2
    out = out.crop((left, top, left + img.width, top + img.height))
    if invert:
        out = ImageOps.invert(out)

    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    transparent = Image.new("RGBA", img.size, (0, 0, 0, 0))
    mask = ImageOps.invert(out) if not invert else out
    result = Image.composite(black, transparent, mask)
    result.putalpha(Image.fromarray(alpha).point(lambda p: 255 if p > 0 else 0))
    return result


def png_bytes(img: Image.Image, dpi: int) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", dpi=(dpi, dpi))
    return buffer.getvalue()


def pdf_bytes(img: Image.Image, dpi: int) -> bytes:
    buffer = io.BytesIO()
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.getchannel("A"))
    bg.save(buffer, format="PDF", resolution=dpi)
    return buffer.getvalue()


def preview_on_background(img: Image.Image, color):
    bg = Image.new("RGBA", img.size, color)
    bg.alpha_composite(img)
    return bg.convert("RGB")


st.markdown("""
<style>
.block-container {padding-top: 1.8rem;}
.mc-title {font-size: 2.3rem; font-weight: 900; margin-bottom: 0;}
.mc-sub {opacity: .75; margin-top: .2rem;}
.badge {display:inline-block; padding: .3rem .6rem; border-radius:999px; background:#222; border:1px solid #444; margin-right:.4rem; font-size:.85rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="mc-title">MC DTF Pro</div>', unsafe_allow_html=True)
st.markdown('<p class="mc-sub">Herramienta web para quitar fondo, limpiar píxeles basura, eliminar semitransparencias, semitonos y exportación para DTF.</p>', unsafe_allow_html=True)
st.markdown('<span class="badge">MC Creative Studio</span><span class="badge">PNG transparente</span><span class="badge">PDF opcional</span><span class="badge">Semitonos</span>', unsafe_allow_html=True)
st.divider()

left, right = st.columns([0.38, 0.62])

with left:
    uploaded = st.file_uploader("Sube tu imagen", type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"])
    preset_name = st.selectbox("Modo de trabajo", list(PRESETS.keys()), index=0)
    preset = PRESETS[preset_name]

    skip_ai = st.checkbox("Saltar IA si ya tiene fondo transparente", value=True)
    generate_pdf = st.checkbox("Generar PDF", value=False)
    generate_halftone = st.checkbox("Generar semitono", value=False)

    with st.expander("Ajustes avanzados"):
        alpha_cut = st.slider("Corte de transparencia", 1, 254, preset.alpha_cut)
        despeckle_area = st.slider("Quitar basura menor a", 1, 500, preset.despeckle_area)
        edge_contract = st.slider("Contraer borde", 0, 4, preset.edge_contract)
        max_ai_side = st.slider("Tamaño máximo para IA", 800, 2600, preset.max_ai_side, step=100)
        upscale = st.selectbox("Alta resolución", [1, 2, 3, 4], index=preset.upscale - 1)
        dpi = st.number_input("DPI", min_value=72, max_value=600, value=300)
        width_cm = st.number_input("Ancho final cm opcional", min_value=0.0, value=0.0, step=0.5)
        height_cm = st.number_input("Alto final cm opcional", min_value=0.0, value=0.0, step=0.5)

    if generate_halftone:
        with st.expander("Ajustes semitono", expanded=True):
            dot_size = st.slider("Tamaño de punto", 4, 40, 8)
            angle = st.slider("Ángulo", 0, 90, 15)
            invert = st.checkbox("Invertir semitono", value=False)
    else:
        dot_size, angle, invert = 8, 15, False

    process = st.button("Procesar imagen", type="primary", use_container_width=True)

with right:
    if uploaded:
        original = open_uploaded_image(uploaded)
        st.caption(f"Original: {original.width} × {original.height}px")
        st.image(original, caption="Antes", use_container_width=True)
    else:
        st.info("Sube una imagen para empezar.")

if uploaded and process:
    start = time.perf_counter()
    logs = []
    progress = st.progress(0)
    status = st.empty()

    try:
        status.write("Abriendo imagen...")
        img = open_uploaded_image(uploaded)
        progress.progress(10)

        has_alpha = np.array(img)[:, :, 3].min() < 255
        if skip_ai and has_alpha:
            status.write("PNG transparente detectado: saltando IA...")
            removed = img
        else:
            status.write("Quitando fondo con IA...")
            ai_img = resize_for_ai(img, max_ai_side)
            removed = remove_background(ai_img)
        progress.progress(45)

        status.write("Limpiando píxeles basura y semitransparencias...")
        cleaned = clean_alpha(removed, alpha_cut, despeckle_area, edge_contract)
        progress.progress(65)

        status.write("Preparando tamaño de impresión...")
        final_img = add_print_canvas(cleaned, width_cm, height_cm, int(dpi))
        if upscale > 1:
            final_img = upscale_and_sharpen(final_img, upscale)
        progress.progress(80)

        out_png = png_bytes(final_img, int(dpi))
        out_pdf = pdf_bytes(final_img, int(dpi)) if generate_pdf else None
        progress.progress(92)

        ht_img = None
        ht_png = None
        ht_pdf = None
        if generate_halftone:
            status.write("Generando semitono...")
            ht_img = make_halftone(final_img, dot_size, angle, invert)
            ht_png = png_bytes(ht_img, int(dpi))
            ht_pdf = pdf_bytes(ht_img, int(dpi)) if generate_pdf else None

        progress.progress(100)
        elapsed = time.perf_counter() - start
        status.success(f"Listo en {elapsed:.1f} segundos")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.image(final_img, caption=f"Resultado limpio — {final_img.width} × {final_img.height}px", use_container_width=True)
        with c2:
            bg_choice = st.radio("Vista previa", ["Negra", "Blanca", "Roja"], horizontal=True)
            color = {"Negra": (8, 8, 8, 255), "Blanca": (255, 255, 255, 255), "Roja": (120, 0, 0, 255)}[bg_choice]
            st.image(preview_on_background(final_img, color), caption="Vista sobre fondo", use_container_width=True)

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.download_button("Descargar PNG limpio", out_png, "mc_dtf_limpio.png", "image/png", use_container_width=True)
        with d2:
            if out_pdf:
                st.download_button("Descargar PDF", out_pdf, "mc_dtf_limpio.pdf", "application/pdf", use_container_width=True)
        if ht_img:
            st.image(ht_img, caption="Semitono", use_container_width=True)
            with d3:
                st.download_button("PNG semitono", ht_png, "mc_dtf_semitono.png", "image/png", use_container_width=True)
            with d4:
                if ht_pdf:
                    st.download_button("PDF semitono", ht_pdf, "mc_dtf_semitono.pdf", "application/pdf", use_container_width=True)

    except Exception as exc:
        status.error(f"Error: {exc}")
        st.exception(exc)
