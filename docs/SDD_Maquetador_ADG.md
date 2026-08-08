# Software Design Document (SDD)
## Sistema Automatizado de Maquetación en Google Slides (Versión Local / Free Tier)

**Organización:** ADG Media Group  
**Fecha:** Agosto 2026

---

## 1. Visión General del Proyecto

Creación de un sistema web local (ejecutado en Mac M4 Pro) capaz de recibir documentos no estructurados (ej. informe "Total Reach Black Friday") y convertirlos en presentaciones editables de Google Slides.

El sistema operará bajo el paradigma de **"Combinación de Datos" (Data Merge)**, clonando una plantilla pre-diseñada para asegurar el cumplimiento estricto del manual de identidad (tipografía Helvetica Neue, colores corporativos, logos) sin incurrir en costes de APIs comerciales.

---

## 2. Gestión del Manual de Identidad y Plantilla Base (CRÍTICO)

Para mantener el coste a cero y garantizar la fidelidad visual, el diseño y el código están estrictamente separados. **El código NO dibuja diapositivas desde cero; inyecta datos en plantillas pre-formateadas.**

### 2.1 El Rol de la Plantilla (`Plantilla_base_ADG.pdf` / Slides)

El 90% del cumplimiento del Manual de Identidad reside físicamente en un archivo matriz de Google Slides alojado en Google Drive.

- **Tipografía y Color:** Las "Diapositivas Maestras" (Slide Masters) del archivo ya tienen aplicada la fuente **Helvetica Neue** y los fondos corporativos (*Petrol Blue, Blanco, Platino*).
- **Logotipos:** Las cabeceras, pies de página y el logo unificado de ADG Media Group son estáticos en la plantilla.
- **Etiquetas Mustache (Placeholders):** El documento contiene cajas de texto formateadas con llaves dobles. Ejemplos: `{{inversion_essential}}`, `{{cpm_objetivo_elite}}`, `{{titulo_slide}}`. Cuando la API reemplace estos textos, heredarán automáticamente el diseño.

### 2.2 El Diccionario de Marca en el Código (Python)

Para las decisiones dinámicas que deba tomar el código (ej. cambiar un logotipo o el color de un gráfico si el documento habla de una filial específica), el backend contendrá un diccionario estático en memoria:

```python
# config/brand_guidelines.py
ADG_COLORS = {
    "petrol_blue": "#02445B",
    "blanco": "#F6F6F6",
    "platino": "#CECECD",
    "obsidian_blue": "#01222E",
    "azul_digital": "#005C7F",
    "acero_glaciar": "#6A96A6"
}

SUBSIDIARY_COLORS = {
    "ad_gravity": "#047DBC",
    "la_naranja_mecanica": "#F18E5D",
    "neural_one": "#75BA91"
}
```

---

## 3. Arquitectura del Sistema (Coste Cero)

Diseñado para baja concurrencia (1 usuario, ~3 docs/semana) utilizando el hardware local del Apple M4 Pro.

1. **Frontend (UI):** `Streamlit` ejecutado en `localhost`. El trabajador arrastra el PDF original.
2. **Módulo DLA (Extracción Física):**
   - Librería: `docling` (o `marker-pdf`).
   - Ejecución: Local. Aprovechando el motor neuronal y la memoria unificada del chip M4 Pro para extraer las tablas de los "Paquetes Essential, Advanced, Elite" sin perder las columnas.
3. **Módulo LLM (El "Cerebro" Semántico):**
   - Librería: `google-generativeai` (Gemini API).
   - Modelo: **Gemini 2.5 Flash-Lite** (Free Tier).
   - Función: Recibe el texto extraído por Docling y se le proporciona un diccionario con las etiquetas exactas de la `Plantilla_base_ADG`. Su única tarea es devolver un JSON asociando los datos del PDF a las etiquetas de la plantilla.
4. **Módulo Renderizador (Google Slides API):**
   - Clona la plantilla base (`files().copy`).
   - Realiza un `batchUpdate` masivo con `ReplaceAllTextRequest`.

---

## 4. Ingeniería de la Inyección de Datos (Google Slides API)

El corazón de la generación de la presentación reside en el empaquetado de peticiones para no superar la cuota gratuita de 60 peticiones/minuto.

```python
def generate_slides_requests(llm_json_data):
    requests = []
    for key, value in llm_json_data.items():
        requests.append({
            'replaceAllText': {
                'containsText': {
                    'text': f'{{{{{key}}}}}',
                    'matchCase': True
                },
                'replaceText': str(value)
            }
        })
    return requests
```

---

## 5. Roadmap de Desarrollo

Ver [ROADMAP.md](../ROADMAP.md) para el plan detallado por fases.

| Fase | Días | Objetivo |
|------|------|----------|
| 1 | 1-2 | Entorno y conexiones |
| 2 | 3-4 | Módulo DLA local |
| 3 | 5-6 | Prompts y mapeo Gemini |
| 4 | 7-9 | Manipulación Google Slides |
| 5 | 10 | Interfaz web y despliegue |

---

## 6. Métricas de Éxito

| Métrica | Objetivo |
|---------|----------|
| Coste mensual | $0 |
| Tiempo generación | < 2 min por documento |
| Fidelidad visual | 100% manual de identidad |
| Peticiones API | 1-2 por documento |
