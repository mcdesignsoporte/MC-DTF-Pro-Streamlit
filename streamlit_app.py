from __future__ import annotations

import time
from io import BytesIO

import streamlit as st
from PIL import Image

from core.background import has_useful_alpha, remove_background_ai
from core.clean import clean_alpha, preset_values, sharpen
from core.halftone import make_halftone
from core.image_utils import (
    add_print_canvas,
    image_to_pdf_bytes,
    image_to_png_bytes,
    open_uploaded_image,
    resize_for_ai,
    upscale_lanczos,
)
from core.preview import preview_on_background

st.set_page_config(
    page_title="MC DTF Pro",
    page_icon="🎨",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {font-size: 3rem; font-weight: 900; margin-bottom: 0;}
    .brand {color:#d9aa2f; font-weight:800; letter-spacing: .08em; text-transform:uppercase;}
    .small-note {color:#bdbdbd; font-size: .95rem;}
    .success-box {padding: .85rem 1rem; border: 1px solid #2e7d32; border-radius: 12px; background: rgba(46,125,50,.12)}
    .warn-box {padding: .85rem 1rem; border: 1px solid #d9aa2f; border-radius: 12px; background: rgba(217,170,47,.12)}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand">MC Creative Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">MC DTF Pro</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="small-note">Quita fondo, limpia semitransparencias, elimina píxeles basura y exporta PNG/PDF listo para DTF.</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Ajustes")
    mode = st.selectbox(
        "Preset",
        ["Caricatura / detalle fino", "Diseño normal DTF", "Logo fuerte / borde duro"],
        index=1,
    )
    default_alpha, default_area, default_contract = preset_values(mode)

    use_ai = st.checkbox("Quitar fondo con IA", value=True)
    skip_if_alpha = st.checkbox("Saltar IA si el PNG ya tiene transparencia", value=True)
    ai_max_side = st.slider("Tamaño máximo para IA", 900, 2500, 1800, 100)

    st.divider()
    alpha_cut = st.slider("Corte de transparencia", 1, 254, default_alpha)
    despeckle_area = st.slider("Quitar basura menor a", 1, 500, default_area)
    edge_contract = st.slider("Contraer borde", 0, 4, default_contract)

    st.divider()
    upscale = st.selectbox("Alta resolución", [1, 2, 3, 4], index=0, format_func=lambda x: "Original" if x == 1 else f"{x}x")
    do_sharpen = st.checkbox("Enfocar resultado", value=True)
    dpi = st.number_input("DPI", min_value=72, max_value=600, value=300, step=1)

    st.divider()
    st.subheader("Medida final opcional")
    width_cm = st.number_input("Ancho final cm", min_value=0.0, value=0.0, step=0.5)
    height_cm = st.number_input("Alto final cm", min_value=0.0, value=0.0, step=0.5)

    st.divider()
    generate_pdf = st.checkbox("Generar PDF", value=False)
    generate_halftone = st.checkbox("Generar semitono", value=False)
    dot_size = st.slider("Tamaño de punto", 4, 40, 8, disabled=not generate_halftone)
    angle = st.slider("Ángulo semitono", 0, 90, 15, disabled=not generate_halftone)
    invert_halftone = st.checkbox("Invertir semitono", value=False, disabled=not generate_halftone)

uploaded = st.file_uploader("Sube tu imagen", type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"])

if uploaded is None:
    st.info("Sube una imagen para empezar. Recomendación: usa 'Caricatura / detalle fino' para diseños con muchos detalles.")
    st.stop()

try:
    original = open_uploaded_image(uploaded)
except Exception as exc:
    st.error(f"No se pudo abrir la imagen: {exc}")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Original")
    st.image(original, use_container_width=True)
    st.caption(f"{original.width} × {original.height}px")

process = st.button("Procesar imagen", type="primary", use_container_width=True)

if process:
    start = time.perf_counter()
    progress = st.progress(0, text="Preparando imagen...")

    try:
        working = original.copy()

        progress.progress(10, text="Revisando transparencia...")
        should_use_ai = use_ai
        if skip_if_alpha and has_useful_alpha(working):
            should_use_ai = False

        progress.progress(25, text="Quitando fondo con IA..." if should_use_ai else "Saltando IA...")
        if should_use_ai:
            ai_img = resize_for_ai(working, max_side=ai_max_side)
            working = remove_background_ai(ai_img, enabled=True)

        progress.progress(50, text="Limpiando semitransparencias y píxeles basura...")
        working = clean_alpha(working, alpha_cut=alpha_cut, despeckle_area=despeckle_area, edge_contract=edge_contract)

        progress.progress(65, text="Aplicando medida final...")
        working = add_print_canvas(working, width_cm=width_cm, height_cm=height_cm, dpi=int(dpi))

        progress.progress(75, text="Escalando imagen...")
        working = upscale_lanczos(working, scale=upscale)

        if do_sharpen:
            progress.progress(85, text="Enfocando resultado...")
            working = sharpen(working)

        progress.progress(92, text="Preparando descargas...")
        png_bytes = image_to_png_bytes(working, dpi=int(dpi))
        pdf_bytes = image_to_pdf_bytes(working, dpi=int(dpi)) if generate_pdf else None

        halftone_img = None
        halftone_png = None
        halftone_pdf = None
        if generate_halftone:
            progress.progress(96, text="Generando semitono...")
            halftone_img = make_halftone(working, dot_size=dot_size, angle=angle, invert=invert_halftone)
            halftone_png = image_to_png_bytes(halftone_img, dpi=int(dpi))
            halftone_pdf = image_to_pdf_bytes(halftone_img, dpi=int(dpi)) if generate_pdf else None

        elapsed = time.perf_counter() - start
        progress.progress(100, text=f"Terminado en {elapsed:.1f} s")

        with col2:
            st.subheader("Resultado")
            bg_view = st.radio("Vista previa", ["Transparente", "Playera negra", "Playera blanca", "Fondo rojo"], horizontal=True)
            if bg_view == "Playera negra":
                st.image(preview_on_background(working, (0, 0, 0)), use_container_width=True)
            elif bg_view == "Playera blanca":
                st.image(preview_on_background(working, (255, 255, 255)), use_container_width=True)
            elif bg_view == "Fondo rojo":
                st.image(preview_on_background(working, (180, 0, 0)), use_container_width=True)
            else:
                st.image(working, use_container_width=True)
            st.caption(f"{working.width} × {working.height}px · {elapsed:.1f} s")

        st.markdown('<div class="success-box">Archivo procesado correctamente.</div>', unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.download_button("Descargar PNG", png_bytes, "mc_dtf_limpio.png", "image/png", use_container_width=True)
        with d2:
            if pdf_bytes:
                st.download_button("Descargar PDF", pdf_bytes, "mc_dtf_limpio.pdf", "application/pdf", use_container_width=True)
            else:
                st.caption("Activa PDF en la barra lateral")
        with d3:
            if halftone_png:
                st.download_button("PNG semitono", halftone_png, "mc_dtf_semitono.png", "image/png", use_container_width=True)
        with d4:
            if halftone_pdf:
                st.download_button("PDF semitono", halftone_pdf, "mc_dtf_semitono.pdf", "application/pdf", use_container_width=True)

        if halftone_img:
            st.subheader("Vista semitono")
            st.image(halftone_img, use_container_width=True)

    except Exception as exc:
        st.error(f"Error al procesar: {exc}")
        st.warning("Prueba con IA desactivada, baja el tamaño máximo para IA o usa una imagen más pequeña.")
else:
    with col2:
        st.subheader("Resultado")
        st.markdown('<div class="warn-box">Presiona “Procesar imagen” para generar el archivo DTF.</div>', unsafe_allow_html=True)
