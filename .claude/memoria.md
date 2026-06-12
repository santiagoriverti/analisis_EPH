# Memoria del proyecto: analisis_EPH

## Qué es

Repositorio de notebooks (Colab) para análisis de la Encuesta Permanente de Hogares (EPH,
INDEC, Argentina). Fuente de datos: `.zip` de microdatos descargados manualmente del
INDEC y subidos a Google Drive (carpeta `carga_EPH`).

## Decisiones de arquitectura

- **Repo**: `analisis_EPH`, público, en GitHub (`santiagoriverti`).
- **Notebooks planificados** (uno por tema, en `notebooks/`):
  1. `01_demografia.ipynb` — estructura poblacional, composición de hogares, región.
  2. `02_mercado_laboral.ipynb` — empleo, desocupación, informalidad, subocupación.
  3. `03_ingresos_pobreza.ipynb` — distribución del ingreso, pobreza, indigencia.
  4. `04_vivienda.ipynb` — condiciones habitacionales, hacinamiento, servicios.
  5. `05_educacion.ipynb` — nivel educativo, asistencia escolar, analfabetismo.
- **Carga de datos** (actualizado 2026-06-12, NO usa `pyeph`):
  - Fuente: `.zip` del INDEC (ej. `EPH_usu_4_Trim_2025_txt.zip`), que contienen
    `usu_individual_T<Q><YY>.txt` y `usu_hogar_T<Q><YY>.txt` (separados por `;`,
    encoding `latin1`).
  - El usuario sube esos `.zip` **sin descomprimir** a Google Drive, carpeta
    `carga_EPH` (raíz de "Mi unidad"). En Colab se monta Drive con
    `google.colab.drive.mount('/content/drive')` → ruta
    `/content/drive/MyDrive/carga_EPH` (constante `DRIVE_DIR` en `src/data_loader.py`).
  - `src/data_loader.py::_find_sources()` escanea `DRIVE_DIR` y `data/raw/`, indexa
    cada `.zip`/`.txt` por `(year, period, base_type)` parseando el patrón `T<Q><YY>`
    del nombre de archivo (ej. `usu_individual_T425.txt` → (2025, 4, "individual")).
  - `load_eph(year, period, base_type)` lee el `.txt` directo desde el `.zip` (sin
    descomprimir a disco) o desde `data/raw/`.
  - `list_available_quarters()` devuelve los `(year, period)` que tienen AMBAS bases
    (individual + hogar) disponibles.
  - `build_panel(quarters=None, save=True)`: si `quarters` es None usa
    `list_available_quarters()`; une individuos+hogares por `CODUSU`+`NRO_HOGAR`
    (`merge_individual_hogar`), agrega `ANIO`/`TRIMESTRE`, corrige columnas con tipos
    mezclados (`_fix_mixed_type_columns`, necesario para exportar a parquet — ej.
    `CH05` viene como int en algunos trimestres y string en otros) y guarda
    `data/processed/eph_T<Q><YY>.parquet` + `data/processed/eph_panel.parquet`.
- **Bases nuevas**: el usuario las descarga manualmente del sitio del INDEC y las sube
  a Drive `carga_EPH` (no se automatiza scraping). Para agregar un trimestre nuevo NO
  hace falta tocar código: `00_preparacion_bases.ipynb` detecta automáticamente todo lo
  que haya en `carga_EPH`.
- **Acceso desde Colab**: se clona el repo público (`git clone`) para tener
  `src/data_loader.py`, y se monta Drive para los datos.

## Estado actual (2026-06-12)

- Estructura de carpetas creada (`notebooks/`, `data/raw/`, `data/processed/`, `src/`).
- `src/data_loader.py` reescrito sin dependencia de `pyeph` (ver arriba).
- `notebooks/00_preparacion_bases.ipynb`: monta Drive, lista trimestres disponibles en
  `carga_EPH`, construye el panel y lo guarda en `data/processed/`.
- README actualizado con el flujo de Drive y el badge "Abrir en Colab" de
  `00_preparacion_bases.ipynb`.
- Bases confirmadas disponibles en INDEC al momento de escribir: T1-2023 a T4-2025
  (T1-2026 se publica ~3 de agosto). El usuario está subiendo todos los `.zip` a Drive.
- Ningún notebook de análisis (01-05) tiene contenido todavía.

## Próximos pasos

1. **Pendiente de validación end-to-end**: correr `00_preparacion_bases.ipynb` en
   Colab una vez que el usuario haya subido los `.zip` a `carga_EPH`, confirmar que
   `list_available_quarters()` los detecta y que `build_panel()` corre sin errores.
2. Una vez validado, decidir si los `.parquet` de `data/processed/` se comitean al
   repo (pueden ser pesados — evaluar Git LFS o no versionarlos y que cada notebook
   corra 00 primero).
3. Implementar `01_demografia.ipynb` leyendo `data/processed/eph_panel.parquet`.
4. Agregar badges "Abrir en Colab" para cada notebook nuevo en el README.
5. Implementar el resto de notebooks (02-05) siguiendo el mismo patrón.

## Notas sobre la EPH (para tener en cuenta al diseñar los notebooks)

- Encuesta trimestral, dos tipos de base: **individual** (personas) y **hogar** (hogares).
- Variables clave típicas: `CH04` (sexo), `CH06` (edad), `ESTADO` (condición de
  actividad), `CAT_OCUP` (categoría ocupacional), `ITF`/`IPCF` (ingresos del hogar/per
  cápita), `NIVEL_ED` (nivel educativo), ponderadores `PONDERA`/`PONDIH`.
- Hay que usar los ponderadores (`PONDERA`, `PONDIH`, `PONDII`) para cualquier
  estadística representativa a nivel poblacional.
- Los `.txt` del INDEC están separados por `;` y en encoding `latin1`.
