# Roadmap — Validador de Identidad ADG

> Herramienta interna ADG Media Group | v2.0

---

## Fase 1: Producto interno con login — Completada

- [x] FastAPI con auth Google Workspace + restricción de dominio
- [x] API `POST /validate/pdf`, `POST /validate/slides`
- [x] Frontend React con informes filtrables
- [x] PostgreSQL/SQLite para usuarios e historial

## Fase 2: Corrección automática en Slides — Completada

- [x] Extender `ValidationIssue` con metadatos de fix
- [x] Implementar `slides_fixer.py`
- [x] UI de corrección selectiva y copia en Drive
- [x] Re-validación post-fix
- [x] Export PDF/PPTX

## Fase 3: Pulido operativo — Completada

- [x] Historial por usuario
- [x] Informe PDF descargable
- [x] Vista previa de diapositiva (thumbnail Slides API)
- [x] Documentación para el equipo (`docs/manual_uso_equipo.md`)
- [x] Docker Compose para despliegue

## Fase 0: Validador Slides base — Completada

- [x] Reparar integración Google Slides (settings, imports, requirements)
- [x] CLI unificado `scripts/validate.py`
- [x] Tests automatizados

---

## Próximos pasos opcionales

- [ ] Despliegue en Cloud Run / VPS producción ADG
- [ ] Manejo robusto de colores `theme:*` en Slides
- [ ] Tests de integración con presentación Slides real
- [ ] Notificaciones por email al completar corrección

## Métricas de éxito

| Métrica | Objetivo |
|---------|----------|
| Coste mensual | < $70 (uso interno) |
| Tiempo validación | < 30 s por presentación |
| Precisión | > 95% detección de incumplimientos |
