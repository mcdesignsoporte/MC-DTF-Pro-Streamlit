from __future__ import annotations

from PIL import Image
import streamlit as st


@st.cache_resource(show_spinner=False)
def get_rembg_remove():
    from rembg import remove
    return remove


def has_useful_alpha(img: Image.Image) -> bool:
    if img.mode != "RGBA":
        return False
    alpha = img.getchannel("A")
    extrema = alpha.getextrema()
    return extrema[0] < 255


def remove_background_ai(img: Image.Image, enabled: bool = True) -> Image.Image:
    if not enabled:
        return img.convert("RGBA")
    remove = get_rembg_remove()
    return remove(img.convert("RGBA")).convert("RGBA")
