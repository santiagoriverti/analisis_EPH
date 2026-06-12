# analisis_EPH

Proyecto de notebooks de análisis de la EPH (INDEC). Ver [`.claude/memoria.md`](.claude/memoria.md)
para contexto, decisiones de arquitectura y próximos pasos.

## Reglas

- Commits sin atribución de Claude (solo usuario `santiagoriverti`).
- Las bases pesadas de EPH no se commitean salvo que sean trimestres "nuevos" sin
  soporte en `pyeph`, en cuyo caso van a `data/raw/`.
- Actualizar `.claude/memoria.md` al finalizar cada sesión con el estado y próximos pasos.
