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
  (`data/processed/`).

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
- Métricas de ingreso usadas son unit-free (Gini, shares, ratios) → no requieren deflactar.
- Deciles en 03: cuantiles ponderados (`weighted_quantile`); ver pendiente de empates.

## 6. Notebook 06 — termómetro

**Se genera, no se edita a mano:** `python tools/gen_06_termometro.py` reescribe
`notebooks/06_termometro.ipynb` (cada `md()`/`code()` del script es una celda, en orden).
Editar el script, regenerar, validar el JSON y pushear.

Estructura del notebook (11 secciones):

| # | Sección | Contenido |
|---|---|---|
| 1 | Setup | clona/actualiza repo, monta Drive, copia parquets a `/content/processed_local`, define `RESULTADOS_DIR`; imports, paleta, `FRANJAS` |
| 2 | Carga | `PERS_COLS` / `HOG_COLS` con `load_panel` + `pd.to_numeric`; hogares filtrados a `CH03==1` |
| 3 | Indicadores | `ind_personas(g)` / `ind_hogares(g)` → DataFrame `ind` (% por trimestre) |
| 4 | Normalización | `DIMENSIONES`, `COMPLEMENTARIOS`, `percentil_orientado`, `armar_termometro`, `termo` |
| 5 | Termómetro hoy | termómetro vertical + dimensiones vs mismo trimestre del año anterior |
| 6-8 | Gráficos | evolución (con media móvil 4T y franjas), dimensiones, mapa de calor de percentiles |
| 9 | Tabla | último trimestre vs año anterior, percentil y sentido de cada indicador |
| 10 | Diagnóstico de candidatas | `CANDIDATAS`, distribución de códigos por esquema, 6 criterios, índice actual vs con candidatas |
| 11 | Exportar | `carga_EPH/resultados/termometro_EPH.csv` |

Piezas clave:
- `DIMENSIONES`: dict dimensión → {indicador: signo} (+1 = más alto es peor, -1 = invertido).
  Para sumar/quitar un indicador del índice: calcularlo en la sección 3 y editar ese dict.
- `percentil_orientado(s, signo)`: rank promedio sobre `signo * s.round(1)` → 0-100.
- `armar_termometro(dimensiones)` → `(norm, dims, termómetro)`; termómetro = media de las
  dimensiones, cada dimensión = media de los percentiles de sus indicadores.
- **Agregar una candidata**: calcularla en la sección 3, listarla en `COMPLEMENTARIOS` y en
  `CANDIDATAS` (`nombre: (dimensión, signo)`), sumar su variable al loop de distribución de
  códigos, correr en Colab y leer la sección 10. Criterios: cobertura desde 2017; códigos
  estables entre esquemas; peor en pandemia (2020T2-2021T1) que en el valle 2023T3-T4;
  autocorrelación lag1 ≥ 0,3; Spearman con el termómetro ≥ 0,3; |corr| < 0,85 con cada
  indicador del índice.
- **Efecto composición:** en shocks que destruyen empleo precario (2020T2), los indicadores
  calculados sobre ocupados mejoran artificialmente. Por eso B incluye una tasa sobre
  población (asalariados registrados). **Chequeo de sentido** tras cualquier cambio:
  2020T2-2021T1 alto, 2023T3-T4 bajo, máximo en 2020T4.
- Los percentiles son relativos a la historia disponible: al sumar trimestres, los valores
  históricos del índice pueden moverse levemente (esperable, no un bug).
- Códigos de variables verificados contra el PDF oficial `EPH_registro_4T2025.pdf`; ver
  `.claude/memoria_EPH.md` §9.

**Testear sin Colab** (solo verifica que el código corre; los números reales salen en Colab):
1. Armar un parquet de un trimestre real: leer los `.xlsx`/`.txt` del INDEC, unir con
   `merge_individual_hogar`, agregar `ANIO`/`TRIMESTRE`, `_fix_mixed_type_columns`, guardar.
2. Generar trimestres sintéticos remuestreando hogares (`CODUSU`+`NRO_HOGAR` con reemplazo),
   con etiquetas que incluyan 2020T2-2021T1 y 2023T3-T4 (la sección 10 las usa) y sin
   `EMPLEO`/`SECTOR` en los previos a 2023T4.
3. Extraer las celdas de código (salteando el setup de Colab), fijar `PROCESSED_DIR`,
   `RESULTADOS_DIR`, backend `Agg`, reemplazar `list_available_quarters` por una lectura de
   los parquets, y ejecutar. En Windows usar `PYTHONIOENCODING=utf-8` (la tabla usa ↑/↓).

## 7. Entorno

- Colab: no requiere instalar nada extra (pandas, pyarrow, matplotlib, seaborn vienen).
- Local: `pip install -r requirements.txt` (pandas, numpy, matplotlib, seaborn, pyarrow,
  jupyter). Python ≥ 3.10 (se usan type hints `tuple[int, int] | None`).
- Chequeo rápido local de un zip nuevo (sin Colab):

```python
import sys, zipfile; sys.path.insert(0, ".")
from src.data_loader import _parse_period_from_name, _base_type_from_name
zf = zipfile.ZipFile("EPH_usu_2_Trim_2026_txt.zip")
for n in zf.namelist():
    print(n, _parse_period_from_name(n), _base_type_from_name(n))
```
