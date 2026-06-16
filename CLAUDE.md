# analisis_EPH

Proyecto de notebooks de análisis de la EPH (INDEC).

## Documentos de contexto (LEER AL INICIAR SESIÓN)

- [`.claude/memoria.md`](.claude/memoria.md) — estado del proyecto, decisiones de
  arquitectura, gotchas resueltos y próximos pasos. **Empezar por el bloque ⭐ HANDOFF.**
- [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) — diccionario completo de variables
  de las bases hogar y personas (significado/valores), claves de vínculo, ponderadores y
  el quiebre de esquema de 4T2023. Consultar antes de tocar cualquier notebook de análisis.

## Estado (2026-06-12)

Proyecto **completo**: 6 notebooks validados en Colab (00 compilador + 01 demografía,
02 laboral, 03 ingresos, 04 vivienda, 05 educación). Datos: `.zip` del INDEC en Google
Drive (`carga_EPH`), compilados a parquets por trimestre en `carga_EPH/processed`. Los
notebooks 01-05 leen con `load_panel(...)` (copiando antes de Drive a disco local).

## Reglas

- Commits sin atribución de Claude (solo usuario `santiagoriverti`).
- Las bases pesadas de EPH no se commitean salvo que sean trimestres "nuevos" sin
  soporte en `pyeph`, en cuyo caso van a `data/raw/`.
- Actualizar `.claude/memoria.md` al finalizar cada sesión con el estado y próximos pasos.
