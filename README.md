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
├── tools/            # Generadores (ej. gen_06_termometro.py crea el notebook 06)
├── docs/             # Documentación técnica (TECNICO.md)
└── .claude/          # Memoria/contexto del proyecto para sesiones de Claude Code
```

## Notebooks

El notebook **00** es el punto de partida: **compila** las bases (une individuos+hogares
de todos los trimestres) y genera los datasets procesados en `data/processed/`. El resto
de los notebooks (01-06) **parten de esos datasets** ya compilados, en lugar de descargar
y unir las bases de nuevo.

| Notebook | Tema | Colab |
|---|---|---|
| `00_preparacion_bases.ipynb` | **Compilación de datos**: lee los `.zip` del INDEC desde Drive, une hogar+personas por `CODUSU`+`NRO_HOGAR` y guarda un parquet por trimestre en `data/processed/` | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/00_preparacion_bases.ipynb) |
| `01_demografia.ipynb` | Estructura poblacional: pirámide edad×sexo, composición de hogares, región, evolución temporal | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/01_demografia.ipynb) |
| `02_mercado_laboral.ipynb` | Tasas de actividad/empleo/desocupación, subocupación, categoría ocupacional, informalidad | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/02_mercado_laboral.ipynb) |
| `03_ingresos_pobreza.ipynb` | Distribución del ingreso (IPCF), deciles, Gini, brechas D10/D1 | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/03_ingresos_pobreza.ipynb) |
| `04_vivienda.ipynb` | Tipo de vivienda, tenencia, servicios (agua/cloaca), hacinamiento, déficit | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/04_vivienda.ipynb) |
| `05_educacion.ipynb` | Nivel educativo, asistencia escolar, público/privado, analfabetismo | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/05_educacion.ipynb) |
| `06_termometro.ipynb` | **Termómetro de la economía de los hogares**: índice de malestar 0-100 (cantidad de empleo y despidos, calidad del empleo, estrategias de supervivencia de los hogares): lectura automática del último trimestre, evolución, mapa de calor, promedios anuales, controles de calidad y exportación a Drive | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/06_termometro.ipynb) |

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
tres dimensiones de igual peso. No usa ingresos ni pobreza (no depende de deflactores).

| Dimensión | Indicadores |
|---|---|
| Cantidad de empleo | desocupación, tasa de empleo, desocupación de más de 1 año, desocupados por despido o renuncia forzada |
| Calidad del empleo | subocupación, ocupados que buscan otro empleo, asalariados sin descuento jubilatorio, tasa de asalariados registrados |
| Estrés de los hogares | gastaron ahorros, préstamos de familiares, vendieron pertenencias, recibieron alimentos (gobierno/instituciones o familiares) |

**Cómo se calcula:** cada indicador se ubica en su percentil histórico (2017 en adelante,
orientado para que 100 = peor); cada dimensión promedia sus indicadores y el termómetro
promedia las tres dimensiones. Franjas: **Templado** (≤ 33), **Tibio** (≤ 66),
**Fiebre** (> 66). Es una medida *relativa a la historia*: 60 = peor que el 60% de los
trimestres observados.

**Qué muestra el notebook:** termómetro del último trimestre y sus dimensiones frente al
año anterior; una **lectura automática en texto** (posición en la serie, qué dimensión
explica la variación interanual, indicadores en récord y mayores movimientos); evolución
trimestral y por dimensión; mapa de calor de indicadores; tabla del último trimestre;
promedios anuales; **controles de calidad** automáticos (cobertura, tamaño de muestra,
chequeo de sentido, códigos de `PP11O`); y, en anexos, la herramienta para evaluar
indicadores candidatos y el historial de versiones.

**Salidas** (en Drive, `carga_EPH/resultados/`, CSV con `;` y decimal `,`):
`termometro_EPH.csv` (serie trimestral completa), `termometro_EPH_anual.csv` y
`termometro_EPH_resumen.md` (la lectura del último trimestre).

**Resultados (v3, T1-2017 → T1-2026):**

| Año | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (T1) |
|---|---|---|---|---|---|---|---|---|---|---|
| Termómetro | 29,9 | 43,8 | 65,9 | 72,3 | 64,4 | 41,6 | 26,2 | 49,0 | 54,3 | 60,0 |

- Máximo en 2020T4 (82,1); mínimos en 2017T4 (20,4) y 2023T3 (22,4).
- **2026T1 = 60,0 (Tibio), +11,0 puntos interanual**, el valor más alto desde 2021T2 (10.º
  de 37). La suba la explican el estrés de los hogares (+7,4) y la calidad del empleo
  (+6,7); la cantidad de empleo resta (−3,1). Hay empleo, pero más precario (asalariados
  sin descuento jubilatorio 37,9% = máximo de la serie) y los hogares usan reservas
  (préstamos de familiares p90, gastaron ahorros p89, vendieron pertenencias p81).

**Actualización trimestral:** después de correr el 00 con el trimestre nuevo, correr el 06
completo y revisar la sección 12 (todos ✓). El anexo A no hace falta (no hace nada salvo
que se carguen candidatas).

El notebook se genera con `python tools/gen_06_termometro.py` (no editar el `.ipynb` a
mano). Detalle metodológico en [`docs/TECNICO.md`](docs/TECNICO.md) §6 y diccionario de
variables en [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) §9.

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
