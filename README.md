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

## Notebooks planificados

| Notebook | Tema | Colab |
|---|---|---|
| `01_demografia.ipynb` | Estructura poblacional: edad, sexo, composición de hogares, región | (pendiente) |
| `02_mercado_laboral.ipynb` | Empleo, desempleo, informalidad, subocupación | (pendiente) |
| `03_ingresos_pobreza.ipynb` | Distribución del ingreso, pobreza, indigencia, brechas | (pendiente) |
| `04_vivienda.ipynb` | Condiciones habitacionales, hacinamiento, acceso a servicios | (pendiente) |
| `05_educacion.ipynb` | Nivel educativo, asistencia escolar, analfabetismo | (pendiente) |

A medida que se publiquen, se agregan acá con su botón "Abrir en Colab"
(formato: `https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/<archivo>.ipynb`).

## Cómo agregar un trimestre nuevo

1. Descargar del INDEC el `.zip` del trimestre, ej. `EPH_usu_4_Trim_2025_txt.zip`
   (contiene `usu_individual_T425.txt` y `usu_hogar_T425.txt`).
2. Subir el `.zip` **sin descomprimir** a Google Drive, carpeta `carga_EPH`
   (Mi unidad > `carga_EPH`).
3. Volver a correr `notebooks/00_preparacion_bases.ipynb`: detecta automáticamente
   todos los trimestres presentes en `carga_EPH`, no hace falta editar nada en el código.

## Abrir en Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/00_preparacion_bases.ipynb) `00_preparacion_bases.ipynb`

## Notebook de preparación de bases

`notebooks/00_preparacion_bases.ipynb` es el punto de partida del proyecto: lee los
`.zip` del INDEC subidos a Google Drive (`carga_EPH`), une individuos con hogares por
`CODUSU` + `NRO_HOGAR`, y genera en `data/processed/`:

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
