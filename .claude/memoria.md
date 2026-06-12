# Memoria del proyecto: analisis_EPH

## Qué es

Repositorio de notebooks (Colab) para análisis de la Encuesta Permanente de Hogares (EPH,
INDEC, Argentina). Fuente de datos: librería `pyeph` + bases manuales en `data/raw/` para
los trimestres recientes que `pyeph` no tiene todavía.

## Decisiones de arquitectura (tomadas el 2026-06-12)

- **Repo**: `analisis_EPH`, público, en GitHub (`santiagoriverti`).
- **Notebooks planificados** (uno por tema, en `notebooks/`):
  1. `01_demografia.ipynb` — estructura poblacional, composición de hogares, región.
  2. `02_mercado_laboral.ipynb` — empleo, desocupación, informalidad, subocupación.
  3. `03_ingresos_pobreza.ipynb` — distribución del ingreso, pobreza, indigencia.
  4. `04_vivienda.ipynb` — condiciones habitacionales, hacinamiento, servicios.
  5. `05_educacion.ipynb` — nivel educativo, asistencia escolar, analfabetismo.
- **Carga de datos**: `src/data_loader.py::load_eph(year, period, base_type)` intenta
  `pyeph.get(...)` primero; si falla (trimestre no publicado aún en la librería), busca
  un archivo manual en `data/raw/usu_<base_type>_T<Q><YY>.{txt,xls}`.
- **Bases nuevas**: se suben manualmente por el usuario a `data/raw/` (sin automatizar
  scraping del sitio de INDEC).
- **Acceso desde Colab**: repo público, lectura vía `raw.githubusercontent.com` o
  `pip install pyeph` + `data_loader` clonando/descargando el repo dentro del notebook.

## Estado actual

- Estructura de carpetas creada (`notebooks/`, `data/raw/`, `data/processed/`, `src/`).
- `src/data_loader.py` con función `load_eph` y `list_available_quarters` implementadas
  (no probadas aún end-to-end — falta validar el esquema real de `pyeph.get()` y los
  nombres de columnas/diccionario de la EPH).
- README con estructura del proyecto y tabla de notebooks (links a Colab pendientes).
- Ningún notebook tiene contenido real todavía — son placeholders en la tabla del README.

## Notebook 00 - Preparación de bases (creado 2026-06-12)

`notebooks/00_preparacion_bases.ipynb`: clona el repo en Colab, instala `pyeph`,
intenta cargar individuos+hogares para una lista de trimestres (`QUARTERS`), reporta
los que faltan (para subir manualmente a `data/raw/`), y arma el panel uniendo
individuos+hogares por `CODUSU`+`NRO_HOGAR` (`merge_individual_hogar` /
`build_panel` en `src/data_loader.py`). Guarda `data/processed/eph_T<Q><YY>.parquet`
por trimestre y `data/processed/eph_panel.parquet` con todo concatenado
(+ columnas `ANIO`, `TRIMESTRE`).

Los notebooks 01-05 deberían leer directamente `eph_panel.parquet` (o el parquet
de un trimestre puntual) en lugar de volver a descargar/unir las bases.

## Próximos pasos

1. **Pendiente de validación end-to-end**: correr `00_preparacion_bases.ipynb` en
   Colab al menos una vez para confirmar que `pyeph.get()` funciona con la firma
   usada (`pyeph.get(data="eph", year=..., period=..., base_type=...)`) y que el
   merge individuos+hogares por `CODUSU`+`NRO_HOGAR` da `validate="m:1"` sin error
   (si pyeph devuelve columnas con otros nombres, ajustar `HOGAR_KEYS` en
   `src/data_loader.py`).
2. Una vez validado, comitear los `.parquet` generados en `data/processed/` (o
   decidir si son muy pesados y conviene Git LFS / releases).
3. Implementar `01_demografia.ipynb` leyendo `data/processed/eph_panel.parquet`.
4. Subir badges "Abrir en Colab" al README una vez los notebooks estén en GitHub.
5. Implementar el resto de notebooks (02-05) siguiendo el mismo patrón.
6. Si se suben bases manuales a `data/raw/`, documentar qué trimestres y de dónde
   se descargaron (en este archivo o en `data/raw/README.md`).

## Notas sobre la EPH (para tener en cuenta al diseñar los notebooks)

- Encuesta trimestral, dos tipos de base: **individual** (personas) y **hogar** (hogares).
- Variables clave típicas: `CH04` (sexo), `CH06` (edad), `ESTADO` (condición de
  actividad), `CAT_OCUP` (categoría ocupacional), `ITF`/`IPCF` (ingresos del hogar/per
  cápita), `NIVEL_ED` (nivel educativo), ponderadores `PONDERA`/`PONDIH`.
- Hay que usar los ponderadores (`PONDERA`, `PONDIH`, `PONDII`) para cualquier
  estadística representativa a nivel poblacional.
