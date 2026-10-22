# analisis_EPH

Proyecto de notebooks (Google Colab) de análisis de la EPH del INDEC.

## Documentos de contexto (LEER AL INICIAR SESIÓN, en este orden)

1. [`.claude/memoria.md`](.claude/memoria.md) — estado, pendientes, flujo para agregar
   trimestres, valores de referencia y reglas. **Empezar por el bloque ⭐ HANDOFF.**
2. [`docs/TECNICO.md`](docs/TECNICO.md) — pipeline de datos, API de `src/data_loader.py`,
   esquemas/tamaños por trimestre, gotchas resueltos, convenciones de análisis y detalle de
   los notebooks 06 (termómetro, §6), 07 (nowcast, §7) y 08 (adultos mayores, §8).
3. [`docs/NOWCAST.md`](docs/NOWCAST.md) — rutina del nowcast (07): cuándo correrlo, qué
   mantener (bono previsional mensual, respaldos), qué revisar, qué hacer cuando sale una EPH.
4. [`docs/JUBILADOS.md`](docs/JUBILADOS.md) — rutina del 08 (adultos mayores y jubilados): cómo
   correrlo y validarlo, qué revisar, valores de referencia, cuidados al leer los resultados,
   límites de la EPH y mejoras pendientes.
5. [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) — diccionario completo de variables
   (hogar y personas), claves de vínculo, ponderadores y quiebre de esquema 4T2023 (§10: las
   variables del 08). Consultar antes de tocar cualquier notebook de análisis.

## Estado (2026-10-22)

9 notebooks: 00 compilador + 01 demografía, 02 laboral, 03 ingresos, 04 vivienda, 05 educación,
06 termómetro 0-100 (v4), **07 nowcast del termómetro** (D por microsimulación, A, B y C por
ecuaciones puente; backtest, robustez y registro de versiones) y **08 adultos mayores y jubilados**
(varones 65+, mujeres 60+: convivencia, jubilación, ingresos, pobreza, trabajo, vivienda; con IC
bootstrap, por región y aglomerado, evolución y Excel/CSV/PNG/ZIP), con **37 trimestres T1-2017 →
T1-2026**. 00-06 validados en Colab; el 07 validado en Colab hasta el termómetro completo
(2026-10-21; falta correr en Colab su sección 7 y el gráfico `nowcast_05_evolucion`). El 08
(2026-10-22) está validado en Colab (idéntico a la corrida local). El T2-2026 de la
EPH todavía no estaba publicado. Pendientes en el HANDOFF de la memoria.

Datos: `.zip` del INDEC en Google Drive (`carga_EPH`), compilados a parquets por trimestre en
`carga_EPH/processed`; salidas en `carga_EPH/resultados/` (06), `carga_EPH/resultados/nowcast/`
(07, incluido el registro de versiones) y `carga_EPH/resultados/jubilados/` (08). Los datos NO
están en el repo: viven en el Drive del usuario; el código corre en Colab, así que cambiar de PC
solo requiere clonar el repo.

## Reglas

- Commits sin atribución de Claude (nada de `Co-Authored-By: Claude`); solo el usuario
  Santiago Riverti (`santiagoriverti`).
- Los cambios de código solo llegan a Colab tras `git push` a `main` (los notebooks
  clonan el repo público).
- Las bases pesadas de EPH no se commitean (`data/raw/*.zip` y `data/processed/*` ignorados).
- Actualizar `.claude/memoria.md` (HANDOFF + historial) al finalizar cada sesión.
- Editar notebooks vía JSON (`json.load`/`json.dump`), no con `sed` sobre el `.ipynb`.
- **El notebook 06 se genera** con `tools/gen_06_termometro.py`: editar el script y
  regenerar (`python tools/gen_06_termometro.py`), nunca el `.ipynb` directo.
- **El notebook 07 se genera** con `tools/gen_07_nowcast.py`; su lógica vive en `src/nowcast.py`
  (las fórmulas de D, `DIMENSIONES` y la normalización son copias de las del 06; A, B y C se leen
  del CSV del 06: si cambia el 06, cambiar las dos y verificar con el control de la sección 3
  del 07). Orden: correr el 06 antes que el 07. Si cambia el método del nowcast, cambiar
  `VERSION` en el generador. Ver `docs/TECNICO.md` §7 y `docs/NOWCAST.md`.
- **El notebook 08 se genera** con `tools/gen_08_jubilados.py`; su lógica vive en
  `src/jubilados.py` (definiciones, `preparar`, `estimar`/`distribucion` con bootstrap, gráficos y
  exportación). Probar con `python tools/probar_08_local.py` (~3 min): la sección 15 tiene que dar
  todo ✓ (incluida la réplica de la pobreza oficial). Ver `docs/TECNICO.md` §8 y `docs/JUBILADOS.md`.
- No hay datos EPH en el repo. En la PC se pueden tener los datos reales:
  `python tools/probar_06_local.py --descargar` baja los zips del INDEC a `data/raw/`, compila
  a `data/processed/` (ambos ignorados) y corre el 06; `python tools/probar_07_local.py` corre
  el 07 (~5 min) y `python tools/probar_08_local.py` el 08 (~3 min). Para los demás notebooks,
  Colab sigue siendo la referencia (el usuario pega las salidas en el chat). Validar en Colab =
  comparar los CSV que el usuario baja de Drive contra los de `data/processed/resultados_06/`
  (deben coincidir salvo redondeo ~1e-10); para el 08, con el ZIP que descarga el notebook:
  `python -X utf8 tools/comparar_zip_08.py <ruta al ZIP>`.
- El registro de versiones del nowcast (`carga_EPH/resultados/nowcast/registro_versiones.csv`,
  en Drive) es el único estado que no se puede regenerar: no borrarlo.
- En Windows, evitar heredocs largos con backticks en bash: escribir scripts a archivo. Usar
  `PYTHONUTF8=1` o `python -X utf8` (`python -I` ignora `PYTHONUTF8`).
