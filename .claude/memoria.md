# Memoria del proyecto: analisis_EPH

> Documento de continuidad entre sesiones de Claude Code (y entre PCs). Leer primero el
> bloque **HANDOFF**. Detalle técnico en [`docs/TECNICO.md`](../docs/TECNICO.md);
> diccionario de variables en [`memoria_EPH.md`](memoria_EPH.md).

## ⭐ HANDOFF (última sesión: 2026-10-06)

**Estado: termómetro v4 validado en Colab (2026-10-06): el CSV exportado en Colab es idéntico
al de la corrida local (diferencia máxima 0,0 en las 56 columnas, bootstrap incluido por la
semilla fija), IPC por API, controles de la sección 13 todos ✓.** Datos al día con T1-2026 (37 trimestres, T1-2017 → T1-2026). T2-2026 todavía no
estaba publicado el 2026-10-06 (la URL del INDEC devuelve una página HTML).

Qué se hizo en la sesión 2026-10-06:
1. **Datos reales en la PC.** Los 37 zips se bajaron del sitio del INDEC a `data/raw/`
   (ignorado; URL `https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/EPH_usu_<Q>_Trim_<AAAA>_txt.zip`,
   T1-2017 se llama `EPH_usu_1er_Trim_2017_txt.zip`). Nuevo `tools/probar_06_local.py
   [--descargar]`: baja lo que falte, compila a `data/processed/` (ignorado) y corre el 06
   completo en ~30 s. Réplica exacta del v3 verificada (82,1 / 20,4 / 60,0). **Ya no hace falta
   el remuestreo sintético para testear.**
2. **Evaluación del termómetro** (bootstrap de 300 réplicas por vivienda, 15 candidatas, 10
   variantes de metodología, validación contra pobreza oficial, EMAE i.a. y confianza del
   consumidor UTDT). Conclusiones: el índice es robusto (variantes de metodología con corr.
   0,93-0,98; ninguna candidata nueva lo movía > 5 pts); el ruido muestral era grande (i.a.
   de +11 en 2026T1 con IC −0,2 a +22,6; variación mínima detectable ~10 pts); "asalariados
   sin descuento" fallaba 2 criterios del Anexo A (cae en la pandemia, Spearman −0,23); punto
   ciego = ingresos (corr. con la pobreza 0,29).
3. **v4 (pedido del usuario: cambios 1, 2 y 4 de la evaluación):** (1) intervalos de confianza
   bootstrap en el notebook (nivel, i.a., media móvil; lectura dice si la variación es
   significativa; banda en el gráfico; columnas en el CSV); (2) `CH08==4` sin cobertura de
   salud reemplaza a asalariados sin descuento en B (sale a complementario); (3) nueva
   dimensión **D. Ingresos reales** (ingreso laboral real + personas con ingreso per cápita
   real bajo), IPC nacional por API con respaldo `data/ipc_nacional.csv`. El usuario antes
   había descartado ingresos; lo reconsideró con la evidencia. Sección 3 reescrita: un
   diccionario `INDICADORES` define cada indicador una vez (numerador/denominador) y sirve
   para el valor puntual y las réplicas. Los 19 indicadores comunes dan idéntico al v3.
4. Tras la validación: fix de la tabla de la sección 11 (los complementarios en pesos, como el
   ingreso per cápita familiar real, se marcaban "↑ peor"; ahora "↓ peor"). Sin efecto en el índice.
5. **Gráficos a Drive** (pedido del usuario): `guardar_figura` guarda cada gráfico como PNG
   (150 dpi) en `carga_EPH/resultados/graficos/` (`01_termometro_hoy` … `05_promedios_anuales`,
   `anexoA_candidatas` si hay candidatas); se sobrescriben en cada corrida, como los CSV.

**Pendientes / ideas:**
1. Cosmético (heredado de v3): la lectura dice "media móvil 49,8 (la más baja desde 2025T4)"
   cuando el "desde" es el trimestre anterior; podría omitirse en ese caso.
2. **T2-2026** cuando lo publique el INDEC: subir zip a `carga_EPH`, correr 00 y 01-06 (o
   probar antes en la PC con `tools/probar_06_local.py --descargar`). El IPC ya cubre mar-may 2026.
3. Extensiones propuestas antes (ninguna empezada): transiciones con el panel rotativo
   (recomendada; el bootstrap por `CODUSU` ya respeta el panel), termómetro por región o
   grupos, calidad del empleo por rama/tamaño, página/artifact de resultados.
4. Deciles "escalonados" en 03 (empates de IPCF en valores redondos; fix: decil por ranking
   acumulado de `PONDIH`). Sin confirmar por el usuario.
5. Menores: columna faltante en T126 (234 vs 235), T3-2021 con 266 cols, contrastar
   desocupación T1-2026 (7,8%) con el informe INDEC. La skill global `indec-api` tiene un ID de
   IPC que ya no existe (`148.3_INIVELGENE_DICI_M_26`; el correcto es `148.3_INIVELNAL_DICI_M_26`).

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

**Resultados v4 (validados en Colab = corrida local, 2026-10-06):** máx 2020T4 89,7; mín
2017T4 13,4; valle 2023T3-T4 31,0 / 32,3 (percentil 18); 2020T2 70,1; 2024T1 56,6; 2024T2 64,4.
**2026T1 = 52,8 (Tibio; IC 95% 44,4-60,6), +5,4 i.a. (IC −4,4 a +15,1: no significativa, sube
en el 83% de las réplicas); media móvil 4T 49,8, −6,3 i.a. (IC −11,3 a −0,6: significativa).**
Dimensiones 2026T1: A 34,7 · B 65,6 · C 78,9 · D 31,9. Lectura: ingresos reales recuperados
respecto de 2024, empleo más precario (sin cobertura 34,1%, p97; asalariados registrados p86)
y hogares usando reservas (préstamos familiares p90, ahorros p89, vendieron pertenencias p81).
Promedio anual v4: 2017 24,1 · 2018 35,0 · 2019 58,2 · 2020 76,6 · 2021 66,4 · 2022 47,2 ·
2023 35,0 · 2024 58,3 · 2025 48,4 · 2026 (solo T1) 52,8. Estados: 24 Tibio, 8 Templado, 5 Fiebre.
Ruido: error estándar medio del nivel 3,6 pts y de la i.a. 4,9 pts (variación mínima
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

1. Descargar del INDEC `EPH_usu_<Q>_Trim_<YYYY>_txt.zip` (Bases de datos → EPH microdatos).
2. Subirlo **sin descomprimir** a Google Drive → Mi unidad → `carga_EPH`.
3. Correr `00_preparacion_bases.ipynb` en Colab (Runtime → Run all). Debe mostrar el
   trimestre nuevo como "compilado" y los demás "ya existía (salteado)".
4. Re-correr 01-06: toman el último trimestre automáticamente.
5. Si el zip trae nombres internos raros (como T4-2020), ampliar `_parse_period_from_name`
   / `_base_type_from_name` en `src/data_loader.py`.

**Importante:** 01-06 obtienen `ULTIMO` con `list_available_quarters()`, que escanea los
**zips de Drive**, no los parquets. Si se sube un zip y no se corre el 00, el notebook
pedirá un parquet inexistente → siempre correr el 00 primero.

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

## Qué es / arquitectura (resumen)

- Repo público `santiagoriverti/analisis_EPH`. Notebooks pensados para **Google Colab**.
- Datos: `.zip` de microdatos INDEC en Drive `carga_EPH` → el **00** los compila a un
  parquet por trimestre en `carga_EPH/processed/eph_T<Q><YY>.parquet` (persistente en
  Drive, **no versionado** en GitHub: "Opción A").
- 01-06 copian esos parquets a `/content/processed_local` (evita desconexión FUSE) y leen
  con `load_panel(columns=[...], quarters=[...], out_dir=PROCESSED_DIR)`.
- Sin dependencia de `pyeph`. Toda la lógica de carga en `src/data_loader.py`.
- Detalle de funciones, gotchas y decisiones: [`docs/TECNICO.md`](../docs/TECNICO.md).

## Notebooks (todos validados en Colab)

| NB | Contenido | Base / ponderador |
|---|---|---|
| 00 | Compila zips → parquets por trimestre; verifica merge/montos y quiebre 4T2023 | — |
| 01 | Pirámide edad×sexo, parentesco y tamaño de hogar, región, edad promedio e índice de masculinidad | Personas / `PONDERA` |
| 02 | Actividad/empleo/desocupación, subocupación (`INTENSI`), `CAT_OCUP`, informalidad (`EMPLEO==2`, solo ≥2023T4) | Personas / `PONDERA` |
| 03 | IPCF: percentiles, participación por decil, D10/D1, Gini (Lorenz), top10/bottom40. Sin línea de pobreza (decisión del usuario) | Personas / `PONDIH` |
| 04 | Tipo de vivienda (`IV1`), tenencia (`II7`), agua (`IV6`), desagüe (`IV11`), hacinamiento (`IX_TOT`/`II1`, crítico >3) | Hogar (jefe `CH03==1`) / `PONDERA` |
| 05 | `NIVEL_ED` 25+, asistencia (`CH10`), público/privado (`CH11`), analfabetismo (`CH09`) | Personas / `PONDERA` |
| 06 | Termómetro de la economía de los hogares 0-100, v4 con IC (ver sección Termómetro). Generado por `tools/gen_06_termometro.py`; prueba local `tools/probar_06_local.py` | Personas + Hogar / `PONDERA`, `PONDIIO`, `PONDIH` + IPC |

Definiciones INDEC usadas en 02: PEA = `ESTADO∈{1,2}`; actividad = PEA/total;
empleo = ocupados/total; desocupación = desocupados/PEA; subocupación = `INTENSI==1`/PEA.

## Reglas del usuario

- Commits **solo** con el usuario Santiago Riverti; **nunca** `Co-Authored-By: Claude` ni
  atribución a Claude en commits/PRs.
- Repos locales en `C:\Users\sriverti\Desktop\INECO\Repositorios\` (en otra PC, clonar
  donde corresponda).
- Idioma de trabajo: español. Actualizar este archivo al cerrar cada sesión.
- Bases pesadas del INDEC no se commitean (`data/raw/*.zip` en `.gitignore`).

## Historial resumido

- **2026-06-12**: creación del repo, `data_loader` sin `pyeph`, notebook 00 (refactor
  memory-safe, fix coma decimal, naming irregular de zips, Opción A en Drive), diccionario
  `memoria_EPH.md`, notebooks 01-05 creados y validados en Colab (36 trimestres).
  Fixes: copia Drive→local (FUSE), `pd.to_numeric` en `IPCF`/`PONDIH` (03).
- **2026-06-16**: `CLAUDE.md` apuntando a la memoria.
- **2026-09-29**: incorporado T1-2026 (ver HANDOFF); documentación reorganizada
  (`docs/TECNICO.md`, README con setup para nueva PC). Creado `06_termometro.ipynb`;
  v1 falló chequeo 2020 (efecto composición) → v2 corregida → v3 suma despidos
  (`PP11O∈{1,7}`), pluriempleo descartado; v3 validada. Generador versionado en `tools/`.
  Re-corrida verificada (idéntica). 06 reorganizado: lectura automática, promedios
  anuales, controles de calidad, exportación anual/resumen, candidatas a Anexo A; validado en Colab.
- **2026-10-06**: datos reales en la PC (zips del INDEC + `tools/probar_06_local.py`).
  Evaluación del termómetro (bootstrap, 15 candidatas, 10 variantes, validación externa) →
  **v4**: IC bootstrap, sin cobertura de salud en B, dimensión D de ingresos reales (IPC
  nacional, `data/ipc_nacional.csv`). Validado en Colab (idéntico a la corrida local).
