# Memoria del proyecto: analisis_EPH

> Documento de continuidad entre sesiones de Claude Code (y entre PCs). Leer primero el
> bloque **HANDOFF**. Detalle técnico en [`docs/TECNICO.md`](../docs/TECNICO.md); rutina del
> nowcast en [`docs/NOWCAST.md`](../docs/NOWCAST.md); rutina del notebook 08 (adultos mayores) en
> [`docs/JUBILADOS.md`](../docs/JUBILADOS.md); diccionario de variables en
> [`memoria_EPH.md`](memoria_EPH.md).

## ⭐ HANDOFF (última sesión: 2026-10-22)

**Estado: todo commiteado y pusheado a `main`, sin trabajo a medias.** Notebook 08 (adultos mayores
y jubilados) creado y **validado en Colab** el 2026-10-22 (commit e2a23a3: las 38 tablas, el resumen y
los 20 gráficos idénticos a la corrida local, dif. relativa máx. 5e-16; sección 15 toda ✓; nota de
validación en 00fcec4). Al cierre se consolidó la documentación para seguir en otra PC: guía
[`docs/JUBILADOS.md`](../docs/JUBILADOS.md) y `tools/comparar_zip_08.py` (validación del ZIP de Colab).
El 06 y el 07 no cambiaron desde el 2026-10-21.
- **08 (2026-10-22):** pedido del usuario: situación demográfica de los adultos mayores (varones 65+,
  mujeres 60+), cómo viven, si cobran jubilación y cuánto, ingresos, si viven con sus hijos o los
  hijos con ellos según quién es jefe de hogar. Decisiones del usuario: foto con los **últimos 4
  trimestres**, **pobreza e indigencia con CBT/CBA** (metodología INDEC), comparar con el resto de la
  población, tramos de edad, pre-jubilables, región y **aglomerado**; incluir trabajo, vivienda,
  estrategias del hogar, salud/educación/viudez; **IC bootstrap + marcas de calidad**; salidas
  **Excel + CSV + PNG + ZIP**. Ver sección "Adultos mayores (notebook 08)" abajo.
- **Devolución del 08 (2026-10-22):** sólido y validado; cuidados de lectura (pobreza de los AM baja
  en parte por la escala de adulto equivalente y la vivienda propia, 23,1% apenas arriba de la línea;
  cobertura = piso; "menos de la mínima" no verificable) y límites de la EPH (solo hijos convivientes,
  sin rural ni geriátricos). Mejoras evaluadas (vulnerabilidad `ITF_EN_LP`, ayuda de no convivientes
  `V12_M`, mujeres de 60-64 por edad simple tras el fin de la moratoria, deflactar con el IPC de
  jubilados, tipo de beneficio en la serie): **el usuario dijo "por ahora no"; no hacerlas sin que
  lo pida.** Detalle con cifras en `docs/JUBILADOS.md` §7-9.
- Notebooks 00-06 validados en Colab con 37 trimestres (T1-2017 → T1-2026). El termómetro v4 (06)
  no cambió desde el 2026-10-06.
- **07 (nowcast del termómetro completo):** validado en Colab el 2026-10-21 hasta el commit
  4631093 (backtest, resumen y nowcast idénticos a la corrida local, dif. máx. 7e-11). Después se
  sumaron, probados en la PC con datos reales: la **sección 7 de robustez** (commit 1064dcf) y el
  **gráfico `nowcast_05_evolucion`** (evolución del termómetro con la proyección; último commit de
  la sesión). **Falta correrlos en Colab.**
- **Registro de versiones en Drive** (`carga_EPH/resultados/nowcast/registro_versiones.csv`): 69
  filas del 2026-10-21 (60 de `termómetro v1` + 9 de `D-microsim v1`, D igual en las dos). Base
  2026T1 = 52,8: **2026T2 = 62,8 (IC 54,5-71,1), 2026T3 = 58,6 (44,8-72,4), 2026T4 = 54,1
  (36,8-71,4)**; interanual +12,0 / +12,5 / +4,6 (la suba contra el T1 es sobre todo estacional).
- **La EPH del T2-2026 seguía sin publicarse el 2026-10-21** (la URL habitual del INDEC devuelve
  HTML; normalmente sale ~85 días después del trimestre: revisar si cambió el nombre del archivo).

**Cómo retomar (en cualquier PC):**
1. Clonar el repo (README, "Continuar en otra PC") y leer este HANDOFF, `docs/NOWCAST.md`,
   `docs/JUBILADOS.md` y `docs/TECNICO.md` §6-8.
2. `pip install -r requirements.txt`. Datos reales en la PC (opcional):
   `python tools/probar_06_local.py --descargar` (baja los zips del INDEC, compila y corre el 06),
   después `python tools/probar_07_local.py` (~5 min) y `python tools/probar_08_local.py` (~3 min).
3. En Colab: correr el 06 y después el 07 (el 07 lee del CSV del 06). El 08 es independiente; para
   validarlo, bajar su ZIP y correr `python -X utf8 tools/comparar_zip_08.py <ruta al ZIP>` después
   de `probar_08_local.py` con el mismo commit.

**Próximo paso inmediato:** correr 06 + 07 en Colab para validar la sección 7 del 07 y su gráfico
nuevo (el 08 ya está validado).

**Pendientes (en orden):**
1. **Cuando salga el T2-2026:** subir el zip → 00 → 06 → 07 → 08. El registro concilia las versiones
   del 21/10: primer error real (comparar con el RMSE del backtest; ver `docs/NOWCAST.md` §5). La foto
   del 08 pasa sola a T3-2025 a T2-2026; si faltara la canasta regional de algún mes, la estima con la
   nacional y lo avisa en la sección 15 (al 2026-10-22 las regionales llegaban hasta jun-2026).
2. Correr el 07 cuando salen sus series (IPC ~día 14, salarios ~45 días, EMAE ~55, SIPA ~100,
   confianza del consumidor a fin de mes) para acumular versiones.
3. **Mantenimiento mensual:** fila nueva en `data/bono_previsional.csv` (última: 2026-10; también en
   `IPC_jubilados/data/reference/`; lo usan el 07 y el 08). De vez en cuando: `nc.actualizar_respaldo`,
   el respaldo del IPC del 06 (`docs/NOWCAST.md` §6) y los del 08 (`python -X utf8
   tools/probar_08_local.py --respaldos`: canastas por región y pobreza oficial).
4. Serie mensual del termómetro (trimestre móvil con Chow-Lin) y actualización semanal con el
   ICR-SEPA (repo `precios_minoristas_supermercados`): era el pedido original del usuario.
5. Mejorar B y C (candidatas: morosidad de familias y préstamos personales reales del BCRA),
   reducir la dependencia del SIPA y revisar con los errores reales del registro la compensación
   de errores entre dimensiones y la corrección de sesgo de D.
6. Heredados del 06 (2026-10-06): cosmético de la lectura ("media móvil … la más baja desde 2025T4"
   cuando el "desde" es el trimestre anterior); extensiones no empezadas (transiciones con el panel
   rotativo —recomendada—, termómetro por región o grupos, calidad del empleo por rama/tamaño,
   página de resultados); deciles "escalonados" en 03 (empates de IPCF; fix: decil por ranking
   acumulado de `PONDIH`, sin confirmar); menores: T3-2021
   con 266 cols, contrastar la desocupación T1-2026 (7,8%) con el informe del INDEC, la skill global
   `indec-api` tiene un ID de IPC que no existe (`148.3_INIVELGENE_DICI_M_26`; el correcto es
   `148.3_INIVELNAL_DICI_M_26`).
7. Mejoras del 08 (evaluadas, **en espera: el usuario dijo "por ahora no"**): ver
   `docs/JUBILADOS.md` §9, en orden de prioridad.

## Adultos mayores y jubilados (notebook 08) — 2026-10-22

**Qué es:** foto de los adultos mayores (AM: varones 65+, mujeres 60+) con los últimos 4 trimestres
juntos + evolución trimestral 2017-2026, con IC 95% bootstrap por vivienda en todo. Generado por
`tools/gen_08_jubilados.py`; lógica en `src/jubilados.py`; prueba `tools/probar_08_local.py` (~3 min).
Secciones: cuántos son · con quién viven (tipología, rol, hijos en el hogar del AM vs AM en el hogar
de un hijo, hijos convivientes, quién sostiene a quién) · jubilación (cobertura, tipo, haber en
mínimas) · ingresos · pobreza · trabajo y pre-jubilables · vivienda · estrategias · salud/educación/
estado civil/tareas · regiones y aglomerados · evolución · lectura · controles · exportar.

**Decisiones (con evidencia):**
- Jubilado = monto `V2_M` (≤2023T3) o `V2_01_M + V2_02_M + V2_03_M` (≥2023T4) > 0, con `PONDII`
  (~11% de los AM no declara montos). **`CAT_INAC` no sirve:** cambió de códigos en 2023T4 (AM con
  `CAT_INAC==1` 76% → 52%; el resto pasó a "ama de casa") y **es la columna que falta en T126**.
- **Pobreza con los meses calendario** del trimestre (convención INDEC): réplica vs oficial error
  medio 0,11 pp, máx. 0,22 (18 semestres 2017S1-2025S2); por región 0,10-0,35 pp. Con el mes anterior
  (como el IPC del 06) erraba 2,1 pp. Canastas regionales de datos.gob.ar (445.1 / 446.1; llegan con
  atraso: si falta un mes se estima con la nacional × relación de los últimos 6 meses).
- **Haber en mínimas con los meses de referencia** (mes anterior): más masa en la mínima que con los
  meses calendario. "La mínima (con o sin bono)" = 0,95 × mín a 1,05 × (mín + bono). Debajo de la
  mínima: 31% de los de moratoria (descuento de cuotas) y 66% de otras pensiones (PUAM = 80%).
- "Trabaja" se mide con `PONDERA` (20,3%); con `PONDII` da menos (18,7%) porque los ocupados dejan
  de declarar sus ingresos más seguido. Jubilación × trabajo sí usa `PONDII`.
- Educación: adultos desde 25 años (los de 18-24 todavía estudian).

**Resultados (T2-2025 a T1-2026):** 4,44 M de AM (14,8% de la población, 66% mujeres); 33% de los
hogares tiene un AM. Solos 22,0%, solo con pareja 29,8%, viven con hijos 39,8% (33,3% hijos en su
hogar, 6,6% en el hogar de un hijo; 19% entre los de 85+). Cuando los hijos viven en el hogar del AM,
los AM aportan más de la mitad del ingreso en el 55% (28% si el AM vive en el hogar del hijo).
Cobertura 88,8% (mujeres 60-64: 69,5%); aportes 56,5%, moratoria 24,2%, otras 3,5%, más de uno 4,5%.
Cobran la mínima 38,9%, menos 17,1%. Pobreza AM 11,6% (indigencia 1,7%) vs 28,3% adultos, 43,1%
menores, 29,7% total; AM que no cobran 21,5%. 2017 7,2% → 2024 23,4% → 11,6%. Haber mediano real
−33% vs 2017, −14% vs 2023. Trabajan 20,3% (59% de los que no cobran), 55% informales.
Valores de referencia completos: `docs/JUBILADOS.md` §3.

**Validación:** Colab = corrida local (commit e2a23a3, 38 tablas, dif. relativa máx. 5e-16). Para
repetirla: `python tools/probar_08_local.py` y `python -X utf8 tools/comparar_zip_08.py <ZIP de Colab>`
(sale con código 1 si algo difiere; probado también con un ZIP alterado a propósito).

**Archivos:** `src/jubilados.py` (toda la lógica), `tools/gen_08_jubilados.py` (genera el notebook),
`tools/probar_08_local.py` (`--respaldos` regenera los dos CSV de abajo), `tools/comparar_zip_08.py`,
`data/canastas_regionales.csv`, `data/pobreza_oficial.csv`; además usa `data/series_nowcast.csv` (IPC y
haber mínimo si falla la API) y `data/bono_previsional.csv`. Salidas en `carga_EPH/resultados/jubilados/`
(local: `data/processed/resultados_06/jubilados/`).

**Cómo testear cambios:** `python tools/gen_08_jubilados.py && python tools/probar_08_local.py`
(sección 15 toda ✓; comparar las cifras con `docs/JUBILADOS.md` §3).

## Nowcast del termómetro (notebook 07) — `termómetro v1` vigente

**Qué es:** proyecta el termómetro del 06 para los trimestres que todavía no tienen EPH (sale ~85
días después del trimestre), lo corrige cuando sale (el trimestre pasa a oficial, los percentiles
y los coeficientes se recalculan) y guarda cada corrida en el registro de versiones, que completa
el error de cada versión cuando llega la EPH. Pedido del usuario (2026-10-20): el termómetro con
frecuencia mensual o semanal, proyectado con la mayor precisión posible y corregido con la EPH.

- **D (ingresos reales): microsimulación** sobre los microdatos de la última EPH: `P21`/`TOT_P12` de
  cada ocupado con el índice de salarios de su grupo (registrado privado o público; no registrado
  para no registrados, cuentapropistas y patrones), jubilaciones con el haber mínimo (o mínimo +
  bono si cobra ≤ 1,05 × eso), AUH con su monto y el resto con el IPC; estacionalidad con los
  factores del 06.
- **A, B y C: ecuaciones puente:** cada indicador desestacionalizado cambia Δy = Σ β·Δx con el EMAE,
  los asalariados registrados del SIPA (privados + públicos + casas particulares) y la confianza
  del consumidor UTDT en bienes durables; sin constante ni término AR; los mismos tres para los 13
  indicadores; β por MCO con la historia hasta la base (sin 2020T1-2021T2).
- Los 15 indicadores pasan por la **misma normalización del 06** (control de la sección 3:
  idéntico). Cada trimestre se proyecta por separado. Bandas: ±1,96 × RMSE del backtest para el
  horizonte más parecido.

**Resultados (backtest en pseudo tiempo real 2019-2026, sin pandemia, RMSE del termómetro):**

| Horizonte | Proyección | Repetir el último | A, B y C con persistencia |
|---|---|---|---|
| EPH del trimestre anterior (k=1, 80 días después del cierre) | 4,1 | 7,2 | 5,5 |
| EPH demorada 1 trimestre (k=2, al cierre) | 7,0 | 12,1 | 9,6 |
| EPH demorada 2 trimestres (k=3, 75 días antes del cierre) | 8,8 | 15,2 | 13,9 |

D: 9,5 vs 14,8 (ingreso laboral real 3,5% vs 6,4%; ingreso bajo 1,8 vs 3,3 pp). Por dimensión
(k=1): A 11,4 vs 12,0 (persistencia), B 14,2 vs 14,1, C 7,4 vs 8,7: **B y C casi no se anticipan**.
**Robustez** (sección 7): sin sesgo significativo; la ventaja se sostiene en 2019-2022 (5,4 vs 6,8)
y 2023-2026 (2,5 vs 7,6); le gana a repetir el último en 60-64% de los trimestres; los IC cubren
92 / 96 / 84% (k=1/2/3); las versiones convergen (7,1 → 6,7 → 4,4 → 4,2 → 4,1); **depende del SIPA**
(sin él el error sube hasta 48%; sin EMAE no cambia). **El 4,1 es optimista:** a k=1 buena parte de
la mejora viene de errores de B que compensan los de A y C (lo esperable: 4,1-5,5). El nowcast de
hoy varía 60,8-64,3 (T2) entre variantes razonables y siempre queda arriba de 2025.

**Decisiones (evidencia en el anexo del 07 y `docs/TECNICO.md` §7):** índice no registrado corrido
6 meses (corr. 0,874 → 0,988); base = último trimestre (el mismo del año anterior erra el doble);
sin corrección de sesgo de D (no baja el RMSE); predictores neutrales (elegirlos por indicador es
optimista); sin término AR (empeora); meses sin dato con tendencia (constantes empeora; el no
registrado sigue al registrado privado mientras éste tiene dato).

**Reglas que muerden:**
- La API de datos.gob.ar devuelve tablas vacías de forma intermitente (a veces todo el día para una
  serie): `_bajar_serie` reintenta, baja el CSV de la distribución (URL de `metadata=full`) y
  recién después usa `data/series_nowcast.csv`. RIPTE (`158.1_REPTE_0_0_5`) vino vacío: no se usa.
- En el 06 solo los ingresos se desestacionalizan: A, B y C tienen estacionalidad (el T2 sale peor
  que el T1 en B y C) → leer la proyección contra el mismo trimestre del año anterior.
- Agregar a la historia otros trimestres proyectados mueve el percentil de uno ~1 punto: comparar
  siempre trimestres proyectados por separado.
- El bono previsional no tiene serie pública: carga manual mensual en `data/bono_previsional.csv`.
- El registro de versiones vive en Drive y no se puede regenerar: no borrarlo.

**Archivos:** `src/nowcast.py` (toda la lógica), `tools/gen_07_nowcast.py` (genera el notebook),
`tools/probar_07_local.py`, `data/series_nowcast.csv`, `data/bono_previsional.csv`; salidas en
`carga_EPH/resultados/nowcast/` (local: `data/processed/resultados_06/nowcast/`).

**Cómo testear cambios:** `python tools/gen_07_nowcast.py && python tools/probar_06_local.py &&
python tools/probar_07_local.py` (sección 3 ✓ y lectura de la sección 7).

## Termómetro de la economía de los hogares (notebook 06) — v4 vigente

**Qué es:** índice de malestar 0-100 (0 = mejor trimestre de la serie, 100 = peor). Franjas:
≤33 Templado, ≤66 Tibio, >66 Fiebre. Cuatro dimensiones con peso 1/4; cada indicador se
normaliza como **percentil histórico orientado**, redondeando a 1 decimal antes de rankear.
Intervalos de confianza del 95% por bootstrap (200 réplicas, Poisson por vivienda `CODUSU`,
mismo multiplicador en todos los trimestres).

| Dimensión | Indicadores (en el índice) |
|---|---|
| A. Cantidad de empleo | desocupación; tasa de empleo (invertida); desocupación >1 año (`PP10A==5`, % PEA); desocupados por despido o renuncia forzada (`PP11O∈{1,7}`, % PEA) |
| B. Calidad del empleo | subocupación (`INTENSI==1`); ocupados que buscan otro empleo (`PP03J==1`, % PEA); **sin cobertura de salud** (`CH08==4`, % población); tasa de empleo asalariado registrado (`CAT_OCUP==3 & PP07H==1`, % población, invertida) |
| C. Estrés de los hogares (jefe `CH03==1`, % hogares) | `V13` gastaron ahorros; `V14` préstamos familiares; `V17` vendieron pertenencias; `V6` alimentos de gobierno/instituciones; `V7` alimentos de familiares |
| D. Ingresos reales | ingreso laboral real (media geométrica de `P21`/IPC, ocupados con `P21>0`, `PONDIIO`, invertido); personas con ingreso per cápita real bajo (`IPCF`/IPC < $3.123 de dic-2016 = 60% de la mediana 2017-2019, `PONDIH`). Ambos desestacionalizados (aguinaldo en T1 y T3) |

Deflactor: IPC nacional `148.3_INIVELNAL_DICI_M_26` (dic-2016 = 100), promedio de los meses de
referencia = mes anterior a la entrevista (T1 → dic, ene, feb).

Complementarios (fuera del índice): asalariados sin descuento jubilatorio (salió en v4),
ingreso per cápita familiar real (redundante, corr. 0,98 con ingreso bajo), informalidad
`EMPLEO==2` (solo ≥2023T4), `V15` y `V16` (señal ambigua), desalentados y niños <10 (ruido),
pluriempleo (procíclico).

**Resultados v4 (validados en Colab = corrida local, 2026-10-06; re-corrida idéntica el 2026-10-21):**
máx 2020T4 89,7; mín 2017T4 13,4; valle 2023T3-T4 31,0 / 32,3 (percentil 18); 2020T2 70,1; 2024T1
56,6; 2024T2 64,4. **2026T1 = 52,8 (Tibio; IC 95% 44,4-60,6), +5,4 i.a. (IC −4,4 a +15,1: no
significativa, sube en el 83% de las réplicas); media móvil 4T 49,8, −6,3 i.a. (IC −11,3 a −0,6:
significativa).** Dimensiones 2026T1: A 34,7 · B 65,6 · C 78,9 · D 31,9. Lectura: ingresos reales
recuperados respecto de 2024, empleo más precario (sin cobertura 34,1%, p97; asalariados
registrados p86) y hogares usando reservas (préstamos familiares p90, ahorros p89, vendieron
pertenencias p81). Promedio anual v4: 2017 24,1 · 2018 35,0 · 2019 58,2 · 2020 76,6 · 2021 66,4 ·
2022 47,2 · 2023 35,0 · 2024 58,3 · 2025 48,4 · 2026 (solo T1) 52,8. Estados: 24 Tibio, 8 Templado,
5 Fiebre. Ruido: error estándar medio del nivel 3,6 pts y de la i.a. 4,9 pts (variación mínima
detectable ~10 pts). Validación: corr. con la pobreza oficial 0,60 (v3: 0,29); corr. i.a. con
EMAE i.a. −0,53 (v3: −0,32); señal/ruido 22 (v3: 18).

**Historia de versiones (por qué está armado así):**
- **v1**: falló el chequeo de sentido (2020T2 = 48) por **efecto composición** (en la
  cuarentena se perdieron sobre todo empleos informales y de pocas horas: los indicadores
  sobre ocupados "mejoraron"). Desalentados y niños <10 (≈0,1%) metían ruido.
- **v2**: desalentados y niños a complementarios; B suma asalariados registrados sobre población.
- **v3**: Anexo A "Diagnóstico de candidatas" (6 criterios: cobertura desde 2017, códigos
  estables entre esquemas, pandemia > valle 2023, autocorrelación ≥0,3, Spearman con
  termómetro ≥0,3, |corr| <0,85 con indicadores del índice). `PP11O∈{1,7}` entra a A;
  pluriempleo descartado (procíclico).
- **v4** (2026-10-06): IC bootstrap; `CH08==4` reemplaza a asalariados sin descuento (que fallaba
  los criterios 3 y 5 por efecto composición: 35,8% → 23,8% en 2020T2); dimensión D de
  ingresos reales. Chequeo de sentido nuevo: valle 2023 en el tercio inferior (antes ≤ 33, ya no
  aplica porque los ingresos de 2023 eran bajos) y D > 66 en 2024T1-T2.
- Descartado en la evaluación v4 (detalle en el Anexo A del 06 y `docs/TECNICO.md` §6): horas
  trabajadas por persona, desocupación de jefes, hogares con activos sin ocupados, despidos +
  cierres de cuentapropistas (`PP11L∈{1,2,4}`), hogares con 2+ estrategias, jóvenes que no
  estudian ni trabajan, quieren más horas (`PP03G`) → redundantes (corr. 0,88-0,95); ocupados
  ausentes (`INTENSI==4`, estacional), temporarios, `V15`, `V16`, `V3`/`V4` → ruido o signo
  contrario; z-scores, min-max, desestacionalizar todo, pesos PCA/por indicador, C por personas
  → cambios de segundo orden.

**Cómo testear cambios:** `python tools/gen_06_termometro.py && python tools/probar_06_local.py`
(con `--descargar` la primera vez en una PC nueva). Corre con datos reales; los números
coinciden con Colab.

## Flujo para agregar un trimestre (no requiere tocar código)

1. Descargar del INDEC `EPH_usu_<Q>_Trim_<YYYY>_txt.zip` (Bases de datos → EPH microdatos;
   URL directa `https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_usu_<Q>_Trim_<AAAA>_txt.zip`;
   si no existe, el sitio responde una página HTML; T1-2017 se llama `EPH_usu_1er_Trim_2017_txt.zip`).
2. Subirlo **sin descomprimir** a Google Drive → Mi unidad → `carga_EPH`.
3. Correr `00_preparacion_bases.ipynb` en Colab (Runtime → Run all). Debe mostrar el
   trimestre nuevo como "compilado" y los demás "ya existía (salteado)".
4. Re-correr 01-06 (toman el último trimestre automáticamente; revisar la sección 13 del 06),
   **después el 07**, que concilia el registro de versiones (error de las proyecciones de ese
   trimestre; ver `docs/NOWCAST.md` §5), y el **08** (su foto pasa sola a los últimos 4 trimestres;
   revisar su sección 15; ver `docs/JUBILADOS.md` §4).
5. Si el zip trae nombres internos raros (como T4-2020), ampliar `_parse_period_from_name`
   / `_base_type_from_name` en `src/data_loader.py`.
6. Actualizar los valores de referencia de abajo y el HANDOFF.

**Importante:** 01-06 y 08 obtienen los trimestres con `list_available_quarters()`, que escanea los
**zips de Drive**, no los parquets. Si se sube un zip y no se corre el 00, el notebook
pedirá un parquet inexistente → siempre correr el 00 primero. El 07 toma los trimestres del CSV
del 06 (y avisa con ⚠ si hay microdatos que el 06 todavía no procesó).

## Valores de referencia (para detectar regresiones)

| Indicador | T4-2025 | T1-2026 |
|---|---|---|
| Actividad / empleo / desocupación (%) | 48,6 / 45,0 / 7,5 | 48,6 / 44,8 / 7,8 |
| Subocupación (% PEA) | 11,3 | 11,1 |
| Informalidad (% ocupados, desde 2023T4) | 43,0 | 44,2 (máx. serie) |
| Termómetro v4 (0-100) / media móvil 4T | 49,4 / 48,4 | 52,8 / 49,8 |
| Termómetro v4: IC 95% del nivel | 41,8-56,7 | 44,4-60,6 |
| Sin cobertura de salud (% población) | 33,8 | 34,1 |
| Ingreso laboral real ($ dic-2016, media geom.) / ingreso bajo (% personas) | 7.823 / 28,2 | 7.486 / 27,1 |
| (v3, referencia histórica) Termómetro / media móvil 4T | 57,1 / 54,3 | 60,0 / 57,0 |
| Desocupados por despido o renuncia forzada (% PEA) | 1,1 | 1,1 |
| Gini IPCF / D10/D1 / top10 % | 0,427 / 17,7 / 32,5 | 0,442 / 19,1 / 34,0 |
| Sin cloaca / sin agua cañería / hacinamiento crítico (% hogares) | 27,3 / 1,9 / 1,8 | 27,0 / 1,9 / 1,8 |
| Secundario completo+ (25+) / analfabetismo (%) | 63,7 / 0,86 | 64,3 / 0,71 |
| Edad promedio / índice masculinidad | 35,7 / 95,0 | 35,7 / 95,0 |

Otros hitos de la serie: desocupación pico 2020T2 (13,1%) y mínimo 2023T3-T4 (5,7%);
subocupación pico 2020T4 (15,1%); Gini pico 2024T1 (0,467); edad promedio cae en
2020T2 (efecto pandemia en el operativo). Tamaño medio del hogar T126: 2,95.
Total panel previo a T126: 1.825.881 filas (36 trimestres).

**Nowcast (07) con base 2026T1, series al 2026-10-21** (cambian si se actualizan las series):
umbral de ingreso bajo $3.123 de dic-2016; backtest del termómetro RMSE 4,1 / 7,0 / 8,8 (k=1/2/3;
repetir el último 7,2 / 12,1 / 15,2); backtest de D 9,5 pts (k=1, 80 días); nowcast 2026T2 / T3 /
T4 = 62,8 / 58,6 / 54,1 (D 35,1 / 31,6 / 24,4).

**Adultos mayores (08), foto T2-2025 a T1-2026:** 4,44 M (14,8% de la población); cobertura 88,8%;
pobreza AM 11,6% (total 29,7%); viven con hijos 39,8%; cobran la mínima 38,9%; réplica de la pobreza
oficial error medio 0,11 pp. Tabla completa en `docs/JUBILADOS.md` §3.

## Qué es / arquitectura (resumen)

- Repo público `santiagoriverti/analisis_EPH`. Notebooks pensados para **Google Colab**.
- Datos: `.zip` de microdatos INDEC en Drive `carga_EPH` → el **00** los compila a un
  parquet por trimestre en `carga_EPH/processed/eph_T<Q><YY>.parquet` (persistente en
  Drive, **no versionado** en GitHub: "Opción A").
- 01-08 copian esos parquets a `/content/processed_local` (evita desconexión FUSE) y leen
  con `load_panel(columns=[...], quarters=[...], out_dir=PROCESSED_DIR)`.
- Sin dependencia de `pyeph`. Toda la lógica de carga en `src/data_loader.py`; la del nowcast,
  en `src/nowcast.py` (series de la API de datos.gob.ar, con respaldo en `data/`); la del 08, en
  `src/jubilados.py` (reusa de `src/nowcast.py` la descarga de series, los meses de referencia y el bono).
- Notebooks generados por script (no editar el `.ipynb`): 06 (`tools/gen_06_termometro.py`), 07
  (`tools/gen_07_nowcast.py`) y 08 (`tools/gen_08_jubilados.py`).
- Salidas en Drive: `carga_EPH/resultados/` (06), `carga_EPH/resultados/nowcast/` (07) y
  `carga_EPH/resultados/jubilados/` (08).
- Detalle de funciones, gotchas y decisiones: [`docs/TECNICO.md`](../docs/TECNICO.md).

## Notebooks

| NB | Contenido | Base / ponderador |
|---|---|---|
| 00 | Compila zips → parquets por trimestre; verifica merge/montos y quiebre 4T2023 | — |
| 01 | Pirámide edad×sexo, parentesco y tamaño de hogar, región, edad promedio e índice de masculinidad | Personas / `PONDERA` |
| 02 | Actividad/empleo/desocupación, subocupación (`INTENSI`), `CAT_OCUP`, informalidad (`EMPLEO==2`, solo ≥2023T4) | Personas / `PONDERA` |
| 03 | IPCF: percentiles, participación por decil, D10/D1, Gini (Lorenz), top10/bottom40. Sin línea de pobreza (decisión del usuario) | Personas / `PONDIH` |
| 04 | Tipo de vivienda (`IV1`), tenencia (`II7`), agua (`IV6`), desagüe (`IV11`), hacinamiento (`IX_TOT`/`II1`, crítico >3) | Hogar (jefe `CH03==1`) / `PONDERA` |
| 05 | `NIVEL_ED` 25+, asistencia (`CH10`), público/privado (`CH11`), analfabetismo (`CH09`) | Personas / `PONDERA` |
| 06 | Termómetro de la economía de los hogares 0-100, v4 con IC (ver sección Termómetro). Generado por `tools/gen_06_termometro.py`; prueba local `tools/probar_06_local.py`. Validado en Colab | Personas + Hogar / `PONDERA`, `PONDIIO`, `PONDIH` + IPC |
| 07 | **Nowcast del termómetro** (ver sección Nowcast): D por microsimulación, A, B y C por ecuaciones puente, backtest, robustez (sección 7), registro de versiones, gráficos `nowcast_01` … `nowcast_05`. Generado por `tools/gen_07_nowcast.py` (lógica en `src/nowcast.py`); prueba local `tools/probar_07_local.py`. Validado en Colab salvo la sección 7 y `nowcast_05_evolucion` | Personas / `PONDIIO`, `PONDIH` + CSV del 06 + series de datos.gob.ar |
| 08 | **Adultos mayores y jubilados** (ver sección 08): convivencia, jubilación, ingresos, pobreza (réplica INDEC), trabajo, vivienda, estrategias, salud; región y aglomerado; evolución; IC bootstrap; Excel/CSV/PNG/ZIP en `resultados/jubilados/`. Generado por `tools/gen_08_jubilados.py` (lógica en `src/jubilados.py`); prueba local `tools/probar_08_local.py`. Validado en Colab (2026-10-22) | Personas / `PONDERA`, `PONDII`, `PONDIIO`, `PONDIH` + IPC, haber mínimo, canastas y pobreza oficial |

Definiciones INDEC usadas en 02: PEA = `ESTADO∈{1,2}`; actividad = PEA/total;
empleo = ocupados/total; desocupación = desocupados/PEA; subocupación = `INTENSI==1`/PEA.

## Reglas del usuario

- Commits **solo** con el usuario Santiago Riverti; **nunca** `Co-Authored-By: Claude` ni
  atribución a Claude en commits/PRs.
- Repos locales en `C:\Users\sriverti\Desktop\INECO\Repositorios\` (en otra PC, clonar
  donde corresponda).
- Idioma de trabajo: español. Actualizar este archivo al cerrar cada sesión.
- Bases pesadas del INDEC no se commitean (`data/raw/*.zip` en `.gitignore`).
- Validación en Colab: el usuario corre los notebooks, pega las salidas en el chat y baja los CSV
  de Drive (del 08, el ZIP que descarga el notebook); se comparan contra la corrida local (deben
  coincidir salvo redondeo ~1e-10; para el 08, `tools/comparar_zip_08.py`).

## Historial resumido

- **2026-06-12**: creación del repo, `data_loader` sin `pyeph`, notebook 00 (refactor
  memory-safe, fix coma decimal, naming irregular de zips, Opción A en Drive), diccionario
  `memoria_EPH.md`, notebooks 01-05 creados y validados en Colab (36 trimestres).
  Fixes: copia Drive→local (FUSE), `pd.to_numeric` en `IPCF`/`PONDIH` (03).
- **2026-06-16**: `CLAUDE.md` apuntando a la memoria.
- **2026-09-29**: incorporado T1-2026; documentación reorganizada (`docs/TECNICO.md`, README con
  setup para nueva PC). Creado `06_termometro.ipynb`; v1 falló chequeo 2020 (efecto composición) →
  v2 corregida → v3 suma despidos (`PP11O∈{1,7}`), pluriempleo descartado; v3 validada. Generador
  versionado en `tools/`. 06 reorganizado: lectura automática, promedios anuales, controles de
  calidad, exportación anual/resumen, candidatas a Anexo A; validado en Colab.
- **2026-10-06**: datos reales en la PC (zips del INDEC + `tools/probar_06_local.py`; réplica
  exacta del v3). Evaluación del termómetro (bootstrap de 300 réplicas, 15 candidatas, 10
  variantes, validación contra pobreza, EMAE y confianza del consumidor) → **v4**: IC bootstrap,
  sin cobertura de salud en B, dimensión D de ingresos reales (IPC nacional,
  `data/ipc_nacional.csv`); gráficos a Drive. Validado en Colab (idéntico a la corrida local).
- **2026-10-20**: diseño del nowcast (vara: repetir el último dato erra 8,4 pts de termómetro; el
  ruido muestral es 3,6; proyectar indicadores y no el índice; serie mensual = trimestre móvil;
  semanal solo como frecuencia de actualización) y prototipo `07_nowcast` de la dimensión D
  (microsimulación; backtest D 9,5 vs 14,8). Validado en Colab el 2026-10-21.
- **2026-10-21**: A, B y C por ecuaciones puente (EMAE, SIPA, confianza del consumidor): el 07
  proyecta el termómetro completo (backtest k=1 4,1 vs 7,2 de repetir el último); validado en
  Colab. Después: sección 7 de robustez (subperíodos, calibración, versiones, dependencia de cada
  predictor), gráfico `nowcast_05_evolucion`, guía `docs/NOWCAST.md` y documentación consolidada
  para continuar en otra PC (falta correr en Colab la sección 7 y el gráfico).
- **2026-10-22**: notebook 08 de adultos mayores y jubilados (preguntas de diseño al usuario;
  `src/jubilados.py`, generador y prueba local; respaldos `data/canastas_regionales.csv` y
  `data/pobreza_oficial.csv`; `openpyxl` en requirements). Identificada la columna faltante de T126
  (`CAT_INAC`). Validado en Colab el mismo día (idéntico a la corrida local). Devolución del 08 con
  mejoras evaluadas (en espera). Documentación consolidada para otra PC: `docs/JUBILADOS.md`,
  `tools/comparar_zip_08.py`, README (el 08 había quedado fuera de la tabla de notebooks), TECNICO,
  CLAUDE.md, NOWCAST y diccionario §10.
