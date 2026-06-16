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

A medida que se publiquen los notebooks 01-05 se agregan acá con su botón "Abrir en Colab"
(formato: `https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/<archivo>.ipynb`).

### Qué hace el notebook 00 (compilación)

1. Monta Google Drive y escanea `carga_EPH` (detecta automáticamente todos los trimestres).
2. Para cada trimestre, lee `usu_individual` y `usu_hogar` desde el `.zip` y los une por
   `CODUSU` + `NRO_HOGAR` (relación persona→hogar, sufijo `_hogar` para columnas duplicadas).
3. Agrega `ANIO`/`TRIMESTRE`, corrige columnas con tipos mezclados y guarda en
   `data/processed/` **un parquet por trimestre** (`eph_T<Q><YY>.parquet`), procesando
   un trimestre por vez para no desbordar la RAM de Colab. No se genera un único panel
   combinado (sería >100 MB, supera el límite de GitHub).
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
   todos los trimestres presentes en `carga_EPH`, no hace falta editar nada en el código.

## Setup local

```bash
pip install -r requirements.txt
```

## Diccionario de datos

Ver [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) para el **diccionario completo de
variables** de las bases hogar y personas (significado y valores de cada campo), el
mapa de claves de vínculo, los ponderadores y el **quiebre de esquema de 4T2023**.

## Memoria de proyecto

Ver [`.claude/memoria.md`](.claude/memoria.md) para el estado del proyecto, decisiones
de arquitectura y próximos pasos (usado para continuidad entre sesiones de Claude Code).
