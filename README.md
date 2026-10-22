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
├── notebooks/                 # Notebooks de análisis (Colab): 00-08
├── data/
│   ├── raw/                   # Zips del INDEC (ignorado por git; probar_06_local --descargar)
│   ├── processed/             # Parquets y salidas locales (ignorado por git)
│   ├── ipc_nacional.csv       # Respaldo del IPC nacional (06)
│   ├── series_nowcast.csv     # Respaldo de las series de datos.gob.ar del nowcast (07; IPC y haber mínimo del 08)
│   ├── bono_previsional.csv   # Bono previsional mensual, carga manual (07 y 08)
│   ├── canastas_regionales.csv # Respaldo de la CBA y la CBT por región (08)
│   └── pobreza_oficial.csv    # Respaldo de la pobreza publicada por el INDEC (08, validación)
├── src/
│   ├── data_loader.py         # Carga y compilación de las bases EPH
│   ├── nowcast.py             # Lógica del nowcast del termómetro (07)
│   └── jubilados.py           # Lógica del análisis de adultos mayores (08)
├── tools/                     # Generadores de los notebooks 06, 07 y 08 (gen_06/gen_07/gen_08), pruebas
│                              # locales (probar_06/07/08_local) y validación del 08 (comparar_zip_08)
├── docs/
│   ├── TECNICO.md             # Documentación técnica
│   ├── NOWCAST.md             # Rutina del nowcast: cuándo correrlo, qué mantener, qué revisar
│   └── JUBILADOS.md           # Rutina del 08: correrlo, validarlo, mantenerlo y leer sus resultados
└── .claude/                   # Memoria/contexto del proyecto para sesiones de Claude Code
```

## Notebooks

El notebook **00** es el punto de partida: **compila** las bases (une individuos+hogares
de todos los trimestres) y genera los datasets procesados en `data/processed/`. El resto
de los notebooks (01-08) **parten de esos datasets** ya compilados, en lugar de descargar
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
| `07_nowcast.ipynb` | **Nowcast del termómetro**: proyecta las cuatro dimensiones antes de que salga la EPH (D por microsimulación sobre la última base con salarios, haberes, AUH e IPC; A, B y C con ecuaciones puente sobre EMAE, empleo registrado SIPA y confianza del consumidor), backtest en pseudo tiempo real y registro de versiones que mide el error cuando llega la EPH oficial | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/07_nowcast.ipynb) |
| `08_jubilados.ipynb` | **Adultos mayores y jubilados** (varones 65+, mujeres 60+): cuántos son, con quién viven (si viven con sus hijos o los hijos con ellos, quién sostiene a quién), cobertura previsional, tipo de beneficio y haber en mínimas, ingresos, pobreza e indigencia (metodología INDEC), trabajo, vivienda, estrategias del hogar, salud, educación y estado civil; por región y aglomerado con IC, evolución 2017-2026 y salidas en Excel/CSV/PNG/ZIP | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/analisis_EPH/blob/main/notebooks/08_jubilados.ipynb) |

**Cobertura actual:** 37 trimestres, **T1-2017 → T1-2026** (00-06 validados en Colab; el 07
validado en Colab salvo su sección de robustez y el gráfico de evolución, agregados el 2026-10-21;
el 08, creado el 2026-10-22, validado en Colab: idéntico a la corrida local con datos reales).

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

Los notebooks 01-08 leen los datos con `load_panel(columns=..., quarters=...)`, pidiendo
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
4. Recién después re-correr los notebooks 01-06 (toman el último trimestre solos), el 07, que
   completa el error de las proyecciones de ese trimestre en el registro de versiones, y el 08 (su
   foto pasa sola a los últimos 4 trimestres; ver [`docs/JUBILADOS.md`](docs/JUBILADOS.md) §4).
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

## Nowcast del termómetro (notebook 07)

La EPH sale ~85 días después de cada trimestre. El 07 **proyecta el termómetro** antes de esa
fecha, indicador por indicador, y los pasa por la misma normalización del 06:

- **D (ingresos reales):** microsimulación sobre los microdatos de la última EPH, actualizando el
  ingreso de cada persona con índices mensuales que se publican antes (índice de salarios del
  INDEC por sector, haber mínimo y bono, AUH, IPC).
- **A, B y C (empleo, calidad del empleo, estrés de los hogares):** ecuaciones puente: cada
  indicador cambia en proporción al cambio del EMAE, de los asalariados registrados del SIPA y de la
  confianza del consumidor de la UTDT (bienes durables), que sale en el mismo mes.

Cuando sale la EPH, el trimestre pasa a oficial y cada versión guardada en el **registro de
versiones** (`carga_EPH/resultados/nowcast/registro_versiones.csv`, en Drive) recibe su error.

**Qué muestra el notebook:** series usadas y su último dato; control contra el 06; qué movió la
proyección; backtest en pseudo tiempo real; el nowcast de cada trimestre sin EPH con su intervalo
y la comparación interanual; robustez; registro de versiones. **Gráficos** (en
`nowcast/graficos/`): evolución del termómetro con la proyección (`nowcast_05_evolucion`), el
nowcast por dimensión (`nowcast_03_hoy`), error según la fecha de la proyección
(`nowcast_01_error_por_horizonte`), backtest (`nowcast_02_backtest`) y versiones de cada trimestre
(`nowcast_04_versiones`).

**Backtest (2019-2026, sin pandemia, RMSE):** con la EPH del trimestre anterior, el termómetro
proyectado erra 4,1 pts contra 7,2 de repetir el último publicado (el ruido muestral de la EPH es
~3,6); si la EPH se demora uno o dos trimestres, 7-9 contra 12-15. Por dimensión, la ganancia
está en D (9,5 vs 14,8) y en A; B y C casi no se pueden anticipar. Parte de la mejora del
termómetro a un trimestre viene de errores de B que compensan los de A y C, así que lo esperable
es algo peor (entre 4,1 y 5,5).

La **sección 7** del notebook chequea en cada corrida la robustez de ese resultado: subperíodos
(la ventaja se sostiene en 2019-2022 y 2023-2026, mucho más en el segundo), sesgo (no
significativo), cobertura de los intervalos (84-96%), convergencia de las versiones (el error baja
de 7,1 a 4,1 a medida que llegan datos) y dependencia de cada predictor (sin el SIPA el error sube
~50%: es la serie clave). La lectura queda en `nowcast/robustez_termometro.md`.

**Nowcast al 21/10/2026** (base 2026T1 = 52,8; el T2-2026 todavía no estaba publicado):
2026T2 = 62,8 (IC 95% 54-71), 2026T3 = 58,6 (45-72), 2026T4 = 54,1 (37-71). La suba contra el T1
es sobre todo estacional; contra el mismo trimestre de 2025: +12,0, +12,5 y +4,6 pts.

Generado con `python tools/gen_07_nowcast.py`; prueba local `python tools/probar_07_local.py`
(después del 06; ~5 min). Rutina (cuándo correrlo, mantenimiento mensual del bono previsional, qué
revisar, qué hacer cuando sale una EPH): [`docs/NOWCAST.md`](docs/NOWCAST.md). Detalle técnico:
[`docs/TECNICO.md`](docs/TECNICO.md) §7.

## Adultos mayores y jubilados (notebook 08)

Cómo viven los **adultos mayores** (varones de 65 años o más y mujeres de 60 o más, las edades
jubilatorias) y cómo se relaciona con cobrar o no una jubilación. La foto junta los **últimos 4
trimestres** (más muestra y sin la estacionalidad del aguinaldo); la evolución va de 2017 a hoy.
Todos los indicadores tienen **intervalo de confianza del 95%** (bootstrap por vivienda, como el 06)
y se marcan las estimaciones poco precisas (criterio del INDEC para el coeficiente de variación).

**Cómo se mide:** *cobra jubilación o pensión* = declara un monto (`V2_M`; desde 2023T4 separado en
por aportes, moratoria y otras pensiones), con el ponderador de ingresos `PONDII`; `CAT_INAC` no
sirve (cambió de códigos en 2023T4 y no viene en 2026T1). *Con quién viven* sale del parentesco de
todos los integrantes del hogar: distingue si **los hijos viven en el hogar del adulto mayor** (es
jefe/a o cónyuge) o **el adulto mayor vive en el hogar de un hijo/a**, y qué parte del ingreso del
hogar aportan los adultos mayores. **Pobreza e indigencia** con la metodología del INDEC (adulto
equivalente y canasta de la región): la réplica coincide con la tasa oficial con un error medio de
0,1 pp (2017S1-2025S2). Ingresos en pesos constantes y en haberes mínimos.

**Resultados (T2-2025 a T1-2026, 31 aglomerados urbanos):**

- **4,44 millones** de adultos mayores (14,8% de la población; 66% mujeres); un tercio de los hogares
  tiene al menos uno.
- **Con quién viven:** 22% solos, 30% solo con su pareja, **40% con al menos un hijo/a**: en el 33%
  los hijos viven en el hogar del adulto mayor y en el 7% el adulto mayor vive en el hogar de un hijo
  (19% entre los de 85 y más). Los hijos que viven con ellos son en su mayoría adultos (69% tiene 30
  años o más) y el 65% trabaja; aun así, en el 55% de esos hogares los adultos mayores aportan más de
  la mitad del ingreso (28% cuando el adulto mayor vive en el hogar del hijo).
- **Jubilación:** cobra el **88,8%** (mujeres de 60 a 64: 69,5%; de 75 en adelante: 96%). Por aportes
  56,5%, moratoria 24,2%, otras pensiones 3,5% y más de un beneficio 4,5%. El 39% de los que cobran declara
  la mínima (con o sin bono) y el 17% menos (probablemente por descuentos de moratoria y créditos, o
  por cobrar la PUAM). El haber
  mediano real de los últimos 4 trimestres está un 33% debajo del de 2017 y un 14% debajo del de 2023.
- **Pobreza:** **11,6%** de los adultos mayores (indigencia 1,7%), contra 28% de los adultos y 43% de
  los menores de 18; 21,5% entre los que no cobran jubilación y 32% entre los que viven con hijos y
  nietos. Solo el 13% está en los tres deciles de ingreso más pobres. En 2024 la pobreza de los
  adultos mayores llegó a 23% (7% en 2017).
- **Trabajo:** el 20% trabaja (59% de los que no cobran) y el 55% de los ocupados es informal.
- **Vivienda:** 87% son propietarios; hacinamiento 2% (13% en el resto).

**Cuidados al leerlos:** la pobreza de los adultos mayores sale baja en parte por la metodología
(menos adultos equivalentes y 87% de propietarios) y el 23% está apenas arriba de la línea (de 1 a
1,5 líneas); la cobertura es un piso (subdeclaración); la EPH solo ve a los hijos que viven en el
mismo hogar y no cubre zonas rurales ni geriátricos. Detalle y mejoras pendientes en
[`docs/JUBILADOS.md`](docs/JUBILADOS.md) §7-9.

**Salidas** (en Drive, `carga_EPH/resultados/jubilados/`): `jubilados_EPH.xlsx` (hoja Índice + 38
tablas; las estimaciones con valor, IC, casos y calidad), `tablas/*.csv` (`;` y coma decimal), 20 gráficos en
`graficos/`, `jubilados_EPH_resumen.md` (lectura automática) y `jubilados_EPH.zip` con todo, que en
Colab se descarga al final. Generado con `python tools/gen_08_jubilados.py`; prueba local
`python tools/probar_08_local.py` (~3 min); validación contra Colab
`python -X utf8 tools/comparar_zip_08.py <ruta al ZIP>` (validado el 2026-10-22: idéntico). Rutina
(qué revisar, qué hacer cuando sale una EPH, mantenimiento):
[`docs/JUBILADOS.md`](docs/JUBILADOS.md). Detalle técnico: [`docs/TECNICO.md`](docs/TECNICO.md) §8.

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
   `.claude/memoria.md` (estado/pendientes, empezando por el HANDOFF), `docs/TECNICO.md`,
   `docs/NOWCAST.md`, `docs/JUBILADOS.md` y `.claude/memoria_EPH.md`.
4. Para ejecutar: abrir cualquier notebook con su badge de Colab (usa la cuenta de Google
   que tiene la carpeta `carga_EPH`). Los cambios de código deben estar pusheados a
   `main` para que Colab los vea. Todo el estado que no está en el repo vive en Drive: los zips
   y parquets (`carga_EPH/`, `carga_EPH/processed/`) y las salidas (`carga_EPH/resultados/`,
   `carga_EPH/resultados/nowcast/` y `carga_EPH/resultados/jubilados/`, incluido el registro de
   versiones del nowcast, que no se puede regenerar; el resto se regenera corriendo los notebooks).

### Setup local (opcional)

```bash
pip install -r requirements.txt
```

Para correr localmente, poner los `.zip` del INDEC en `data/raw/` (no se versionan).
`python tools/probar_06_local.py --descargar` los baja del sitio del INDEC, compila los
parquets en `data/processed/` (ignorado por git) y corre el notebook 06 completo;
`python tools/probar_07_local.py` hace lo mismo con el 07 (nowcast) y
`python tools/probar_08_local.py` con el 08 (adultos mayores).

## Documentación técnica

Ver [`docs/TECNICO.md`](docs/TECNICO.md): flujo de datos, funciones de
`src/data_loader.py`, esquemas por trimestre, gotchas resueltos, convenciones de análisis y el
detalle de los notebooks 06 (termómetro), 07 (nowcast, `src/nowcast.py`) y 08 (adultos mayores,
`src/jubilados.py`). Las rutinas de uso y mantenimiento están en [`docs/NOWCAST.md`](docs/NOWCAST.md)
(07) y [`docs/JUBILADOS.md`](docs/JUBILADOS.md) (08).

## Diccionario de datos

Ver [`.claude/memoria_EPH.md`](.claude/memoria_EPH.md) para el **diccionario completo de
variables** de las bases hogar y personas (significado y valores de cada campo), el
mapa de claves de vínculo, los ponderadores y el **quiebre de esquema de 4T2023**.

## Memoria de proyecto

Ver [`.claude/memoria.md`](.claude/memoria.md) para el estado del proyecto, decisiones
de arquitectura y próximos pasos (usado para continuidad entre sesiones de Claude Code).
