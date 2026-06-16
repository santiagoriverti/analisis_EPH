# Memoria del proyecto: analisis_EPH

## ⭐ HANDOFF (última sesión: 2026-06-12) — leer esto primero

**Estado: notebook 00 (compilador) FUNCIONA end-to-end y validado en Colab.**

Lo logrado y verificado en Colab:
- Los 36 trimestres (T1-2017 → T4-2025, incluye T4-2020) se compilan a
  **un parquet por trimestre** guardado en **Google Drive**
  (`/content/drive/MyDrive/carga_EPH/processed/eph_T<Q><YY>.parquet`), persistente.
- Total: **1.825.881 filas**. Merge individuo+hogar OK (cada persona trae `ITF`/`IPCF` del hogar).
- Montos numéricos OK: `ITF` int64, `IPCF` float64 (ej. `2933333.33` con punto). Fix de
  coma decimal aplicado (`decimal=","` en `_read_csv`).
- Quiebre de esquema 4T2023 confirmado: `EMPLEO`, `SECTOR`, `P_DECCF`, `V2_01_M`,
  `V5_01_M` empiezan en 2023T4. Cols del merge: 264 (≤T3-2023) / 332 (≥T4-2023).

**Decisión tomada (Opción A):** los parquets viven en Drive (`carga_EPH/processed`), NO se
versionan en GitHub. Los notebooks 01-05 los leen con
`load_panel(columns=[...], quarters=[...], out_dir=PROCESSED_DIR)` donde
`PROCESSED_DIR = "/content/drive/MyDrive/carga_EPH/processed"`.

**PRÓXIMO PASO:** crear `02_mercado_laboral.ipynb` (empleo, desocupación, informalidad,
subocupación).

**`01_demografia.ipynb` VALIDADO en Colab (2026-06-12).** Corrió completo: pirámide
coherente (base angosta, viudez femenina en 80+), tamaño hogar promedio 2.96, edad
promedio ~35-36 con caída en 2020T2 (efecto pandemia en el operativo EPH), índice de
masculinidad ~92→95. La copia Drive→local resolvió la desconexión FUSE.

**GOTCHA Colab + Drive (importante para notebooks 01-05):** leer muchos parquets seguidos
directo desde el mount de Drive tira `OSError [Errno 107] Transport endpoint is not
connected` (FUSE se desconecta). **Solución aplicada en el notebook 01:** en el setup,
copiar UNA vez los parquets de `DRIVE_PROCESSED` (`/content/drive/MyDrive/carga_EPH/processed`)
a disco local (`PROCESSED_DIR = "/content/processed_local"`) con `shutil.copy`, y pasar ese
`PROCESSED_DIR` local a `load_panel`. Los notebooks 02-05 deben usar el mismo patrón.

**HECHO (sesión 2026-06-12, parte 2):** creado `notebooks/01_demografia.ipynb` con el
**set demográfico estándar** (lo eligió el usuario):
1. Pirámide de población edad×sexo (grupos quinquenales, último trimestre, ponderado).
2. Composición de hogares: parentesco (`CH03`) + tamaño del hogar (`IX_TOT`, 1 registro
   por hogar tomando el jefe CH03==1).
3. Población por región (`REGION`, último trimestre).
4. Evolución temporal: edad promedio e índice de masculinidad por trimestre (toda la serie).
Sigue el patrón de setup del notebook 00 (clonar repo + montar Drive + `PROCESSED_DIR`),
usa `load_panel(columns=[...], quarters=[...], out_dir=PROCESSED_DIR)` y pondera con
`PONDERA`. Detecta el último trimestre con `list_available_quarters()[-1]`. Badge Colab
agregado en la tabla del README. **Falta validarlo corriéndolo en Colab.**

**Cómo retomar en Colab:** abrir notebook desde el badge del README → Runtime → Restart and
run all → esperar a que termine la sección 4 ("Listo. Parquets en:") antes de seguir.
Los parquets ya están en Drive, así que para los notebooks 01-05 NO hace falta recompilar.

---

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
  - `_read_csv` usa `sep=";"`, `encoding="latin1"`, `decimal=","` (montos con coma decimal).
  - `build_panel(quarters=None, search_dirs=None, out_dir=None, overwrite=False)`:
    procesa **un trimestre por vez** (memory-safe), une individuos+hogares por
    `CODUSU`+`NRO_HOGAR` (`merge_individual_hogar`), agrega `ANIO`/`TRIMESTRE`, corrige
    columnas con tipos mezclados (`_fix_mixed_type_columns` — ej. `CH05` int/string según
    trimestre) y guarda **un parquet por trimestre** en `out_dir` (por defecto
    `data/processed/`, en el notebook se pasa la carpeta de Drive). Con `overwrite=False`
    saltea los ya compilados. Devuelve un resumen (lista de dicts), NO el DataFrame.
    Imprime progreso por trimestre.
  - `load_panel(columns=None, quarters=None, out_dir=None)`: lee los parquets por
    trimestre de `out_dir` y los concatena, tomando solo las columnas pedidas (si una
    columna no existe en un trimestre viejo, la saltea). Es la función que usan los
    notebooks 01-05. Lanza `FileNotFoundError` claro si no hay parquets.
  - **NO existe `eph_panel.parquet`** (un panel único superaría RAM de Colab y 100 MB de GitHub).
- **Bases nuevas**: el usuario las descarga manualmente del sitio del INDEC y las sube
  a Drive `carga_EPH` (no se automatiza scraping). Para agregar un trimestre nuevo NO
  hace falta tocar código: `00_preparacion_bases.ipynb` detecta automáticamente todo lo
  que haya en `carga_EPH`.
- **Acceso desde Colab**: se clona el repo público (`git clone`) para tener
  `src/data_loader.py`, y se monta Drive para los datos.

## Estado actual (2026-06-12)

- Estructura de carpetas creada (`notebooks/`, `data/raw/`, `data/processed/`, `src/`).
- `src/data_loader.py` reescrito sin dependencia de `pyeph` (ver arriba).
- `notebooks/00_preparacion_bases.ipynb`: **completo, validado y funcionando** en Colab.
  6 secciones numeradas: Setup → Diagnóstico → Trimestres disponibles → Compilación →
  Verificación merge/montos → Verificación esquema 4T2023. Guarda los parquets en Drive.
- README actualizado: notebook 00 en la tabla con badge "Abrir en Colab"; documentado el
  flujo Drive, `load_panel`, y el quiebre 4T2023.
- Bases en Drive: **36 trimestres T1-2017 → T4-2025** (T1-2026 se publica ~3 de agosto).
- Notebooks de análisis 01-05: **todavía sin contenido** (próximo paso: 01_demografia).

## Naming irregular dentro de los zips del INDEC (detectado 2026-06-12)

Los 36 zips de `carga_EPH` (T1-2017 a T4-2025) no son uniformes en los nombres internos:
- Mayúsculas/minúsculas variables (`usu_individual_t117.txt`, `Usu_individual_T417.txt`).
- Algunos con doble extensión (`usu_individual_T222.txt.txt`).
- **T4-2020 es un caso especial**: el zip trae
  `EPH_usu_personas_4to.trim_2020.txt` (usa "personas" en vez de "individual") y
  `EPH_usu_hogar_4to_trim2020_txt.txt` (sin el patrón `T420`).

Se agregó en `src/data_loader.py`:
- `_base_type_from_name`: ahora también reconoce `"personas"` como `"individual"`.
- `_parse_period_from_name`: además del patrón `T<Q><YY>`, soporta el patrón
  `<Q>to_trim<YYYY>` / `<Q>.trim_<YYYY>` (regex `_ORDINAL_TRIM_RE`) para casos como T4-2020.

Con esto los 36 trimestres (T1-2017 a T4-2025, incluyendo T4-2020) deberían quedar
disponibles en `list_available_quarters()`.

## Diccionario de datos EPH (creado 2026-06-12)

`.claude/memoria_EPH.md` es el **diccionario completo** de las bases EPH (hogar +
personas): significado y valores de cada variable, combinando el PDF oficial
`EPH_registro_4T2025.pdf` con la verificación de los headers reales de los 36 `.txt`.

Hallazgo crítico documentado ahí: **quiebre de esquema en 4T2023**.
- Hasta T3-2023: 177 cols individual / 88 cols hogar (esquema "viejo", ingresos agregados).
- Desde T4-2023: 235 cols individual / 98 cols hogar (esquema "nuevo": agrega `EMPLEO`,
  `SECTOR`, ingresos/pensiones desagregados, deciles `P_DECCF` de personas).
- Implicancia: al concatenar el panel, las columnas nuevas quedan NaN en trimestres
  viejos. Para informalidad/ingresos desagregados restringir a T4-2023+; para series
  largas usar solo variables comunes.

Consultar `memoria_EPH.md` antes de escribir cualquier notebook de análisis.

## Opción A: parquets persistentes en Drive (2026-06-12)

Decisión: los parquets compilados se guardan en **Google Drive**
(`/content/drive/MyDrive/carga_EPH/processed/`), no en el `data/processed/` efímero de
Colab. Así persisten y los notebooks 01-05 los leen sin recompilar.
- `build_panel(out_dir=..., overwrite=False)`: guarda en `out_dir`; con `overwrite=False`
  saltea trimestres ya compilados (para agregar solo nuevos).
- `load_panel(out_dir=...)`: lee de la misma carpeta.
- El notebook 00 define `PROCESSED_DIR = "/content/drive/MyDrive/carga_EPH/processed"` y
  lo pasa a ambas funciones.

## Fix coma decimal en montos (2026-06-12)

Al correr el notebook 00 OK con los 36 trimestres, se vio que `IPCF` (y otros montos)
venían como `2933333,33` (coma decimal del INDEC) → se leían como **texto**, rompiendo
cálculos. Fix: `_read_csv` ahora usa `decimal=","` en `pd.read_csv`. Tras esto los montos
(ITF, IPCF, P21, P47T, V*_M, etc.) quedan como float. Requiere re-correr el notebook 00.

Nota: conteo de columnas del merge = 264 (esquema viejo) / 332 (esquema nuevo desde
4T2023). Anomalía menor: T3-2021 dio 266 (2 columnas extra) — no bloquea, revisar si
algún análisis lo necesita.

## Refactor memory-safe (2026-06-12) — IMPORTANTE

Al correr el notebook 00 en Colab con los 36 trimestres, la sesión murió por RAM al
concatenar todo en un solo DataFrame. Cambios en `src/data_loader.py`:
- `build_panel(quarters=None)`: ahora procesa **un trimestre por vez**, guarda un parquet
  por trimestre (`eph_T<Q><YY>.parquet`) y libera memoria con `del`. **Ya NO concatena en
  RAM ni genera `eph_panel.parquet`** (un panel único de 36 trimestres × 235 cols
  superaría además el límite de 100 MB de GitHub). Devuelve un resumen (lista de dicts).
- Nueva función `load_panel(columns=None, quarters=None)`: lee los parquets por trimestre
  y concatena, leyendo solo las columnas pedidas (maneja el quiebre de esquema: si una
  columna no existe en un trimestre viejo, la saltea para ese archivo). Es la función que
  deben usar los notebooks 01-05.
- Import nuevo: `import pyarrow.parquet as pq` (para leer schemas por trimestre).

El notebook 00 se actualizó en consecuencia: `build_panel(available)` devuelve un resumen
(tabla de filas/columnas por trimestre); la verificación del merge y del esquema 4T2023
usan `load_panel` con columnas acotadas.

## Notebook 00 actualizado (2026-06-12)

`00_preparacion_bases.ipynb` quedó como el **notebook base/compilador** del proyecto.
Cambios:
- Intro reescrita: deja claro que compila los datos para que los notebooks 01-05 los
  procesen, y advierte el quiebre de esquema 4T2023.
- Celda de verificación del panel (filas/columnas, conteo por trimestre).
- Celda nueva que reporta, para cada variable del esquema nuevo (`EMPLEO`, `SECTOR`,
  `P_DECCF`, `V2_01_M`, `V5_01_M`), el primer trimestre con datos no nulos.
- En el README, el notebook 00 ahora está **en la misma tabla** que 01-05, con su badge
  "Abrir en Colab" (para ejecutarlo directo desde el README).

## Próximos pasos

1. **Implementar `01_demografia.ipynb`** (próximo, martes): pirámide edad×sexo, hogares,
   región/aglomerado, evolución temporal. Leer con `load_panel(..., out_dir=PROCESSED_DIR)`,
   ponderar con `PONDERA`. Preguntar al usuario qué cortes priorizar. Agregar badge Colab al README.
2. Implementar el resto de notebooks (02-05) siguiendo el mismo patrón.
3. (Opcional, baja prioridad) investigar la anomalía de T3-2021 (266 cols vs 264).
4. Cuando salga T1-2026 (~3 ago): subir su `.zip` a `carga_EPH` y correr el notebook 00
   con `overwrite=False` (compila solo el trimestre nuevo).

## Notas sobre la EPH (para tener en cuenta al diseñar los notebooks)

- Encuesta trimestral, dos tipos de base: **individual** (personas) y **hogar** (hogares).
- Variables clave típicas: `CH04` (sexo), `CH06` (edad), `ESTADO` (condición de
  actividad), `CAT_OCUP` (categoría ocupacional), `ITF`/`IPCF` (ingresos del hogar/per
  cápita), `NIVEL_ED` (nivel educativo), ponderadores `PONDERA`/`PONDIH`.
- Hay que usar los ponderadores (`PONDERA`, `PONDIH`, `PONDII`) para cualquier
  estadística representativa a nivel poblacional.
- Los `.txt` del INDEC están separados por `;` y en encoding `latin1`.
