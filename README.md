# Análisis EPH (Encuesta Permanente de Hogares)

Proyecto de notebooks reproducibles para analizar la **Encuesta Permanente de Hogares (EPH)**
del INDEC (Argentina, encuesta trimestral): https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos

Los notebooks están pensados para correr en **Google Colab**, leyendo las bases desde este
repositorio público (`raw.githubusercontent.com`) o descargándolas directamente con la
librería [`pyeph`](https://github.com/institutohumai/pyeph).

## Fuentes de datos

1. **pyeph** (preferido): descarga las bases EPH oficiales (txt/xls → DataFrame) directamente
   en el notebook. No siempre tiene los últimos 1-2 trimestres disponibles.
2. **`data/raw/`**: bases de los trimestres más recientes que `pyeph` aún no tiene,
   descargadas manualmente desde el sitio del INDEC y subidas a este repo en formato
   `.txt` o `.xls` originales del INDEC.

Los notebooks combinan ambas fuentes: intentan `pyeph` primero, y si el trimestre buscado
no está disponible, caen a `data/raw/`.

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

## Notebooks planificados

| Notebook | Tema | Colab |
|---|---|---|
| `01_demografia.ipynb` | Estructura poblacional: edad, sexo, composición de hogares, región | (pendiente) |
| `02_mercado_laboral.ipynb` | Empleo, desempleo, informalidad, subocupación | (pendiente) |
| `03_ingresos_pobreza.ipynb` | Distribución del ingreso, pobreza, indigencia, brechas | (pendiente) |
| `04_vivienda.ipynb` | Condiciones habitacionales, hacinamiento, acceso a servicios | (pendiente) |
| `05_educacion.ipynb` | Nivel educativo, asistencia escolar, analfabetismo | (pendiente) |

Cada notebook va a tener un botón "Abrir en Colab" una vez publicado.

## Cómo agregar una base nueva manualmente

1. Descargar del INDEC los archivos `usu_individual_TxQyy.txt` y `usu_hogar_TxQyy.txt`
   (o `.xls`) del trimestre.
2. Subirlos a `data/raw/` renombrados como `usu_individual_T<Q><YY>.txt` y
   `usu_hogar_T<Q><YY>.txt`, por ejemplo `usu_individual_T424.txt` y
   `usu_hogar_T424.txt` para el T4 2024.
3. Agregar el trimestre a `QUARTERS` en `notebooks/00_preparacion_bases.ipynb` y correrlo.

## Notebook de preparación de bases

`notebooks/00_preparacion_bases.ipynb` es el punto de partida del proyecto: descarga
las bases (pyeph + `data/raw/`), une individuos con hogares por `CODUSU` + `NRO_HOGAR`,
y genera en `data/processed/`:

- `eph_T<Q><YY>.parquet`: un archivo por trimestre, individuos+hogares ya unidos.
- `eph_panel.parquet`: panel con todos los trimestres concatenados.

El resto de los notebooks (demografía, laboral, ingresos, vivienda, educación) parten
de estos archivos en lugar de descargar y unir las bases de nuevo.

## Setup local

```bash
pip install -r requirements.txt
```

## Memoria de proyecto

Ver [`.claude/memoria.md`](.claude/memoria.md) para el estado del proyecto, decisiones
de arquitectura y próximos pasos (usado para continuidad entre sesiones de Claude Code).
