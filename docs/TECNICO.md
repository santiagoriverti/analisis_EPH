# Documentación técnica — analisis_EPH

Referencia técnica del pipeline de datos y de los notebooks. Estado del proyecto y
próximos pasos: [`.claude/memoria.md`](../.claude/memoria.md). Diccionario de variables:
[`.claude/memoria_EPH.md`](../.claude/memoria_EPH.md). Rutina del nowcast (cuándo correrlo, qué
mantener, qué revisar): [`NOWCAST.md`](NOWCAST.md).

## 1. Flujo de datos

```
INDEC (descarga manual)                Google Drive (Mi unidad)
EPH_usu_<Q>_Trim_<YYYY>_txt.zip  ──►   carga_EPH/*.zip
                                              │
                        00_preparacion_bases  │  build_panel(overwrite=False)
                                              ▼
                                       carga_EPH/processed/eph_T<Q><YY>.parquet
                                              │  (1 parquet por trimestre)
                   01-07: copia a /content/processed_local (shutil.copy)
                                              ▼
                              load_panel(columns=[...], quarters=[...])
                                              │
              06_termometro ──► carga_EPH/resultados/termometro_EPH.csv (+ anual, resumen, graficos/)
                                              │  (A, B y C del termómetro)
              07_nowcast  ──► carga_EPH/resultados/nowcast/ (registro_versiones.csv, nowcast, backtest,
                              robustez, graficos/)  + series de datos.gob.ar
```

- Rutas en Colab: `DRIVE_DIR = /content/drive/MyDrive/carga_EPH`,
  `DRIVE_PROCESSED = /content/drive/MyDrive/carga_EPH/processed`,
  `PROCESSED_DIR` (01-07) = `/content/processed_local`; `RESULTADOS_DIR` (06-07) =
  `/content/drive/MyDrive/carga_EPH/resultados`.
- Cada notebook clona (o hace `git pull` de) este repo en `/content/analisis_EPH` para
  importar `src/data_loader.py`. **Los cambios de código solo llegan a Colab después
  de pushearlos a `main`.**
- Alternativa local: poner `.zip`/`.txt` en `data/raw/` y usar `out_dir` por defecto
  (`data/processed/`). `tools/probar_06_local.py --descargar` baja los zips del sitio del
  INDEC, compila y corre el notebook 06 completo (ver §6, "Probar en la PC");
  `tools/probar_07_local.py` corre el 07 (§7).

## 2. `src/data_loader.py`

| Función | Qué hace |
|---|---|
| `_parse_period_from_name(name)` | Extrae `(year, period)` de patrón `T<Q><YY>` (`usu_individual_T126.txt`) o `<Q>to_trim<YYYY>` (caso T4-2020). |
| `_base_type_from_name(name)` | `"hogar"` / `"individual"` (acepta `"personas"`). |
| `_read_csv(f)` | `sep=";"`, `encoding="latin1"`, `decimal=","`, `low_memory=False`. |
| `_find_sources(search_dirs)` | Indexa zips (lee `namelist()`, sin descomprimir) y `.txt` sueltos por `(year, period) → {base: ref}`. Default `[DRIVE_DIR, RAW_DIR]`. |
| `list_available_quarters()` | Trimestres con **ambas** bases disponibles (según los **zips**, no los parquets). |
| `load_eph(year, period, base_type)` | Lee una base de un trimestre directo del zip. |
| `merge_individual_hogar(ind, hog)` | Merge `m:1` por `CODUSU`+`NRO_HOGAR`; columnas repetidas del hogar con sufijo `_hogar`. |
| `_fix_mixed_type_columns(df)` | Castea a `str` las columnas `object` con tipos mezclados (ej. `CH05`) para pyarrow. |
| `build_panel(quarters, search_dirs, out_dir, overwrite)` | Un trimestre por vez: carga, merge, agrega `ANIO`/`TRIMESTRE`, guarda parquet, libera memoria. Con `overwrite=False` saltea los existentes. Devuelve lista de dicts (resumen). |
| `load_panel(columns, quarters, out_dir)` | Concatena parquets leyendo solo las columnas pedidas que existan en cada trimestre (tolera el quiebre de esquema). Siempre agrega `ANIO`, `TRIMESTRE`. |

No existe un `eph_panel.parquet` único: 37 trimestres × ~330 cols desbordan la RAM de
Colab y superarían los 100 MB de GitHub.

## 3. Esquemas y tamaños

| Período | Cols individual | Cols hogar | Cols parquet (merge + ANIO) |
|---|---|---|---|
| T1-2017 → T3-2023 | 177 | 88 | 264 (T3-2021: 266) |
| T4-2023 → T4-2025 | 235 | 98 | 332 |
| T1-2026 | 234 | 98 | 331 |

T1-2026: 43.739 personas, 15.447 hogares, 0 personas sin hogar en el merge. La columna
faltante respecto de T4-2025 no fue identificada todavía (pendiente, no afecta notebooks).

Variables del esquema nuevo (primer dato en 2023T4): `EMPLEO`, `SECTOR`, `P_DECCF`,
`V2_01_M`, `V5_01_M` y demás desagregadas (ver `memoria_EPH.md` §2).

## 4. Gotchas resueltos (no reintroducir)

1. **RAM de Colab**: nunca concatenar todos los trimestres con todas las columnas;
   usar `load_panel(columns=...)`.
2. **FUSE de Drive** (`OSError [Errno 107] Transport endpoint is not connected`) al leer
   muchos parquets desde el mount → copiar primero a disco local (setup de 01-05).
3. **Coma decimal** del INDEC → `decimal=","` en `_read_csv`.
4. **Dtypes al concatenar**: si una columna viene como texto en algún trimestre, toda la
   columna queda `object` → `pd.to_numeric(col, errors="coerce")` antes de operar
   (helpers `cargar_ingresos` en 03, `cargar_hogares` en 04, `cargar` en 05).
5. **Naming irregular dentro de los zips**: mayúsculas variables, doble extensión
   (`.txt.txt`), T4-2020 con `personas` y `4to_trim2020` → resuelto en los parsers.
6. **Tipos mezclados** (`CH05`) → `_fix_mixed_type_columns` antes del parquet.
7. **`overwrite`** del 00 debe quedar en `False`; usar `True` solo si cambia la lógica de
   compilación (ej. un fix en `_read_csv`) y hay que regenerar todo (~36+ trimestres).
8. **Orden de ejecución**: subir zip ⇒ correr 00 ⇒ recién después 01-05 (ver
   `list_available_quarters` arriba).

## 5. Convenciones de análisis

- Ponderar siempre: `PONDERA` (general), `PONDIH` (ITF/IPCF), `PONDII` (P47T),
  `PONDIIO` (P21).
- Informalidad y variables desagregadas: filtrar `(ANIO, TRIMESTRE) >= (2023, 4)`.
- Ingresos: filtrar `IPCF >= 0` y no nulos (códigos de no respuesta `-9`).
- Hogares: un registro por hogar tomando al jefe (`CH03 == 1`).
- Métricas de ingreso del 03 son unit-free (Gini, shares, ratios) → no requieren deflactar.
  El 06 sí deflacta (IPC nacional, mes anterior a la entrevista; ver §6).
- No respuesta de ingresos: `P21 = -9` tiene `PONDIIO = 0`; las personas de hogares sin
  respuesta (~25%) tienen `PONDIH = 0`. Los ponderadores de ingreso suman el total de la
  población (ya corrigen la no respuesta): no hace falta imputar.
- Deciles en 03: cuantiles ponderados (`weighted_quantile`); ver pendiente de empates.

## 6. Notebook 06 — termómetro (v4)

**Se genera, no se edita a mano:** `python tools/gen_06_termometro.py` reescribe
`notebooks/06_termometro.ipynb` (cada `md()`/`code()` del script es una celda, en orden).
Editar el script, regenerar, probar con `tools/probar_06_local.py` y pushear.

Estructura del notebook (14 secciones + 2 anexos):

| # | Sección | Contenido |
|---|---|---|
| 1 | Setup | clona/actualiza repo, monta Drive, copia parquets a `/content/processed_local`, define `RESULTADOS_DIR`; imports, paleta (4 dimensiones), `FRANJAS`, `GRAFICOS_DIR` y `guardar_figura(fig, nombre)` (PNG 150 dpi en `resultados/graficos/`, se llama antes de cada `plt.show()`) |
| 2 | Carga | `PERS_COLS` / `HOG_COLS` con `load_panel` + `pd.to_numeric` (salvo `CODUSU`); hogares filtrados a `CH03==1`. `cargar_ipc()`: IPC nacional por API (respaldo `data/ipc_nacional.csv`) → `IPC_Q` (promedio de los meses de referencia = mes anterior a la entrevista) → `P21_REAL`, `IPCF_REAL`; `SIN_IPC` lista los trimestres sin deflactor |
| 3 | Indicadores + bootstrap | `INDICADORES` (nombre → base, ponderador, función → (numerador, denominador), tipo `pct`/`geo`); `UMBRAL_INGRESO`; un loop por trimestre arma sumas por vivienda (`CODUSU`) y calcula `ind` (puntual) e `ind_boot` (B × trimestres × indicadores) con multiplicadores Poisson `R` |
| 4 | Normalización | `DIMENSIONES`, `COMPLEMENTARIOS`, `DESESTACIONALIZAR`, `SIGNO`, `desestacionalizar`, `serie_indice`, `percentil_orientado`, `armar_termometro(dimensiones, datos=None)`, `termo` |
| 5 | Incertidumbre | arma el termómetro en cada réplica → `boot_t`, `boot_d`; `intervalo`, `resumen_incertidumbre` → `inc` (IC del nivel, variación i.a., P(sube), media móvil y su variación i.a.); `VAR_MIN` |
| 6 | Termómetro hoy | termómetro vertical con IC + dimensiones (con IC) vs mismo trimestre del año anterior |
| 7 | Lectura del último trimestre | `resumen_trimestre(q)` → Markdown (`resumen`): ranking y "desde cuándo" + IC, variación i.a. con IC/significancia/P(sube) y aporte por dimensión (Δdim/4), media móvil y su variación i.a., indicadores en récord o percentil ≥ 80, mayores movimientos i.a., complementarios que se movieron (≥ 1 pp o ≥ 5%); aviso si falta una dimensión |
| 8-10 | Gráficos | evolución (banda IC 95%, media móvil 4T, franjas), dimensiones, mapa de calor de percentiles |
| 11 | Tabla | último trimestre vs año anterior (pp para %, variación % para pesos), percentil y sentido |
| 12 | Promedios anuales | `anual` (con `Trimestres` para marcar el año incompleto) + barras por franja |
| 13 | Controles de calidad | cobertura, tamaño de muestra, chequeo de sentido (máximo 2019-2021, pandemia > 66, valle 2023 en el tercio inferior, D > 66 en 2024T1-T2), códigos de `PP11O` y `CH08` por esquema (`dist_codigos`) |
| 14 | Exportar | `termometro_EPH.csv` (`pct_`/`pesos_`, `perc_`, termómetro, `Termómetro IC ...`), `termometro_EPH_anual.csv`, `termometro_EPH_resumen.md` en `carga_EPH/resultados/`; lista los PNG de `graficos/` (`01_termometro_hoy`, `02_evolucion`, `03_dimensiones`, `04_mapa_calor`, `05_promedios_anuales`; `anexoA_candidatas` si hay candidatas) |
| A | Diagnóstico de candidatas | `CANDIDATAS` (vacío por defecto), 6 criterios + error estándar, índice actual vs con candidatas; registro de evaluaciones |
| B | Historial de versiones | v1 → v4 y valores de referencia |

Piezas clave:
- **Un indicador se define una sola vez** en `INDICADORES`: `(base, ponderador, f, tipo)`, con
  `f(g) -> (numerador, denominador)` por fila. `tipo="pct"`: Σw·num/Σw·den × 100;
  `tipo="geo"`: media geométrica (el numerador es `log` del ingreso real, el denominador la
  máscara del universo). El numerador puede estar fuera del denominador (desalentados / PEA).
  Para sumar/quitar del índice: definirlo ahí y editar `DIMENSIONES`.
- **Bootstrap:** multiplicadores Poisson(1) por vivienda (`R`, `B_BOOT = 200`, `SEMILLA` fija);
  la misma vivienda recibe el mismo multiplicador en todos los trimestres (respeta el panel
  rotativo, importante para las variaciones i.a.). Las réplicas reconstruyen el índice completo
  (percentiles incluidos). IC = intervalo percentil centrado en el valor puntual. No conoce el
  diseño muestral (áreas, estratos): los IC son aproximados, probablemente algo angostos.
- **Ingresos (D):** deflactor `IPC_Q` = promedio del IPC nacional (`148.3_INIVELNAL_DICI_M_26`,
  dic-2016 = 100) de los meses de referencia (el T1 usa dic, ene, feb). Ingreso laboral real =
  media geométrica de `P21`/IPC de ocupados con `P21 > 0`, ponderada con `PONDIIO`. Ingreso
  bajo = `IPCF`/IPC < `UMBRAL_INGRESO` (60% de la mediana ponderada del IPCF real 2017-2019 =
  $3.123 de dic-2016 por persona), ponderado con `PONDIH`. Ambos se desestacionalizan
  (`desestacionalizar`: media móvil centrada 2x4, factor = mediana del desvío por trimestre del
  año sin 2020T1-2021T2) porque los meses de referencia del T1 y el T3 incluyen aguinaldo. Si
  falta el IPC del último trimestre, D queda vacía ahí, la cobertura da ⚠ y la lectura avisa.
- **IPC de respaldo:** `data/ipc_nacional.csv` (copia del CSV de la API). Actualizarlo de vez en
  cuando:
  `curl -s "https://apis.datos.gob.ar/series/api/series/?ids=148.3_INIVELNAL_DICI_M_26&format=csv&limit=5000" -o data/ipc_nacional.csv`.
- `resumen_trimestre(q)` funciona para cualquier trimestre; `posicion(serie, q)` decide si
  describirlo como "más alto" o "más bajo" según su ranking. `fv`/`fd` formatean según `UNIDAD`.
- **Efecto composición:** en shocks que destruyen empleo precario y de bajos ingresos (2020T2),
  los indicadores sobre ocupados mejoran artificialmente (subocupación, buscan otro empleo,
  asalariados sin descuento, ingreso laboral). Cada dimensión afectada tiene al menos un
  indicador sobre población (asalariados registrados y cobertura de salud en B; ingreso bajo en D).
- Los percentiles son relativos a la historia disponible: al sumar trimestres, los valores
  históricos del índice se mueven (en v3 el último trimestre se movió en promedio 3,8 pts,
  máximo 12,7, al llegar los siguientes). Esperable, no un bug.
- Códigos de variables verificados contra el PDF oficial `EPH_registro_4T2025.pdf`; ver
  `.claude/memoria_EPH.md` §9.

**Evaluación v3 → v4 (2026-10):** con los 37 trimestres reales en la PC y 300 réplicas se
compararon 15 candidatas y 10 variantes de metodología (z-scores, min-max, desestacionalizar
todo, pesos PCA o por indicador, C ponderada por personas) contra pobreza oficial, EMAE i.a. y
confianza del consumidor UTDT, más señal/ruido, revisiones y estacionalidad. Las variantes de
metodología correlacionan 0,93-0,98 con el índice (cambio de segundo orden); las candidatas
nuevas eran redundantes o ruidosas (detalle en el Anexo A). Lo que mejoró fue: IC (la i.a. de
+11 de v3 en 2026T1 tenía IC −0,2 a +22,6), sin cobertura en lugar de sin descuento y la
dimensión D (corr. con la pobreza 0,29 → 0,60).

**Probar en la PC (con datos reales):** `python tools/probar_06_local.py --descargar` baja del
INDEC los zips que falten a `data/raw/`, compila los parquets que falten a `data/processed/`
(ambos ignorados por git) y ejecuta todas las celdas del notebook salvo el setup de Colab
(CSV, resumen y `graficos/` en `data/processed/resultados_06/`, el equivalente local de
`carga_EPH/resultados/`). Corre en
~30 s una vez compilado (la compilación inicial ~1,5 min). Los números coinciden con Colab
(verificado: réplica exacta de v3, y el CSV de v4 idéntico al de Colab, bootstrap incluido). En Windows usar `PYTHONUTF8=1` (la salida usa ✓/⚠/↑/↓).

## 7. Notebook 07 — nowcast del termómetro (D 2026-10-20; A, B y C 2026-10-21)

**Se genera:** `python tools/gen_07_nowcast.py`. La lógica vive en `src/nowcast.py`; el notebook
solo la llama y muestra. Probar: `python tools/probar_07_local.py` (correr antes el 06 si cambió:
el 07 toma de `termometro_EPH.csv` los indicadores de A, B y C y compara contra él D, las
dimensiones y el termómetro). Salidas en `carga_EPH/resultados/nowcast/` (local:
`data/processed/resultados_06/nowcast/`). ~5 min local (los backtests del termómetro son lo que tarda:
el principal y los tres sin cada predictor de la sección 7).

**Objetivo:** tener el termómetro antes de que salga la EPH (~85 días después del trimestre),
corregirlo cuando sale y registrar cada versión. Cada indicador se proyecta en sus unidades (D por
microsimulación, A, B y C por ecuaciones puente) y pasa por la normalización del 06 (`termometro`).
Lo que sigue hasta "Resultados del backtest" es la parte de D; A, B y C al final de la sección.

Piezas de `src/nowcast.py`:
- **Series (`SERIES`)**: id de datos.gob.ar, desfase en meses y rezago de publicación en días (este
  solo para el backtest). IPC `148.3_INIVELNAL_DICI_M_26`; salarios registrado privado
  `149.1_SOR_PRIADO_OCTU_0_25`, público `149.1_SOR_PUBICO_OCTU_0_14`, no registrado
  `149.1_SOR_PRIADO_OCTU_0_28`; haber mínimo `58.1_MP_0_M_24`; AUH `165.1_AAUH_0_0_3`. Respaldo
  `data/series_nowcast.csv` (tal como vienen de la API, sin desfasar; `nc.actualizar_respaldo(ruta)`
  lo reescribe solo si vinieron todas). Bono previsional: `data/bono_previsional.csv`, copia
  manual de `IPC_jubilados/data/reference/` (actualizar en los dos repos). RIPTE (`158.1_REPTE_0_0_5`)
  vino vacío de la API: no se usa.
- **No registrado realineado 6 meses** (`desfase`): la API lo fecha en el mes de publicación.
  Correlación de la variación i.a. con el `P21` nominal de los asalariados no registrados de la
  EPH: 0,874 sin desfase, 0,982 con 5 (rezago que informa el INDEC), 0,988 con 6.
- **Microdatos (`preparar_base`)**: cada ingreso de cada persona va a una clase (`INDICE_DE_CLASE`):
  `P21`+`TOT_P12` según grupo (asalariado registrado público `PP04A==1` / privado, no registrado,
  cuentapropista o patrón → índice no registrado); `V2*`+`V21*` (jubilaciones + aguinaldo) →
  haber mínimo, o mínimo + bono si el haber es ≤ 1,05 × (mínimo + bono); `V5_M`/`V5_01_M` → AUH; el
  resto de los `V*_M` → IPC. Se suman por hogar (`Y`, hogares × clases). Identidades verificadas en
  T126: `T_VI` = Σ `V*_M` (99,99%), `ITF` = Σ `P47T` e `IPCF` = `ITF`/`IX_TOT` (100%).
- **Microsimulación (`indicadores`)**: `log P21` + log del factor de su clase; `IPCF` × factor del
  hogar (Σ g·Y / Σ Y); deflactor = IPC promedio de los meses de referencia. Mismas fórmulas que
  `INDICADORES` del 06: con factores 1 da el oficial (control de la sección 3 del 07: diferencia
  < 1e-6 en los 37 trimestres, incluida D).
- **Proyección (`proyectar_indicadores`)**: método `"estacional"` = microsimulación desde la última
  base + (factor estacional del objetivo − el de la base), con los factores del 06 estimados hasta
  la base. `"anual"` (base = mismo trimestre del año anterior) erra el doble: queda solo como
  comparación. Meses sin dato (`extender`): mediana de las últimas 3 variaciones; el no registrado
  sigue al registrado privado mientras éste tiene dato (`GUIA`) y después su propia tendencia
  (seguir también la tendencia estimada del privado empeoró el backtest); el bono queda constante.
- **D**: `dimension_D` usa copias exactas de `desestacionalizar` y `percentil_orientado` del 06.
  `D_tiempo_real` = D de cada trimestre cuando era el último (contra eso se mide el error).
- **Backtest (`backtest`, `grilla_horizontes`, `resumir`)**: objetivos 2019T1 → último; k (trimestres
  entre base y objetivo) 1-3 y días respecto del cierre del objetivo −75, −30, 0, 45, 80, 120, solo
  si la base ya podía estar publicada (días ≥ 85 − 90·k). Las series se recortan a lo publicado en
  esa fecha (`publicado`). Benchmarks: último D publicado y persistencia (base + estacionalidad).
  RMSE sin 2020T2-2021T1. Limitación: usa las series actuales, no las versiones de cada momento.
- **Deriva (`estimar_deriva`, `aplicar_deriva`)**: corrige el sesgo con los últimos errores a k=1 ya
  conocidos. Probado con ventanas 4, 8, 12 y todos: baja el sesgo de D pero no el error cuadrático
  y empeora el ingreso laboral → no se usa; el 07 la muestra solo como alternativa (sección 5).
- **Funciones solo de D** (`backtest`, `resumir`, `error_esperado`): quedan para comparar los métodos
  de D (sección 5 del 07, "Alternativas"); el nowcast usa las del termómetro completo (abajo).
- **Registro (`registrar`, `conciliar`)**: ver "A, B y C" abajo (`filas_registro` es general).

**Resultados del backtest (2026-10-20, 25 trimestres sin pandemia):**

| Horizonte | D: proyección | D: repetir el último | Ingreso laboral real | Ingreso bajo |
|---|---|---|---|---|
| k=1, 80 días después del cierre | 9,5 pts | 14,8 | 3,5% (persistencia 6,4%) | 1,8 pp (3,3) |
| k=2, al cierre | 14,5 | 21,8 | 4,6% (9,8%) | 2,7 pp (4,7) |
| k=3, 75 días antes del cierre | 19,9 | 26,4 | 5,6% (11,2%) | 3,3 pp (5,3) |

Sesgo: la proyección es algo pesimista (+2,7 pts de D a k=1, +5 a +10 a k=2-3; los ingresos de la
EPH crecen ~0,3-0,5% por trimestre más que los índices). Mayor error: 2025T1 (+36,7 pts; el
ingreso laboral real de la EPH subió 10% contra el trimestre anterior). Un error de 3% en el
ingreso laboral puede mover D ~10 pts si cae en una zona densa de la historia.

### A, B y C: ecuaciones puente (2026-10-21)

- **Oficiales:** `leer_oficiales(csv06, oficiales_D)` toma del CSV del 06 los 13 indicadores de A, B
  y C (`pct_`) y les suma los 2 de D recalculados. `DIMENSIONES` y `termometro` son copias del 06
  (solo los ingresos se desestacionalizan): control del 07 = dimensiones y termómetro idénticos al
  CSV (dif. < 1e-6). `termometro_tiempo_real` = cada trimestre tal como lo mostró el 06 cuando era
  el último (contra eso se mide el error).
- **Predictores (`SERIES`):** EMAE desestacionalizado `143.3_NO_PR_2004_A_31` (rezago ~55 días),
  SIPA asalariados sin estacionalidad privados `151.1_AARIADOTAC_2012_M_26`, públicos `_25` y casas
  particulares `_40` (~100 días; se suman en `sipa_asal`), confianza del consumidor UTDT bienes
  durables e inmuebles `380.3_DESAGREGACLES_0_T_50` (sale en el mes). También se bajan, sin usar, la
  EIL `50.3_ICS_0_M_12` y el ICC general `380.3_ICC_NACIONNAL_0_T_12`. Trimestres calendario
  (`meses_cal`), log × 100 salvo la confianza (nivel). Meses sin dato: tendencia de los últimos 3
  (la confianza, constante; dejar constantes también EMAE y SIPA empeoró el backtest: termómetro a
  k=3 8,8 → 11,2).
- **API:** algunas series vienen vacías de la API todo un día; `_bajar_serie` baja entonces el CSV de
  la distribución (URL y columna salen de `metadata=full`, que sí responde).
- **`puente`:** sobre el indicador desestacionalizado (factores del 06 hasta la base),
  Δy_t = Σ β_j·Δx_{j,t}, sin constante, MCO con los trimestres hasta la base sin 2020T1-2021T2;
  proyección = último valor + Σ β·Δx + estacionalidad. Sin predictores = persistencia. El término
  autorregresivo (`ar=True`: los cambios de la EPH revierten, autocorrelación hasta −0,48) empeora
  el backtest: desactivado.
- **`PREDICTORES`:** los mismos tres (EMAE, `sipa_asal`, `icc_dur`) para los 13 indicadores. Elegir
  por indicador los de mayor correlación da parecido (termómetro 4,2 vs 4,3 a k=1) pero es
  optimista (usa el período evaluado).
- **`proyectar_termometro`:** D (`proyectar_indicadores`) + A, B y C (`proyectar_abc`) con las series
  preparadas una vez; los 15 se agregan a la historia y pasan por `termometro`. Backtest:
  `backtest_termometro` (formato largo, una fila por objetivo, horizonte y serie) y
  `resumir_termometro`; bandas: `error_esperado_serie` (RMSE de cada serie en el horizonte más
  parecido). Registro (`nowcast/registro_versiones.csv`, CSV estándar): `filas_registro` (una fila
  por serie: termómetro, dimensiones y 15 indicadores, con IC ±1,96 × RMSE acotados a 0-100 / ≥ 0),
  `registrar` (clave `fecha_corrida`, `version`, `trimestre`, `indicador`: una corrida del mismo día
  y versión reemplaza a la anterior) y `conciliar(reg, oficiales, termometro_tiempo_real(...))`
  (completa `oficial` y `error` = proyectado − oficial cuando el trimestre ya tiene EPH; acepta las
  filas viejas de la versión `D-microsim v1`).

**Estructura del notebook 07** (9 secciones + anexo; versión `VERSION = "termómetro v1"`):

| # | Sección | Contenido |
|---|---|---|
| 1 | Setup | clona/actualiza repo, monta Drive, copia parquets, `RESULTADOS_DIR`; imports (`importlib.reload(nc)`), paleta del 06, `NOWCAST_DIR`, `guardar_figura`, `FECHA_CORRIDA` (hoy), `VERSION`, `SERIES_T` |
| 2 | Series | `cargar_series` (API → CSV de la distribución → respaldo del repo) y tabla con origen y último mes de cada una |
| 3 | Oficiales | `cargar_bases` (microdatos + D), `leer_oficiales` (A, B y C del CSV del 06), `T_rt`, `T_hoy`; control contra el 06 (✓ si dif. < 1e-6) y aviso si hay microdatos que el 06 no procesó |
| 4 | Qué mueve la proyección | `variaciones` (índices de D) y `variaciones_abc` (predictores) entre la última EPH y el trimestre más lejano |
| 5 | Backtest | `backtest_termometro` + `resumir_termometro` (grilla completa), lectura, tabla por indicador, alternativas (A, B y C con persistencia; D "anual" y con corrección de sesgo), gráficos `nowcast_01_error_por_horizonte` y `nowcast_02_backtest` |
| 6 | Nowcast hoy | `proyectar_termometro` para cada trimestre sin EPH (por separado), bandas `error_esperado_serie`, tabla con IC, lectura interanual, tabla de indicadores, gráficos `nowcast_05_evolucion` (serie del 06 con su IC y media móvil 4T + proyección) y `nowcast_03_hoy` (termómetro y dimensiones) |
| 7 | Robustez | `robustez_subperiodos`, `robustez_calibracion`, `convergencia`, `dependencia_predictores`, `alertas_robustez` |
| 8 | Registro | `registrar` + `conciliar`, errores de las versiones con EPH, gráfico `nowcast_04_versiones` |
| 9 | Exportar | `nowcast_termometro.csv`, `backtest_termometro.csv`, `backtest_termometro_resumen.csv` (`;` y `,`), `robustez_termometro.md`; lista los PNG |
| Anexo | Decisiones y pruebas | evidencia de cada decisión de D y de A, B y C |

**Resultados del backtest del termómetro (2026-10-21, 25 trimestres sin pandemia, RMSE en pts):**

| Horizonte | Termómetro | Repetir el último | A, B y C con persistencia |
|---|---|---|---|
| k=1, 80 días después del cierre | 4,1 | 7,2 | 5,5 |
| k=2, al cierre | 7,0 | 12,1 | 9,6 |
| k=3, 75 días antes del cierre | 8,8 | 15,2 | 13,9 |

Por dimensión (k=1, 80 días; puente vs persistencia): A 11,4 vs 12,0; B 14,2 vs 14,1; C 7,4 vs 8,7;
a k=2 al cierre A 11,9 vs 15,4, B 18,2 vs 19,1, C 14,8 vs 13,8. **Ojo:** a k=1 la mayor parte de la
mejora del termómetro viene de que los errores de B quedan correlacionados negativamente con los
de A y C (−0,30 y −0,40; con persistencia, −0,04 y −0,08) y se compensan en el promedio (varianza
del promedio de las dimensiones 30,2 → 17,9, con la suma de las varianzas casi igual): puede no
repetirse, así que el 4,1 es optimista (lo esperable está entre 4,1 y 5,5). A k ≥ 2 la mejora de A
es sólida. Por indicador, el puente le gana a la persistencia en 5 de 13 (despidos +9%,
subocupación +7%, vendieron pertenencias +8%, tasa de empleo y desocupación +2%) y pierde en el
resto (hasta −19% en asalariados registrados): la ganancia está en el agregado.

Nowcast al 21/10/2026 (base 2026T1, termómetro 52,8): 2026T2 = 62,8 (IC 54,5-71,1), 2026T3 = 58,6
(44,8-72,4), 2026T4 = 54,1 (36,8-71,4). La suba contra T1 es sobre todo estacional (el T2 es peor
que el T1 en B y C; solo con persistencia daría 60,3); contra el mismo trimestre de 2025: +12,0,
+12,5 y +4,6. EMAE cae en jul-2026 (−2,9% mensual) y la tendencia lo arrastra a los meses sin dato.

**Robustez (2026-10-21, sobre el backtest local; sin pandemia).** Se recalcula en cada corrida en la
sección 7 del 07 (`robustez_subperiodos`, `robustez_calibracion`, `convergencia`,
`dependencia_predictores` y la lectura ✓/⚠ de `alertas_robustez`, que se exporta a
`nowcast/robustez_termometro.md`; horizontes en `HORIZONTES_ROBUSTEZ`, versiones en `CALENDARIO`).
Umbrales de las alertas: sesgo significativo si |sesgo| > 1,96 × su error estándar; intervalos
angostos si cubren < 85%; el error de las versiones no puede subir más de 0,3 pts; un predictor es
crítico si sacarlo sube el error > 20% en algún horizonte. Resultados al 2026-10-21:
- **Sesgo:** ninguno significativo en el termómetro (+0,2 pts a k=1, EE 0,8; +1,3 a k=3, EE 1,8).
- **Estabilidad:** mejora en los dos subperíodos, pero mucho más en 2023-2026 (k=1: 2,5 vs 7,6 de
  repetir el último) que en 2019-2022 (5,4 vs 6,8). Le gana a repetir el último en 60-64% de los
  trimestres. B en 2019-2022 y C a k ≥ 2 en 2019-2022 son peores que repetir el último.
- **Intervalos de 95%:** cubren el dato oficial en 92% (k=1), 96% (k=2) y 84% (k=3) de los trimestres;
  con el RMSE que se conocía en cada fecha cubren 100% (conservadores en 2023-2026).
- **Versiones:** el error baja ordenado a medida que llegan datos (calendario normal: −75 días 7,1;
  −30 6,7; al cierre, ya con la base nueva, 4,4; +45 4,2; +80 4,1). La corrección grande llega con la
  EPH nueva (revisión media 4,7 pts); después las revisiones son chicas (1-1,5) y solo ~60% acercan al
  oficial (el resto es ruido).
- **Dependencia de una serie:** sin SIPA el error sube a 5,3 / 9,4 / 13,1 (k=1/2/3; con SIPA 4,1 /
  7,0 / 8,8); sin confianza del consumidor 4,6 / 6,9 / 9,8; sin EMAE 3,9 / 7,6 / 8,5 (el EMAE casi no
  aporta). El SIPA es el predictor clave y sale con ~100 días.
- **Nowcast de hoy ante decisiones razonables** (predictores elegidos por indicador, término AR, sacar
  un predictor, meses sin dato constantes, no registrado corrido 5 meses, D con corrección de sesgo):
  2026T2 60,8-64,3 (elegido 62,8), T3 55,3-61,4 (58,6), T4 51,2-57,8 (54,1). En todas las variantes los
  tres quedan por encima del mismo trimestre de 2025 (50,8 / 46,1 / 49,4). Cada trimestre se proyecta
  por separado: si se agregan a la historia los siguientes trimestres proyectados, su percentil cambia
  ~1 punto (2026T2: 63,7 en vez de 62,8).

## 8. Entorno

- Colab: no requiere instalar nada extra (pandas, pyarrow, matplotlib, seaborn vienen).
- Local: `pip install -r requirements.txt` (pandas, numpy, matplotlib, seaborn, pyarrow,
  jupyter, requests). Python ≥ 3.10 (se usan type hints `tuple[int, int] | None`); probado con 3.14.
- Prueba completa del 06 con datos reales: `python tools/probar_06_local.py --descargar` (~30 s una
  vez compilado); del 07: `python tools/probar_07_local.py` (~5 min).
- Windows: `PYTHONUTF8=1` o `python -X utf8` (las salidas usan ✓/⚠/→). `python -I` ignora
  `PYTHONUTF8`: usar `python -X utf8 -I`. No usar heredocs de bash con backticks para editar
  archivos: escribir el script a un archivo y correrlo.
- Chequeo rápido local de un zip nuevo (sin Colab):

```python
import sys, zipfile; sys.path.insert(0, ".")
from src.data_loader import _parse_period_from_name, _base_type_from_name
zf = zipfile.ZipFile("EPH_usu_2_Trim_2026_txt.zip")
for n in zf.namelist():
    print(n, _parse_period_from_name(n), _base_type_from_name(n))
```
