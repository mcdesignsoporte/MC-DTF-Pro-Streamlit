# MC DTF Pro Streamlit

Herramienta web gratuita para preparar imágenes DTF desde Streamlit Community Cloud.

## Funciones

- Quitar fondo con IA usando rembg.
- Saltar IA si el PNG ya tiene transparencia.
- Limpieza de semitransparencias.
- Eliminación de píxeles basura.
- Presets para caricatura, diseño normal y logo fuerte.
- Exportación PNG transparente.
- Exportación PDF opcional.
- Semitonos opcionales.
- Vista previa sobre fondo transparente, negro, blanco y rojo.

## Archivos importantes

```text
streamlit_app.py
requirements.txt
core/
assets/
examples/
.streamlit/config.toml
.gitignore
README.md
```

## Despliegue en Streamlit Community Cloud

1. Sube todos los archivos a GitHub.
2. Entra a Streamlit Community Cloud.
3. Create app.
4. Repository: tu repositorio.
5. Branch: main.
6. Main file path: streamlit_app.py.
7. Deploy.

## Uso recomendado

Para diseños con muchos detalles:

- Preset: Caricatura / detalle fino
- IA: activada
- Tamaño máximo para IA: 1800
- PDF: desactivado hasta necesitarlo
- Semitono: desactivado hasta el final

## MC Creative Studio

Software de autoría propia para flujo DTF de MC Creative Studio.
