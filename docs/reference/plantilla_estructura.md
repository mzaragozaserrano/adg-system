# Estructura — Plantilla base ADG

> Fuente: `plantilla_base_adg.pdf`

## Tipos de diapositiva

| # | Tipo | Contenido editable | Placeholder Mustache |
|---|------|-------------------|---------------------|
| 1 | Portada A | Título + subtítulo | `{{titulo_presentacion}}`, `{{subtitulo_presentacion}}` |
| 2 | Portada B | Título + subtítulo (variante) | `{{titulo_presentacion}}`, `{{subtitulo_presentacion}}` |
| 3 | Índice | 6 apartados numerados | `{{contenido_01}}` … `{{contenido_06}}` |
| 4 | Informe | Título + periodo | `{{informe_titulo}}`, `{{informe_periodo}}` |
| 5 | Separador | Título + subtítulo sección | `{{separador_titulo}}`, `{{separador_subtitulo}}` |
| 6 | Cierre | Contacto | `{{contacto}}` |

Elementos estáticos (no reemplazar via API): logotipos, fondos corporativos, tipografía, "¡Muchas gracias!".

## Formato del índice

Cada entrada del índice sigue el patrón:

```
01. Título: Subtítulo
```

Ejemplo placeholder en plantilla: `XXXXXXXX: XXXXXXXXXXX`

## Campos adicionales (informes comerciales)

Para documentos tipo Total Reach / propuestas de medios, la plantilla Google Slides debe incluir diapositivas con KPIs:

| Placeholder | Ejemplo |
|-------------|---------|
| `{{inversion_essential}}` | 15.000 € |
| `{{inversion_advanced}}` | 20.000 € |
| `{{inversion_elite}}` | 30.000 € |
| `{{cpm_objetivo_essential}}` | 3,50 € |
| `{{cpm_objetivo_advanced}}` | … |
| `{{cpm_objetivo_elite}}` | … |
| `{{alcance_essential}}` | … |
| `{{alcance_advanced}}` | … |
| `{{alcance_elite}}` | … |
| `{{impresiones_essential}}` | … |
| `{{impresiones_advanced}}` | … |
| `{{impresiones_elite}}` | … |
| `{{tabla_inversion_markdown}}` | Tabla completa |
| `{{resumen_ejecutivo}}` | Texto libre |
| `{{cliente}}` | Nombre cliente |
| `{{filial}}` | ad_gravity / la_naranja_mecanica / neural_one / adg |

Estos campos deben añadirse a la versión Google Slides de la plantilla como cajas de texto con formato predefinido.

## Regla crítica

Al reemplazar texto con `ReplaceAllTextRequest`, el formato (fuente, color, tamaño) se hereda de la caja de texto en la plantilla. Nunca crear slides ni modificar estilos desde código.
