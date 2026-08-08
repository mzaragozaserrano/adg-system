# Roadmap — Maquetador ADG Media Group

> Sistema automatizado de maquetación en Google Slides (versión local / Free Tier)
> Hardware objetivo: Mac M4 Pro | Concurrencia: 1 usuario, ~3 docs/semana

---

## Fase 1: Entorno y Conexiones (Días 1-2)

**Estado:** En progreso

### Tareas

- [x] Inicializar repositorio y estructura de proyecto
- [x] Definir `requirements.txt` con dependencias core
- [x] Crear `config/settings.py` y `config/brand_guidelines.py`
- [x] Crear esquema JSON de plantilla (`schemas/template_schema.json`)
- [ ] Crear entorno virtual Python 3.11+
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Configurar Google Cloud Console (proyecto ADG, coste $0)
  - [ ] Habilitar Google Slides API
  - [ ] Habilitar Google Drive API
  - [ ] Crear credenciales OAuth 2.0 (Desktop App)
  - [ ] Descargar `credentials.json` a la raíz del proyecto
- [ ] Obtener API Key gratuita de Gemini en [Google AI Studio](https://aistudio.google.com/)
- [ ] Configurar `.env` desde `.env.example`
- [ ] Subir `Plantilla_base_ADG` a Google Drive y copiar File ID

### Criterio de aceptación

Autenticación OAuth funcional y variables de entorno configuradas.

---

## Fase 2: Módulo DLA Local (Días 3-4)

**Estado:** Pendiente

### Tareas

- [x] Implementar `src/dla/extractor.py` con Docling
- [ ] Probar extracción con PDF de referencia: `Total_Reach_Black_Friday_2026_(19).pptx (1).pdf`
- [ ] Validar tablas de inversión (15k, 20k, 30k) en Markdown
- [ ] Verificar preservación de columnas: CPM, alcance, impresiones
- [ ] Optimizar rendimiento en Apple Silicon (M4 Pro)
- [ ] Documentar casos edge (PDFs escaneados, tablas rotas)

### Criterio de aceptación

Extracción Markdown fiel de tablas Essential/Advanced/Elite desde el PDF de prueba.

---

## Fase 3: Prompts y Mapeo Gemini (Días 5-6)

**Estado:** Pendiente

### Tareas

- [x] Definir esquema JSON basado en etiquetas `Plantilla_base_ADG`
- [x] Crear system prompt en `prompts/system_prompt.txt`
- [x] Implementar `src/llm/mapper.py`
- [ ] Ajustar esquema JSON con etiquetas reales de la plantilla Slides
- [ ] Iterar prompt con PDFs reales de ADG
- [ ] Validar output JSON contra schema (Pydantic)
- [ ] Manejar respuestas malformadas del LLM

### Criterio de aceptación

Gemini devuelve JSON válido mapeando KPIs del PDF a todas las etiquetas Mustache.

---

## Fase 4: Manipulación Google Slides (Días 7-9)

**Estado:** Pendiente

### Tareas

- [x] Implementar OAuth en `src/slides/auth.py`
- [x] Implementar clonación de plantilla (`files().copy`)
- [x] Implementar generador `ReplaceAllTextRequest`
- [x] Implementar exponential backoff
- [ ] Probar clonación con plantilla real en Drive
- [ ] Verificar que placeholders se reemplazan manteniendo formato
- [ ] Probar con filiales (ad_gravity, la_naranja_mecanica, neural_one)
- [ ] Validar cuota API (1 batchUpdate = 1 petición)

### Criterio de aceptación

Presentación clonada con todos los placeholders reemplazados y diseño intacto.

---

## Fase 5: Interfaz Web y Despliegue Local (Día 10)

**Estado:** Pendiente

### Tareas

- [x] Crear `app.py` con Streamlit (drag & drop PDF)
- [x] Unificar pipeline en `src/pipeline.py`
- [ ] Pulir UX: barra de progreso, mensajes de error claros
- [ ] Añadir preview del JSON mapeado antes de generar
- [ ] Documentar comando de arranque: `streamlit run app.py`
- [ ] Prueba end-to-end con documento real ADG
- [ ] Entregar manual de uso al equipo de maquetación

### Criterio de aceptación

El trabajador sube un PDF, pulsa un botón y obtiene enlace a Google Slides editable.

---

## Backlog futuro (post-MVP)

- [ ] Soporte para múltiples plantillas (por tipo de informe)
- [ ] Validación Pydantic del JSON de Gemini
- [ ] Historial de presentaciones generadas
- [ ] Fallback a `marker-pdf` si Docling falla
- [ ] Tests automatizados con PDFs de referencia
- [ ] Colores dinámicos de gráficos por filial via API

---

## Métricas de éxito

| Métrica | Objetivo |
|---------|----------|
| Coste mensual | $0 |
| Tiempo generación | < 2 min por documento |
| Fidelidad visual | 100% manual de identidad |
| Peticiones API | 1-2 por documento |
