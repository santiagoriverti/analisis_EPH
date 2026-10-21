# Análisis EPH (Encuesta Permanente de Hogares)

Proyecto de notebooks reproducibles para analizar la **Encuesta Permanente de Hogares (EPH)**
del INDEC (Argentina, encuesta trimestral): https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos

Los notebooks están pensados para correr en **Google Colab**.

## Fuentes de datos

Las bases EPH se descargan **manualmente del INDEC** (sección "Bases de datos", microdatos
trimestrales) en formato `.zip` (ej. `EPH_usu_4_Trim_2025_txt.zip`), que contiene dos `.txt`
separados por `;`:
- `usu_individual_T<Q><YY>.txt`
- `usu_hogar_T<Q><YY>.txt`

Esos `.zip` se suben **sin descomprimir** a una carpeta de **Google Drive** llamada
`carga_EPH` (en la raíz de "Mi unidad"). El notebook `00_preparacion_bases.ipynb` monta
Drive, escanea esa carpeta, detecta automáticamente todos los trimestres disponibles,
une individuos+hogares y genera los datasets procesados en `data/processed/`.

Como alternativa (o complemento), también se pueden colocar `.zip` o `.txt` sueltos en
`data/raw/` del repo.

## Estructura del proyecto

```
analisis_EPH/
├── notebooks/        # Notebooks de análisis (Colab)
├── data/
│   ├── raw/          # Bases EPH descargadas manualmente (txt/xls del INDEC)
│   └── processed/    # Datasets intermedios/limpios generados por los notebooks
├── src/              # Funciones compartidas (carga de datos, armonización, utils)
├── tools/            # Generadores de los notebooks 06 y 07 (gen_06/gen_07) y pruebas locales
├── docs/             # Documentación técnica (TECNICO.md)
└── .claude/          # Memoria/contexto del proyecto para sesiones de Claude Code
```

## Notebooks

El notebook **00** es el punto de partida: **compila** las bases (une individuos+hogares
de todos los trimestres) y genera los datasets procesados en `data/processed/`. El resto
de los notebooks (01-07) **parten de esos datasets** ya compilados, en lugar de descargar
y unir las bases de nuevo.

| Notebook | Tema | Colab |
|---|---|---|
| `00_preparacion_bases.ipynb` | **Compilación de datos**: lee los `.zip` del INDEC desde Drive, une hogar+personas por `CODUSU`+`NRO_HOGAR` y guarda un parquet por trimestre en `data/processed/` | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/00_preparacion_bases.ipynb) |
| `01_demografia.ipynb` | Estructura poblacional: pirámide edad×sexo, composición de hogares, región, evolución temporal | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/01_demografia.ipynb) |
| `02_mercado_laboral.ipynb` | Tasas de actividad/empleo/desocupación, subocupación, categoría ocupacional, informalidad | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/02_mercado_laboral.ipynb) |
| `03_ingresos_pobreza.ipynb` | Distribución del ingreso (IPCF), deciles, Gini, brechas D10/D1 | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/03_ingresos_pobreza.ipynb) |
| `04_vivienda.ipynb` | Tipo de vivienda, tenencia, servicios (agua/cloaca), hacinamiento, déficit | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/04_vivienda.ipynb) |
| `05_educacion.ipynb` | Nivel educativo, asistencia escolar, público/privado, analfabetismo | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/05_educacion.ipynb) |
| `06_termometro.ipynb` | **Termómetro de la economía de los hogares**: índice de malestar 0-100 (cantidad de empleo y despidos, calidad del empleo, estrategias de supervivencia de los hogares, ingresos reales) con intervalos de confianza: lectura automática del último trimestre, evolución, mapa de calor, promedios anuales, controles de calidad y exportación a Drive | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/06_termometro.ipynb) |
| `07_nowcast.ipynb` | **Nowcast del termómetro (prototipo, solo dimensión D)**: proyecta los ingresos reales antes de que salga la EPH con una microsimulación sobre la última base (salarios por sector, haberes, AUH, IPC), backtest en pseudo tiempo real y registro de versiones que mide el error cuando llega la EPH oficial | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/07_nowcast.ipynb) |

**Cobertura actual:** 37 trimestres, **T1-2017 → T1-2026** (todos los notebooks validados en Colab).

### Qué hace el notebook 00 (compilación)

1. Monta Google Drive y escanea `carga_EPH` (detecta automáticamente todos los trimestres).
2. Para cada trimestre, lee `usu_individual` y `usu_hogar` desde el `.zip` y los une por
   `CODUSU` + `NRO_HOGAR` (relación persona→hogar, sufijo `_hogar` para columnas duplicadas).
3. Agrega `ANIO`/`TRIMESTRE`, corrige columnas con tipos mezclados y guarda en
   `data/processed/` **un parquet por trimestre** (`eph_T<Q><YY>.parquet`), procesando
   un trimestre por vez para no desbordar la RAM de Colab. No se genera un único panel
   combinado (sería >100 MB, supera el límite de GitHub). Con `overwrite=False` solo
   compila los trimestres que todavía no tienen parquet en Drive.
4. Reporta el **quiebre de esquema de 4T2023** (ver diccionario): los trimestres viejos
   (≤T3-2023) no tienen las variables nuevas (`EMPLEO`, `SECTOR`, ingresos desagregados, etc.).

Los notebooks 01-05 leen los datos con `load_panel(columns=..., quarters=...)`, pidiendo
solo las columnas y trimestres necesarios (evita cargar todo en memoria):

```python
from src.data_loader import load_panel
df = load_panel(columns=["CH06", "CH04", "REGION", "PONDERA"])  # ej. demografía
```

## Cómo agregar un trimestre nuevo

1. Descargar del INDEC el `.zip` del trimestre, ej. `EPH_usu_4_Trim_2025_txt.zip`
   (contiene `usu_individual_T425.txt` y `usu_hogar_T425.txt`).
2. Subir el `.zip` **sin descomprimir** a Google Drive, carpeta `carga_EPH`
   (Mi unidad > `carga_EPH`).
3. Volver a correr `notebooks/00_preparacion_bases.ipynb`: detecta automáticamente
   todos los trimestres presentes en `carga_EPH` y compila solo el nuevo; no hace falta
   editar nada en el código.
4. Recién después re-correr los notebooks 01-06: toman el último trimestre solos.
   (Si se corren antes del 00, fallan porque el parquet del trimestre nuevo no existe.)

## Termómetro de la economía de los hogares (notebook 06)

Índice trimestral de **malestar** de 0 (mejor trimestre de la serie) a 100 (peor), con
cuatro dimensiones de igual peso (v4, 2026-10).

| Dimensión | Indicadores |
|---|---|
| Cantidad de empleo | desocupación, tasa de empleo, desocupación de más de 1 año, desocupados por despido o renuncia forzada |
| Calidad del empleo | subocupación, ocupados que buscan otro empleo, personas sin cobertura de salud, tasa de asalariados registrados |
| Estrés de los hogares | gastaron ahorros, préstamos de familiares, vendieron pertenencias, recibieron alimentos (gobierno/instituciones o familiares) |
| Ingresos reales | ingreso real de la ocupación principal, personas con ingreso per cápita familiar real bajo |

**Cómo se calcula:** cada indicador se ubica en su percentil histórico (2017 en adelante,
orientado para que 100 = peor); cada dimensión promedia sus indicadores y el termómetro
promedia las cuatro dimensiones. Franjas: **Templado** (≤ 33), **Tibio** (≤ 66),
**Fiebre** (> 66). Es una medida *relativa a la historia*: 60 = peor que el 60% de los
trimestres observados. Los ingresos se deflactan con el IPC nacional del INDEC (se baja de
la API de datos.gob.ar; respaldo en `data/ipc_nacional.csv`), usando el mes anterior a la
entrevista, y se desestacionalizan por el aguinaldo.

**Incertidumbre:** la EPH es una muestra, así que el notebook calcula **intervalos de
confianza del 95%** con 200 réplicas bootstrap (remuestreo de viviendas) para el nivel, la
variación interanual y la media móvil. Una variación interanual tiene que superar ~10 puntos
para distinguirse del ruido; la media móvil de 4 trimestres tiene la mitad de ruido.

**Qué muestra el notebook:** termómetro del último trimestre (con su intervalo) y sus
dimensiones frente al año anterior; una **lectura automática en texto** (posición en la serie,
variación interanual y si es significativa, qué dimensión la explica, indicadores en récord y
mayores movimientos); evolución trimestral con banda de confianza y por dimensión; mapa de
calor de indicadores; tabla del último trimestre; promedios anuales; **controles de calidad**
automáticos (cobertura, tamaño de muestra, chequeo de sentido, códigos de `PP11O` y `CH08`); y,
en anexos, la herramienta para evaluar indicadores candidatos y el historial de versiones.

**Salidas** (en Drive, `carga_EPH/resultados/`, CSV con `;` y decimal `,`):
`termometro_EPH.csv` (serie trimestral completa con intervalos de confianza),
`termometro_EPH_anual.csv`, `termometro_EPH_resumen.md` (la lectura del último trimestre) y
`graficos/` con los 5 gráficos en PNG (`01_termometro_hoy` … `05_promedios_anuales`). Se
sobrescriben en cada corrida.

**Resultados (v4, T1-2017 → T1-2026):**

| Año | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (T1) |
|---|---|---|---|---|---|---|---|---|---|---|
| Termómetro | 24,1 | 35,0 | 58,2 | 76,6 | 66,4 | 47,2 | 35,0 | 58,3 | 48,4 | 52,8 |

- Máximo en 2020T4 (89,7); mínimo en 2017T4 (13,4). El shock de ingresos de 2024 se ve:
  2024T1 = 56,6 y 2024T2 = 64,4 (dimensión de ingresos en 100 y 97).
- **2026T1 = 52,8 (Tibio; IC 95% 44,4 a 60,6), +5,4 puntos interanual, que no se distingue
  del ruido muestral** (IC −4,4 a +15,1). La media móvil 4T (49,8) bajó 6,3 puntos en un año
  (significativo). Los ingresos reales se recuperaron (dimensión D en 31,9), pero el empleo es
  más precario (sin cobertura de salud 34,1%, p97; asalariados registrados p86) y los hogares
  usan reservas (préstamos de familiares p90, gastaron ahorros p89, vendieron pertenencias p81).

**Actualización trimestral:** después de correr el 00 con el trimestre nuevo, correr el 06
completo y revisar la sección 13 (todos ✓). El anexo A no hace falta (no hace nada salvo
que se carguen candidatas).

El notebook se genera con `python tools/gen_06_termometro.py` (no editar el `.ipynb` a
mano) y se puede probar en la PC con datos reales con `python tools/probar_06_local.py
--descargar`. Detalle metodológico en [`docs/TECNICO.md`](docs/TECNICO.md) §6 y diccionario
de variables en [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) §9.

## Nowcast del termómetro (notebook 07, prototipo)

La EPH sale ~85 días después de cada trimestre. El 07 **proyecta la dimensión D (ingresos
reales)** del termómetro antes de esa fecha: toma los microdatos de la última EPH y actualiza el
ingreso de cada persona con índices mensuales que se publican antes (índice de salarios del
INDEC por sector, haber mínimo y bono, AUH, IPC), recalcula los indicadores de D con las mismas
fórmulas del 06 y los normaliza igual. Cuando sale la EPH, el trimestre pasa a oficial y cada
versión guardada en el **registro de versiones** (`carga_EPH/resultados/nowcast/`) recibe su error.

**Backtest (2019-2026, sin pandemia):** con la EPH del trimestre anterior, la proyección de D erra
9,5 pts (RMSE) contra 14,8 de repetir el último dato publicado; el ingreso laboral real, 3,5%
(contra 6,4%), y el % de personas con ingreso bajo, 1,8 pp (contra 3,3). Si la EPH se demora (dos o
tres trimestres sin dato, como en oct-2026), el error sube a 12-20 pts, pero sigue debajo de
repetir el último (22-26).

**Nowcast al 20/10/2026** (base 2026T1, D = 31,9; el T2-2026 todavía no estaba publicado):
2026T2 D = 35 (IC 95% 17-53), 2026T3 = 32 (3-60), 2026T4 = 24 (0-63). Intervalos = ±1,96 × error
del backtest para ese horizonte.

Generado con `python tools/gen_07_nowcast.py`; prueba local `python tools/probar_07_local.py`
(después del 06). Detalle en [`docs/TECNICO.md`](docs/TECNICO.md) §7. Próximo paso: sumar A, B y
C con el mismo esquema.

## Continuar en otra PC

Los datos no están en el repo (viven en el Google Drive del usuario) y los notebooks
corren en Colab, así que en una PC nueva alcanza con:

1. Clonar el repo:
   ```bash
   git clone https://github.com/santiagoriverti/analisis_EPH.git
   ```
2. Configurar git con el usuario propio (`git config user.name "Santiago Riverti"`) y
   credenciales de GitHub (Git Credential Manager o `gh auth login`) para poder pushear.
3. Para trabajar con Claude Code: abrir la carpeta del repo; `CLAUDE.md` indica leer
   `.claude/memoria.md` (estado/pendientes), `docs/TECNICO.md` y `.claude/memoria_EPH.md`.
4. Para ejecutar: abrir cualquier notebook con su badge de Colab (usa la cuenta de Google
   que tiene la carpeta `carga_EPH`). Los cambios de código deben estar pusheados a
   `main` para que Colab los vea.

### Setup local (opcional)

```bash
pip install -r requirements.txt
```

Para correr localmente, poner los `.zip` del INDEC en `data/raw/` (no se versionan).
`python tools/probar_06_local.py --descargar` los baja del sitio del INDEC, compila los
parquets en `data/processed/` (ignorado por git) y corre el notebook 06 completo;
`python tools/probar_07_local.py` hace lo mismo con el 07 (nowcast).

## Documentación técnica

Ver [`docs/TECNICO.md`](docs/TECNICO.md): flujo de datos, funciones de
`src/data_loader.py`, esquemas por trimestre, gotchas resueltos y convenciones de análisis.

## Diccionario de datos

Ver [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) para el **diccionario completo de
variables** de las bases hogar y personas (significado y valores de cada campo), el
mapa de claves de vínculo, los ponderadores y el **quiebre de esquema de 4T2023**.

## Memoria de proyecto

Ver [`.claude/memoria.md`](.claude/memoria.md) para el estado del proyecto, decisiones
de arquitectura y próximos pasos (usado para continuidad entre sesiones de Claude Code).
