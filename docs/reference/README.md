# Documentos de referencia ADG

Archivos oficiales de marca y plantilla. Son la fuente de verdad visual del proyecto.

| Archivo | Descripción |
|---------|-------------|
| `manual_identidad_corporativa.pdf` | Manual de Identidad Corporativa 2026: colores, tipografía, logotipos, valores |
| `plantilla_base_adg.pdf` | Plantilla base de presentación: estructura de diapositivas y campos editables |

## Uso en el proyecto

- **Manual de identidad** → alimenta `config/brand_guidelines.py` y las reglas de Cursor
- **Plantilla base** → define la estructura de diapositivas y las etiquetas Mustache en Google Slides

El código no diseña diapositivas. Clona la plantilla en Google Drive (versión editable) e inyecta datos respetando el formato predefinido.

## Documentación derivada

- [manual_identidad_resumen.md](manual_identidad_resumen.md) — paleta, tipografía y reglas extraídas del manual
- [plantilla_estructura.md](plantilla_estructura.md) — tipos de diapositiva y placeholders

## Google Slides vs PDF

El PDF de plantilla es referencia visual. La versión operativa debe estar en Google Drive con etiquetas Mustache (`{{clave}}`) en cada campo editable. Sincronizar el File ID en `.env` como `GOOGLE_TEMPLATE_FILE_ID`.
