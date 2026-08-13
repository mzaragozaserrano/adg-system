# Software Design Document (SDD)
## Validador de Identidad Corporativa ADG

**Organización:** ADG Media Group  
**Fecha:** Agosto 2026

---

## 1. Visión General

Sistema web local que recibe una presentación (enlace de Google Slides o archivo PDF) y valida automáticamente el cumplimiento del manual de identidad corporativa ADG.

En caso de incumplimiento, muestra en qué diapositiva se produce cada error y qué regla se ha violado.

---

## 2. Reglas de Validación

### 2.1 Tipografía

Toda la tipografía debe ser **Helvetica** (o Elvética / Helvetica Neue).

### 2.2 Colores de texto

| Rol | Color | HEX | Peso |
|-----|-------|-----|------|
| Títulos (headers) | Petrol Blue | `#02445B` | Bold |
| Subtítulos | Obsidian Blue | `#01222E` | Light |
| Cuerpo | Negro | `#000000` | Regular |

### 2.3 Paleta de colores de diapositiva

Todos los colores de fondo, formas y elementos gráficos deben pertenecer a:

| Nombre | HEX |
|--------|-----|
| Petrol Blue | `#02445B` |
| Blanco | `#F6F6F6` |
| Platino | `#CECECD` |
| Obsidian Blue | `#01222E` |
| Azul Digital | `#005C7F` |
| Acero Glaciar | `#6A96A6` |

También se permiten blanco puro (`#FFFFFF`) y negro (`#000000`) para texto.

---

## 3. Arquitectura

```
Entrada (URL Slides / PDF) → Validador → Informe de errores por diapositiva
```

| Módulo | Tecnología | Coste |
|--------|-----------|-------|
| Frontend | Streamlit + CSS ADG | $0 |
| Validador Slides | Google Slides API (readonly) | $0 |
| Validador PDF | PyMuPDF | $0 |

---

## 4. Salida de Errores

Cada incumplimiento genera un `ValidationIssue`:

```json
{
  "slide": 3,
  "category": "color_texto",
  "message": "Color incorrecto en texto de tipo «header»",
  "expected": "Helvetica Bold, color #02445B",
  "actual": "#FF0000, fuente Arial",
  "text_preview": "Título de la presentación"
}
```

---

## 5. Roadmap

Ver [ROADMAP.md](../ROADMAP.md).

---

## 6. Documentos de Referencia

- `docs/reference/manual_identidad_corporativa.pdf` — Manual de identidad 2026
- `config/brand_guidelines.py` — Reglas en código
