# analisis_EPH

Proyecto de notebooks (Google Colab) de análisis de la EPH del INDEC.

## Documentos de contexto (LEER AL INICIAR SESIÓN, en este orden)

1. [`.claude/memoria.md`](.claude/memoria.md) — estado, pendientes, flujo para agregar
   trimestres, valores de referencia y reglas. **Empezar por el bloque ⭐ HANDOFF.**
2. [`docs/TECNICO.md`](docs/TECNICO.md) — pipeline de datos, API de `src/data_loader.py`,
   esquemas/tamaños por trimestre, gotchas resueltos y convenciones de análisis.
3. [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) — diccionario completo de variables
   (hogar y personas), claves de vínculo, ponderadores y quiebre de esquema 4T2023.
   Consultar antes de tocar cualquier notebook de análisis.

## Estado (2026-09-29)

7 notebooks validados en Colab (00 compilador + 01 demografía, 02 laboral, 03 ingresos,
04 vivienda, 05 educación, 06 termómetro 0-100, índice v3 con lectura automática, promedios
anuales y controles de calidad) con **37 trimestres
T1-2017 → T1-2026**. Pendientes e ideas en el HANDOFF de la memoria.
Datos: `.zip` del INDEC en Google Drive (`carga_EPH`), compilados a parquets por
trimestre en `carga_EPH/processed`. Los datos NO están en el repo: viven en el Drive del
usuario; el código corre en Colab, así que cambiar de PC solo requiere clonar el repo.

## Reglas

- Commits sin atribución de Claude (nada de `Co-Authored-By: Claude`); solo el usuario
  Santiago Riverti (`santiagoriverti`).
- Los cambios de código solo llegan a Colab tras `git push` a `main` (los notebooks
  clonan el repo público).
- Las bases pesadas de EPH no se commitean (`data/raw/*.zip` ignorado).
- Actualizar `.claude/memoria.md` (HANDOFF + historial) al finalizar cada sesión.
- Editar notebooks vía JSON (`json.load`/`json.dump`), no con `sed` sobre el `.ipynb`.
- **El notebook 06 se genera** con `tools/gen_06_termometro.py`: editar el script y
  regenerar (`python tools/gen_06_termometro.py`), nunca el `.ipynb` directo.
- No hay datos EPH en el repo ni en la PC (salvo copias sueltas): los resultados reales
  salen de correr en Colab; el usuario pega las salidas en el chat.
- En Windows, evitar heredocs largos con backticks en bash: escribir scripts a archivo.
