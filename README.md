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
└── .claude/          # Memoria/contexto del proyecto para sesiones de Claude Code
```

## Notebooks

El notebook **00** es el punto de partida: **compila** las bases (une individuos+hogares
de todos los trimestres) y genera los datasets procesados en `data/processed/`. El resto
de los notebooks (01-05) **parten de esos datasets** ya compilados, en lugar de descargar
y unir las bases de nuevo.

| Notebook | Tema | Colab |
|---|---|---|
| `00_preparacion_bases.ipynb` | **Compilación de datos**: lee los `.zip` del INDEC desde Drive, une hogar+personas por `CODUSU`+`NRO_HOGAR` y guarda un parquet por trimestre en `data/processed/` | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/00_preparacion_bases.ipynb) |
| `01_demografia.ipynb` | Estructura poblacional: pirámide edad×sexo, composición de hogares, región, evolución temporal | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/01_demografia.ipynb) |
| `02_mercado_laboral.ipynb` | Tasas de actividad/empleo/desocupación, subocupación, categoría ocupacional, informalidad | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/02_mercado_laboral.ipynb) |
| `03_ingresos_pobreza.ipynb` | Distribución del ingreso (IPCF), deciles, Gini, brechas D10/D1 | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/03_ingresos_pobreza.ipynb) |
| `04_vivienda.ipynb` | Tipo de vivienda, tenencia, servicios (agua/cloaca), hacinamiento, déficit | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/04_vivienda.ipynb) |
| `05_educacion.ipynb` | Nivel educativo, asistencia escolar, público/privado, analfabetismo | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/05_educacion.ipynb) |
| `06_termometro.ipynb` | **Termómetro de la economía de los hogares**: índice compuesto 0-100 (cantidad y calidad del empleo + estrategias de supervivencia de los hogares), percentil histórico, evolución, mapa de calor y CSV en Drive | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/06_termometro.ipynb) |

**Cobertura actual:** 37 trimestres, **T1-2017 → T1-2026** (00-05 validados en Colab; 06 pendiente de validar).

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
4. Recién después re-correr los notebooks 01-05: toman el último trimestre solos.
   (Si se corren antes del 00, fallan porque el parquet del trimestre nuevo no existe.)

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
