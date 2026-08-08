# Maquetador ADG Media Group

Sistema web local que convierte informes PDF no estructurados en presentaciones editables de Google Slides, respetando el manual de identidad ADG.

## Arquitectura

```
PDF → Docling (extracción) → Gemini (mapeo JSON) → Google Slides API (inyección) → Presentación
```

| Módulo | Tecnología | Coste |
|--------|-----------|-------|
| Frontend | Streamlit | $0 |
| Extracción PDF | Docling (local) | $0 |
| Mapeo semántico | Gemini 2.5 Flash-Lite | $0 |
| Renderizado | Google Slides API | $0 |

## Requisitos

- Python 3.11+
- Mac M4 Pro (recomendado) o cualquier Mac/Linux con Python
- Cuenta Google con acceso a Google Cloud Console
- API Key de Gemini (Free Tier)

## Instalación

```bash
git clone https://github.com/mzaragozaserrano/lauzs.git
cd lauzs

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Editar .env con tus API keys e IDs
```

## Configuración Google Cloud

1. Crear proyecto en [Google Cloud Console](https://console.cloud.google.com/)
2. Habilitar **Google Slides API** y **Google Drive API**
3. Crear credenciales OAuth 2.0 (tipo **Desktop App**)
4. Descargar `credentials.json` a la raíz del proyecto
5. Subir `Plantilla_base_ADG` a Google Drive
6. Copiar el File ID de la plantilla a `GOOGLE_TEMPLATE_FILE_ID` en `.env`

## Configuración Gemini

1. Obtener API Key en [Google AI Studio](https://aistudio.google.com/)
2. Añadir a `.env`: `GEMINI_API_KEY=tu_key`

## Uso

```bash
streamlit run app.py
```

1. Abrir `http://localhost:8501`
2. Arrastrar el PDF del informe
3. Pulsar "Generar presentación"
4. Abrir el enlace a Google Slides

## Estructura del proyecto

```
lauzs/
├── app.py                    # Interfaz Streamlit
├── config/
│   ├── brand_guidelines.py   # Colores y tipografía ADG
│   └── settings.py           # Configuración centralizada
├── src/
│   ├── dla/                  # Extracción PDF (Docling)
│   ├── llm/                  # Mapeo semántico (Gemini)
│   ├── slides/               # Google Slides API
│   └── pipeline.py           # Orquestador
├── schemas/
│   └── template_schema.json  # Etiquetas Mustache de la plantilla
├── prompts/
│   └── system_prompt.txt     # Prompt para Gemini
├── docs/
│   ├── SDD_Maquetador_ADG.md      # Documento de diseño
│   └── reference/                 # Manual de identidad + plantilla base (PDF)
│       ├── manual_identidad_corporativa.pdf
│       ├── plantilla_base_adg.pdf
│       ├── manual_identidad_resumen.md
│       └── plantilla_estructura.md
└── ROADMAP.md                # Plan de desarrollo
```

## Principio de diseño

El código **no dibuja diapositivas**. Clona una plantilla pre-diseñada en Google Slides e inyecta datos via placeholders Mustache (`{{clave}}`). El 90% del cumplimiento del manual de identidad reside en la plantilla.

## Documentos de referencia

| Archivo | Ubicación |
|---------|-----------|
| Manual de Identidad Corporativa 2026 | `docs/reference/manual_identidad_corporativa.pdf` |
| Plantilla base de presentación | `docs/reference/plantilla_base_adg.pdf` |

Resúmenes en Markdown: `docs/reference/manual_identidad_resumen.md` y `docs/reference/plantilla_estructura.md`.

## Roadmap

Ver [ROADMAP.md](ROADMAP.md) para el plan de desarrollo por fases.

## Licencia

Uso interno — ADG Media Group.
