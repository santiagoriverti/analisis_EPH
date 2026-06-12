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

1. Descargar la base del trimestre desde el sitio del INDEC (formato `.txt` o `.xls`).
2. Subirla a `data/raw/` con el nombre `usu_individual_<TyyTQQ>.txt` (o `.xls`),
   por ejemplo `usu_individual_T424.txt` para el T4 2024.
3. Los notebooks detectan automáticamente los archivos en `data/raw/` y los combinan
   con lo que devuelva `pyeph`.

## Setup local

```bash
pip install -r requirements.txt
```

## Memoria de proyecto

Ver [`.claude/memoria.md`](.claude/memoria.md) para el estado del proyecto, decisiones
de arquitectura y próximos pasos (usado para continuidad entre sesiones de Claude Code).
