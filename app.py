import json
import tempfile
from pathlib import Path

import streamlit as st

from config.settings import settings
from src.pipeline import MaquetadorPipeline

st.set_page_config(
    page_title="Maquetador ADG",
    page_icon="📊",
    layout="centered",
)

st.title("Maquetador ADG Media Group")
st.caption("Convierte informes PDF en presentaciones Google Slides")

uploaded_file = st.file_uploader(
    "Arrastra el PDF del informe",
    type=["pdf"],
    help="Ej. Total Reach Black Friday, propuestas de medios ADG",
)

presentation_name = st.text_input(
    "Nombre de la presentación (opcional)",
    placeholder="Dejar vacío para generar automáticamente",
)

if st.button("Generar presentación", type="primary", disabled=uploaded_file is None):
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".pdf", dir=settings.uploads_dir
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        pdf_path = Path(tmp.name)

    try:
        with st.spinner("Extrayendo datos del PDF..."):
            pipeline = MaquetadorPipeline()

        progress = st.progress(0, text="Extrayendo tablas con Docling...")
        progress.progress(33, text="Mapeando KPIs con Gemini...")
        result = pipeline.run(pdf_path, presentation_name or None)
        progress.progress(100, text="Presentación generada")

        st.success("Presentación creada correctamente")
        st.link_button("Abrir en Google Slides", result["url"])

        with st.expander("Datos mapeados (JSON)"):
            st.json(result["mapped_data"])

        with st.expander("Texto extraído (Markdown)"):
            st.markdown(result["extracted_text"])

    except Exception as e:
        st.error(f"Error durante la generación: {e}")
    finally:
        pdf_path.unlink(missing_ok=True)

with st.sidebar:
    st.header("Configuración")
    st.markdown(
        """
        **Requisitos:**
        - `credentials.json` (OAuth Google)
        - `.env` con API keys
        - Plantilla en Google Drive

        Ver [README.md](README.md) para setup.
        """
    )
    if settings.template_schema_path.exists():
        with open(settings.template_schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        st.caption(f"Etiquetas de plantilla: {len(schema.get('properties', {}))}")
