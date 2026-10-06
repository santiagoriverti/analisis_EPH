# Documentación técnica — analisis_EPH

Referencia técnica del pipeline de datos y de los notebooks. Estado del proyecto y
próximos pasos: [`.claude/memoria.md`](../.claude/memoria.md). Diccionario de variables:
[`.claude/memoria_EPH.md`](../.claude/memoria_EPH.md).

## 1. Flujo de datos

```
INDEC (descarga manual)                Google Drive (Mi unidad)
EPH_usu_<Q>_Trim_<YYYY>_txt.zip  ──►   carga_EPH/*.zip
                                              │
                        00_preparacion_bases  │  build_panel(overwrite=False)
                                              ▼
                                       carga_EPH/processed/eph_T<Q><YY>.parquet
                                              │  (1 parquet por trimestre)
                   01-05: copia a /content/processed_local (shutil.copy)
                                              ▼
                              load_panel(columns=[...], quarters=[...])
```

- Rutas en Colab: `DRIVE_DIR = /content/drive/MyDrive/carga_EPH`,
  `DRIVE_PROCESSED = /content/drive/MyDrive/carga_EPH/processed`,
  `PROCESSED_DIR` (01-05) = `/content/processed_local`.
- Cada notebook clona (o hace `git pull` de) este repo en `/content/analisis_EPH` para
  importar `src/data_loader.py`. **Los cambios de código solo llegan a Colab después
  de pushearlos a `main`.**
- Alternativa local: poner `.zip`/`.txt` en `data/raw/` y usar `out_dir` por defecto
  (`data/processed/`). `tools/probar_06_local.py --descargar` baja los zips del sitio del
  INDEC, compila y corre el notebook 06 completo (ver §6, "Probar en la PC").

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
| 1 | Setup | clona/actualiza repo, monta Drive, copia parquets a `/content/processed_local`, define `RESULTADOS_DIR`; imports, paleta (4 dimensiones), `FRANJAS` |
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
| 14 | Exportar | `termometro_EPH.csv` (`pct_`/`pesos_`, `perc_`, termómetro, `Termómetro IC ...`), `termometro_EPH_anual.csv`, `termometro_EPH_resumen.md` en `carga_EPH/resultados/` |
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
(gráficos en `data/processed/figs_06/`, salidas en `data/processed/resultados_06/`). Corre en
~30 s una vez compilado (la compilación inicial ~1,5 min). Los números coinciden con Colab
(verificado: réplica exacta de v3, y el CSV de v4 idéntico al de Colab, bootstrap incluido). En Windows usar `PYTHONUTF8=1` (la salida usa ✓/⚠/↑/↓).

## 7. Entorno

- Colab: no requiere instalar nada extra (pandas, pyarrow, matplotlib, seaborn vienen).
- Local: `pip install -r requirements.txt` (pandas, numpy, matplotlib, seaborn, pyarrow,
  jupyter). Python ≥ 3.10 (se usan type hints `tuple[int, int] | None`).
- Prueba completa del 06 con datos reales: `python tools/probar_06_local.py --descargar`.
- Chequeo rápido local de un zip nuevo (sin Colab):

```python
import sys, zipfile; sys.path.insert(0, ".")
from src.data_loader import _parse_period_from_name, _base_type_from_name
zf = zipfile.ZipFile("EPH_usu_2_Trim_2026_txt.zip")
for n in zf.namelist():
    print(n, _parse_period_from_name(n), _base_type_from_name(n))
```
