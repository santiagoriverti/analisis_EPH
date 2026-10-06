"""Genera notebooks/06_termometro.ipynb.

El notebook 06 NO se edita a mano: se edita este script y se regenera.

Uso (desde la raíz del repo):
    python tools/gen_06_termometro.py                 # escribe notebooks/06_termometro.ipynb
    python tools/gen_06_termometro.py otra/ruta.ipynb

Cada llamada a md()/code() agrega una celda en orden. Ver docs/TECNICO.md §6.
"""
import json
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "notebooks", "06_termometro.ipynb")

cells = []


def md(s):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)})


def code(s):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": s.strip("\n").splitlines(keepends=True)})


md(r"""
# 06 - Termómetro de la economía de los hogares (EPH)

Índice compuesto trimestral que resume **cómo le está yendo a los hogares** según la EPH.
Funciona como un termómetro de **malestar**: **0 = mejor trimestre de la serie, 100 = peor**
(más "fiebre"). Se construye con los parquets por trimestre compilados por el notebook
**00_preparacion_bases** y con el IPC nacional del INDEC (para llevar los ingresos a pesos
constantes).

**Cuatro dimensiones:**

| Dimensión | Indicador | Variables EPH | Base |
|---|---|---|---|
| **A. Cantidad de empleo** | Desocupación | `ESTADO` | % PEA |
| | Tasa de empleo (invertida) | `ESTADO` | % población |
| | Desocupación de larga duración (>1 año buscando) | `ESTADO==2` & `PP10A==5` | % PEA |
| | Desocupados por despido/cierre o renuncia obligada/pactada (ex asalariados) | `ESTADO==2` & `PP11O∈{1,7}` | % PEA |
| **B. Calidad del empleo** | Subocupación horaria | `INTENSI==1` | % PEA |
| | Ocupados demandantes de otro empleo | `ESTADO==1` & `PP03J==1` | % PEA |
| | Personas sin cobertura de salud (ni obra social, ni prepaga, ni plan estatal) | `CH08==4` | % población |
| | Tasa de empleo asalariado registrado (invertida) | `CAT_OCUP==3` & `PP07H==1` | % población |
| **C. Estrés de los hogares** (últimos 3 meses) | Gastaron ahorros | `V13==1` | % hogares |
| | Pidieron préstamos a familiares/amigos | `V14==1` | % hogares |
| | Vendieron pertenencias | `V17==1` | % hogares |
| | Recibieron mercadería/alimentos del gobierno, iglesias, escuelas | `V6==1` | % hogares |
| | Recibieron mercadería/alimentos de familiares/vecinos | `V7==1` | % hogares |
| **D. Ingresos reales** | Ingreso real de la ocupación principal (invertido) | `P21` / IPC | ocupados con ingreso |
| | Personas con ingreso per cápita familiar real bajo | `IPCF` / IPC < umbral fijo | % población |

**Metodología:**
1. Cada indicador se calcula por trimestre con su ponderador: `PONDERA` en general;
   `PONDIIO` (ingreso de la ocupación) y `PONDIH` (ingreso familiar) en D, que corrigen la no
   respuesta de ingresos. Los indicadores de hogares usan un registro por hogar (jefe/a `CH03==1`).
2. **Ingresos reales:** se deflactan con el IPC nacional (dic-2016 = 100) promedio de los meses
   de referencia, que en la EPH son el **mes anterior a la entrevista** (el T1 usa diciembre,
   enero y febrero). El ingreso laboral se resume con la **media geométrica** (menos sensible a
   valores extremos que el promedio). El umbral de ingreso bajo es fijo en pesos constantes:
   **60% de la mediana del ingreso per cápita familiar real de 2017-2019** (queda en niveles
   cercanos a la línea de pobreza de un hogar tipo). Los dos indicadores de ingresos se
   **desestacionalizan** antes de normalizar, porque los meses de referencia del T1 y el T3
   incluyen aguinaldo.
3. Se orienta para que "más alto = peor" (las tasas de empleo y el ingreso se invierten) y se
   normaliza como **percentil dentro de su propia historia** 2017-hoy (0 = mejor valor observado,
   100 = peor). Percentiles en lugar de min-max para que un outlier (2020T2) no aplaste el resto
   de la serie. Antes de rankear se redondea a 1 decimal.
4. Dimensión = promedio de sus indicadores; **Termómetro = promedio simple de las 4
   dimensiones** (cada dimensión pesa 1/4).
5. Franjas: **Templado** (≤ 33), **Tibio** (≤ 66), **Fiebre** (> 66).
6. **Incertidumbre:** la EPH es una muestra (~16.000 hogares por trimestre). Con réplicas
   bootstrap (remuestreo de viviendas) se calcula un **intervalo de confianza del 95%** para el
   nivel, la variación interanual y la media móvil (sección 5).

**Cómo leerlo:** el valor es *relativo a la historia disponible* (2017-hoy): 60 significa
"peor que el 60% de los trimestres observados", no un nivel absoluto. Las variaciones
interanuales de menos de ~10 puntos suelen ser **ruido muestral**: mirar su intervalo de
confianza y la **media móvil de 4 trimestres** (tiene la mitad de ruido). Al sumar trimestres
los valores pasados se mueven un poco (los percentiles se recalculan): el último trimestre es
provisorio. Hay estacionalidad en el empleo y el estrés (el T1 suele ser peor), por eso se
compara contra el mismo trimestre del año anterior.

**Quedan fuera del índice (se muestran como complementarios):**
- Asalariados sin descuento jubilatorio (`PP07H==2`, % asalariados): salió en la v4. Se calcula
  sobre los ocupados y **mejora en las crisis** por efecto composición (35,8% → 23,8% en
  2020T2). La precarización la siguen captando los asalariados registrados y la falta de
  cobertura de salud, ambos sobre población.
- Ingreso per cápita familiar real (media geométrica): redundante con personas con ingreso bajo
  (correlación 0,98).
- Préstamos bancarios (`V15`) y compras en cuotas/fiado (`V16`): suben tanto por estrés como
  por mayor acceso al crédito (señal ambigua).
- Informalidad `EMPLEO`: solo existe desde 2023T4.
- Pluriempleo (`PP03C==2`): procíclico (cae en la pandemia y en cada T1).
- Desalentados (`PP02E==3`) y niños <10 que aportan dinero (`V19_A/B`): niveles de 0,0-0,4%,
  donde la diferencia entre trimestres es ruido muestral.

**Efecto composición:** en 2020T2 se perdieron sobre todo empleos informales, de pocas horas y
de bajos ingresos, así que los indicadores calculados *sobre los ocupados* **mejoraron**
artificialmente (incluido el ingreso laboral real). Por eso cada dimensión afectada tiene al
menos un indicador sobre toda la población: asalariados registrados y cobertura de salud en B,
personas con ingreso bajo en D.

**Alcance y advertencias:** el IPC se baja de la API de Series de Tiempo (datos.gob.ar); si no
responde, se usa la copia `data/ipc_nacional.csv` del repo. Los intervalos de confianza son
aproximados: la base pública no trae las áreas ni los estratos del diseño muestral, así que
probablemente sean algo más angostos que los reales. La EPH cubre 31 aglomerados urbanos y se
publica ~3 meses después del trimestre; 2020T2-T3 se relevó telefónicamente (pandemia).

**Contenido:** 1-5 preparación (setup, carga, indicadores con réplicas bootstrap,
normalización, incertidumbre) · 6-7 el termómetro hoy (gráfico y lectura automática) · 8-10
evolución (índice, dimensiones, mapa de calor) · 11 tabla del último trimestre · 12 promedios
anuales · 13 controles de calidad · 14 exportar · Anexo A diagnóstico de candidatas · Anexo B
historial de versiones.

*Versión del índice: v4 (2026-10).*
""")

md("## 1. Setup (Colab)")

code(r'''
import sys, os, shutil, glob

REPO_URL = "https://github.com/santiagoriverti/analisis_EPH.git"
REPO_DIR = "/content/analisis_EPH"

if os.path.exists(REPO_DIR):
    !git -C {REPO_DIR} pull -q
else:
    !git clone -q {REPO_URL} {REPO_DIR}

%cd {REPO_DIR}
sys.path.insert(0, REPO_DIR)

from google.colab import drive
drive.mount('/content/drive')

# Copia única Drive -> disco local (leer muchos parquets por FUSE desconecta el mount).
DRIVE_PROCESSED = "/content/drive/MyDrive/carga_EPH/processed"
PROCESSED_DIR = "/content/processed_local"
os.makedirs(PROCESSED_DIR, exist_ok=True)

for src in glob.glob(os.path.join(DRIVE_PROCESSED, "eph_T*.parquet")):
    dst = os.path.join(PROCESSED_DIR, os.path.basename(src))
    if not os.path.exists(dst):
        shutil.copy(src, dst)

n = len(glob.glob(os.path.join(PROCESSED_DIR, "eph_T*.parquet")))
print(f"Parquets locales listos en {PROCESSED_DIR}: {n} trimestres")

# Carpeta de Drive donde se guarda la tabla del termómetro (CSV)
RESULTADOS_DIR = "/content/drive/MyDrive/carga_EPH/resultados"
''')

code(r'''
import io
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from src.data_loader import load_panel, list_available_quarters, _period_tag

plt.rcParams.update({
    "figure.figsize": (11, 5.5),
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e4e3df",
    "grid.linewidth": 0.8,
    "axes.edgecolor": "#8a8984",
    "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e",
    "ytick.color": "#52514e",
})

# Paleta categórica (validada para daltonismo, orden fijo): una por dimensión + tinta para el índice.
COLOR_DIM = {"A. Cantidad de empleo": "#2a78d6",
             "B. Calidad del empleo": "#eb6834",
             "C. Estrés de los hogares": "#1baf7a",
             "D. Ingresos reales": "#eda100"}
TINTA = "#0b0b0b"
# Franjas del termómetro (colores de estado, siempre acompañados de etiqueta)
FRANJAS = [(0, 33, "#0ca30c", "Templado"), (33, 66, "#fab219", "Tibio"),
           (66, 100, "#d03b3b", "Fiebre")]

quarters = list_available_quarters()
ULTIMO = quarters[-1]
print("Trimestres disponibles:", len(quarters), "| último:", _period_tag(*ULTIMO))
''')

md("""
## 2. Carga de datos

Personas (mercado laboral, cobertura de salud e ingresos) y hogares (estrategias del hogar, un
registro por hogar). Todas las columnas salvo `CODUSU` se fuerzan a numéricas (ver gotcha de
dtypes en `docs/TECNICO.md`). Después se carga el IPC para deflactar los ingresos.
""")

code(r'''
PERS_COLS = ["CODUSU", "ESTADO", "INTENSI", "PP10A", "PP02E", "PP03J", "PP07H", "CAT_OCUP", "EMPLEO",
             "PP11O", "PP03C", "CH08", "P21", "PONDIIO", "IPCF", "PONDIH", "PONDERA"]
HOG_COLS = ["CODUSU", "CH03", "V6", "V7", "V13", "V14", "V15", "V16", "V17", "V19_A", "V19_B", "PONDERA"]

def cargar(cols):
    df = load_panel(columns=cols, out_dir=PROCESSED_DIR)
    for c in cols:
        if c == "CODUSU":
            df[c] = df[c].astype(str).str.strip()  # identificador de vivienda (para el bootstrap)
        elif c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = np.nan  # columna inexistente en todos los trimestres
    return df

pers = cargar(PERS_COLS)
hog = cargar(HOG_COLS)
hog = hog[hog["CH03"] == 1].drop(columns="CH03")
print(f"Personas: {len(pers):,} filas | Hogares: {len(hog):,} filas")
''')

code(r'''
IPC_ID = "148.3_INIVELNAL_DICI_M_26"  # IPC nacional, nivel general, dic-2016 = 100 (INDEC)
IPC_CSV = os.path.join(REPO_DIR, "data", "ipc_nacional.csv")  # copia de respaldo en el repo

def cargar_ipc():
    """IPC mensual desde la API de Series de Tiempo; si falla, desde la copia del repo."""
    try:
        r = requests.get("https://apis.datos.gob.ar/series/api/series/",
                         params={"ids": IPC_ID, "format": "csv", "limit": 5000}, timeout=30)
        r.raise_for_status()
        m, fuente = pd.read_csv(io.StringIO(r.text)), "API datos.gob.ar"
    except Exception as e:
        m, fuente = pd.read_csv(IPC_CSV), f"copia del repo (la API falló: {type(e).__name__})"
    return m.set_index(pd.to_datetime(m.iloc[:, 0])).iloc[:, 1], fuente

ipc_m, fuente_ipc = cargar_ipc()
# Los ingresos de la EPH son del mes anterior a la entrevista: el T1 usa diciembre, enero y febrero.
ref = ipc_m.shift(1, freq="MS")
g = ref.groupby([ref.index.year, ref.index.quarter])
ipc_q = (g.mean() / 100)[g.count() == 3]
IPC_Q = {a * 10 + t: v for (a, t), v in ipc_q.items()}  # clave ANIO*10 + TRIMESTRE

pers["IPC_Q"] = (pers["ANIO"] * 10 + pers["TRIMESTRE"]).map(IPC_Q)
pers["P21_REAL"] = pers["P21"] / pers["IPC_Q"]
pers["IPCF_REAL"] = pers["IPCF"] / pers["IPC_Q"]
SIN_IPC = sorted({f"{a}T{t}" for a, t in pers.loc[pers["IPC_Q"].isna(), ["ANIO", "TRIMESTRE"]].drop_duplicates().values})
print(f"IPC: {fuente_ipc}; último mes disponible {ipc_m.index[-1]:%Y-%m}")
if SIN_IPC:
    print("⚠ Falta IPC para", ", ".join(SIN_IPC), "-> la dimensión D queda vacía en esos trimestres")
''')

md("""
## 3. Indicadores por trimestre (con réplicas bootstrap)

Cada indicador se define una sola vez, como **numerador / denominador** (sumas ponderadas por
fila), en el diccionario `INDICADORES`. El ingreso laboral es una media geométrica: su numerador
es el logaritmo del ingreso real.

En el mismo paso se generan las **réplicas bootstrap** para medir la incertidumbre (sección 5):
cada vivienda (`CODUSU`) recibe un peso aleatorio (Poisson de media 1), el mismo en todos los
trimestres en que aparece, para respetar el panel rotativo de la EPH (que repite viviendas entre
trimestres y entre años).

Unidades: % salvo los ingresos medios, en pesos de dic-2016 por mes.
""")

code(r'''
B_BOOT = 200        # réplicas bootstrap (alcanzan para intervalos del 95%)
SEMILLA = 20261006  # fija: la corrida es reproducible

def mediana_ponderada(v, w):
    s = np.argsort(np.asarray(v))
    v, w = np.asarray(v)[s], np.asarray(w)[s]
    return np.interp(0.5, (np.cumsum(w) - 0.5 * w) / w.sum(), v)

# Umbral de ingreso bajo, fijo en pesos de dic-2016: 60% de la mediana del IPCF real 2017-2019
base_umbral = pers[pers["ANIO"].between(2017, 2019) & (pers["PONDIH"] > 0)]
UMBRAL_INGRESO = 0.6 * mediana_ponderada(base_umbral["IPCF_REAL"], base_umbral["PONDIH"])
del base_umbral

def pea(g): return g["ESTADO"].isin([1, 2])
def ocup(g): return g["ESTADO"] == 1
def desoc(g): return g["ESTADO"] == 2
def asal(g): return ocup(g) & (g["CAT_OCUP"] == 3)
def todos(g): return pd.Series(True, index=g.index)
def con_ingreso(g): return ocup(g) & (g["P21"] > 0)
def log_real(x, cond): return np.log(x.where(cond, 1.0))  # fuera del universo: log(1) = 0
CH08_VALIDOS = [1, 2, 3, 4, 12, 13, 23, 123]  # 9 = Ns/Nr queda afuera

# nombre -> (base "p" personas / "h" hogares, ponderador, función -> (numerador, denominador), tipo)
#   tipo "pct": numerador/denominador en %; "geo": media geométrica (exp del promedio de logs)
INDICADORES = {
    # A. Cantidad de empleo
    "Desocupación": ("p", "PONDERA", lambda g: (desoc(g), pea(g)), "pct"),
    "Tasa de empleo": ("p", "PONDERA", lambda g: (ocup(g), todos(g)), "pct"),
    "Desocupación >1 año": ("p", "PONDERA", lambda g: (desoc(g) & (g["PP10A"] == 5), pea(g)), "pct"),
    # PP11O: 1 despido/cierre, 7 renuncia obligada/pactada
    "Desocupados por despido (incl. renuncia forzada)": ("p", "PONDERA", lambda g: (desoc(g) & g["PP11O"].isin([1, 7]), pea(g)), "pct"),
    # B. Calidad del empleo
    "Subocupación": ("p", "PONDERA", lambda g: (g["INTENSI"] == 1, pea(g)), "pct"),
    "Ocupados que buscan otro empleo": ("p", "PONDERA", lambda g: (ocup(g) & (g["PP03J"] == 1), pea(g)), "pct"),
    "Sin cobertura de salud": ("p", "PONDERA", lambda g: (g["CH08"] == 4, g["CH08"].isin(CH08_VALIDOS)), "pct"),
    "Tasa de empleo asalariado registrado": ("p", "PONDERA", lambda g: (asal(g) & (g["PP07H"] == 1), todos(g)), "pct"),
    # C. Estrés de los hogares
    "Gastaron ahorros": ("h", "PONDERA", lambda g: (g["V13"] == 1, todos(g)), "pct"),
    "Préstamos de familiares/amigos": ("h", "PONDERA", lambda g: (g["V14"] == 1, todos(g)), "pct"),
    "Vendieron pertenencias": ("h", "PONDERA", lambda g: (g["V17"] == 1, todos(g)), "pct"),
    "Alimentos de gobierno/instituciones": ("h", "PONDERA", lambda g: (g["V6"] == 1, todos(g)), "pct"),
    "Alimentos de familiares/vecinos": ("h", "PONDERA", lambda g: (g["V7"] == 1, todos(g)), "pct"),
    # D. Ingresos reales
    "Ingreso laboral real": ("p", "PONDIIO", lambda g: (log_real(g["P21_REAL"], con_ingreso(g)), con_ingreso(g)), "geo"),
    "Personas con ingreso per cápita real bajo": ("p", "PONDIH", lambda g: (g["IPCF_REAL"] < UMBRAL_INGRESO, g["IPCF"] >= 0), "pct"),
    # complementarios (fuera del índice)
    "Asalariados sin descuento jubilatorio": ("p", "PONDERA", lambda g: (asal(g) & (g["PP07H"] == 2), asal(g)), "pct"),
    "Ingreso per cápita familiar real": ("p", "PONDIH", lambda g: (log_real(g["IPCF_REAL"], g["IPCF"] > 0), g["IPCF"] > 0), "geo"),
    "Informalidad (EMPLEO)": ("p", "PONDERA", lambda g: (ocup(g) & (g["EMPLEO"] == 2), ocup(g) & g["EMPLEO"].notna()), "pct"),  # solo desde 2023T4
    "Pluriempleo": ("p", "PONDERA", lambda g: (ocup(g) & (g["PP03C"] == 2), ocup(g)), "pct"),
    "Desalentados": ("p", "PONDERA", lambda g: ((g["ESTADO"] == 3) & (g["PP02E"] == 3), pea(g)), "pct"),
    "Préstamos de bancos/financieras": ("h", "PONDERA", lambda g: (g["V15"] == 1, todos(g)), "pct"),
    "Compras en cuotas/fiado": ("h", "PONDERA", lambda g: (g["V16"] == 1, todos(g)), "pct"),
    "Niños <10 aportan dinero": ("h", "PONDERA", lambda g: ((g["V19_A"] == 1) | (g["V19_B"] == 1), todos(g)), "pct"),
}
INGRESOS = ["Ingreso laboral real", "Personas con ingreso per cápita real bajo", "Ingreso per cápita familiar real"]
NOMBRES = list(INDICADORES)
UNIDAD = {c: "$" if INDICADORES[c][3] == "geo" else "%" for c in NOMBRES}

trims = sorted(pers.groupby(["ANIO", "TRIMESTRE"]).groups)
viviendas = pd.Index(pers["CODUSU"].unique())
R = np.random.default_rng(SEMILLA).poisson(1.0, size=(B_BOOT, len(viviendas))).astype(np.uint8)
punto = np.full((len(trims), len(NOMBRES)), np.nan)
ind_boot = np.full((B_BOOT, len(trims), len(NOMBRES)), np.nan)
grupos = {"p": pers.groupby(["ANIO", "TRIMESTRE"]), "h": hog.groupby(["ANIO", "TRIMESTRE"])}

for i, key in enumerate(trims):
    for b_ in ("p", "h"):
        g = grupos[b_].get_group(key)
        ks = [k for k, n in enumerate(NOMBRES) if INDICADORES[n][0] == b_]
        num, den = {}, {}
        for k in ks:
            _, peso, f, _ = INDICADORES[NOMBRES[k]]
            nu, de = f(g)
            w = g[peso].fillna(0).to_numpy(dtype=float)
            num[k] = w * np.nan_to_num(np.asarray(nu, dtype=float))
            den[k] = w * np.asarray(de, dtype=float)
        # sumas por vivienda: el bootstrap pondera viviendas enteras
        N = pd.DataFrame(num).groupby(g["CODUSU"].to_numpy()).sum()
        D = pd.DataFrame(den).groupby(g["CODUSU"].to_numpy()).sum()
        Rq = R[:, viviendas.get_indexer(N.index)].astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            pt = N.sum().to_numpy() / D.sum().to_numpy()
            bt = (Rq @ N.to_numpy()) / (Rq @ D.to_numpy())
        geo = np.array([INDICADORES[NOMBRES[k]][3] == "geo" for k in ks])
        punto[i, ks] = np.where(geo, np.exp(pt), pt * 100)
        ind_boot[:, i, ks] = np.where(geo, np.exp(bt), bt * 100)

etiquetas = [f"{a}T{t}" for a, t in trims]
ind = pd.DataFrame(punto, index=etiquetas, columns=NOMBRES)
if SIN_IPC:  # sin deflactor no hay ingresos reales
    ind.loc[SIN_IPC, INGRESOS] = np.nan
    ind_boot[np.ix_(range(B_BOOT), [etiquetas.index(q) for q in SIN_IPC], [NOMBRES.index(c) for c in INGRESOS])] = np.nan
print(f"Umbral de ingreso bajo: ${UMBRAL_INGRESO:,.0f} por persona de dic-2016".replace(",", ".")
      + (f" (≈ ${UMBRAL_INGRESO * IPC_Q[trims[-1][0] * 10 + trims[-1][1]]:,.0f} del último trimestre)".replace(",", ".")
         if trims[-1][0] * 10 + trims[-1][1] in IPC_Q else ""))
print(f"Réplicas bootstrap: {B_BOOT} | viviendas distintas en la serie: {len(viviendas):,}".replace(",", "."))
ind.round(1)
''')

md("""
## 4. Normalización y armado del termómetro

Cada indicador se convierte en su **percentil histórico orientado** (0 = mejor trimestre
de la serie, 100 = peor). Los indicadores de ingresos se desestacionalizan antes (aguinaldo).
""")

code(r'''
DIMENSIONES = {
    "A. Cantidad de empleo": {"Desocupación": +1, "Tasa de empleo": -1,
                              "Desocupación >1 año": +1, "Desocupados por despido (incl. renuncia forzada)": +1},
    "B. Calidad del empleo": {"Subocupación": +1, "Ocupados que buscan otro empleo": +1,
                              "Sin cobertura de salud": +1,
                              "Tasa de empleo asalariado registrado": -1},
    "C. Estrés de los hogares": {"Gastaron ahorros": +1, "Préstamos de familiares/amigos": +1,
                                 "Vendieron pertenencias": +1,
                                 "Alimentos de gobierno/instituciones": +1,
                                 "Alimentos de familiares/vecinos": +1},
    "D. Ingresos reales": {"Ingreso laboral real": -1, "Personas con ingreso per cápita real bajo": +1},
}
COMPLEMENTARIOS = ["Asalariados sin descuento jubilatorio", "Ingreso per cápita familiar real",
                   "Informalidad (EMPLEO)", "Préstamos de bancos/financieras", "Compras en cuotas/fiado",
                   "Desalentados", "Niños <10 aportan dinero", "Pluriempleo"]
# Se desestacionalizan antes de normalizar: los meses de referencia del T1 y el T3 incluyen aguinaldo
DESESTACIONALIZAR = ["Ingreso laboral real", "Personas con ingreso per cápita real bajo"]
SIGNO = {c: s for cols in DIMENSIONES.values() for c, s in cols.items()}  # indicador -> signo
PANDEMIA = ["2020T2", "2020T3", "2020T4", "2021T1"]
VALLE = ["2023T3", "2023T4"]

def desestacionalizar(s):
    """Resta el factor estacional de cada trimestre del año (método clásico aditivo).

    Tendencia = media móvil centrada 2x4; factor = mediana del desvío respecto de la tendencia
    en cada trimestre del año (sin 2020T1-2021T2, distorsionados por la pandemia), centrado en 0.
    """
    tend = s.rolling(4, center=True).mean().rolling(2).mean().shift(-1)
    trim = s.index.str[-1]
    ok = ~s.index.isin(["2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2"])
    fac = (s - tend)[ok].groupby(trim[ok]).median()
    return s - (fac - fac.mean()).reindex(trim).to_numpy()

def serie_indice(c, datos=None):
    """Serie que entra al índice: la del indicador, desestacionalizada si corresponde."""
    s = (ind if datos is None else datos)[c]
    return desestacionalizar(s) if c in DESESTACIONALIZAR else s

def percentil_orientado(s, signo):
    """0 = mejor valor de la serie, 100 = peor.

    Se redondea a 1 decimal antes de rankear: diferencias menores a 0,1 pp son ruido
    muestral, y así los empates quedan en el percentil promedio en vez de en los extremos.
    """
    r = (signo * s.round(1)).rank(method="average")
    n = r.notna().sum()
    return (r - 1) / (n - 1) * 100 if n > 1 else r * np.nan

def armar_termometro(dimensiones, datos=None):
    """(percentiles por indicador, dimensiones, termómetro) para un set de indicadores.

    `datos` = DataFrame de indicadores (por defecto `ind`; las réplicas bootstrap usan el suyo).
    """
    norm = pd.DataFrame({c: percentil_orientado(serie_indice(c, datos), signo)
                         for dim in dimensiones.values() for c, signo in dim.items()})
    dims = pd.DataFrame({dim: norm[list(cols)].mean(axis=1) for dim, cols in dimensiones.items()})
    return norm, dims, dims.mean(axis=1)

norm, dims, t = armar_termometro(DIMENSIONES)
termo = dims.copy()
termo["Termómetro"] = t
termo["Media móvil 4T"] = termo["Termómetro"].rolling(4).mean()
termo["Var. interanual (pts)"] = termo["Termómetro"].diff(4)

def franja(v):
    if pd.isna(v):
        return "sin dato"
    for lo, hi, _, nombre in FRANJAS:
        if v <= hi:
            return nombre
    return FRANJAS[-1][3]

termo["Estado"] = termo["Termómetro"].map(franja)
termo.round(1)
''')

md("""
## 5. Incertidumbre muestral (bootstrap)

Se arma el termómetro completo (normalización por percentiles incluida) en cada réplica
bootstrap de la sección 3 y se resume:

- **IC 95%**: intervalo de confianza del 95% (percentiles 2,5 y 97,5 de las réplicas, centrado
  en el valor estimado).
- **P(sube)**: proporción de réplicas en que la variación interanual es positiva.
- Una variación es **significativa** si su intervalo no incluye el 0; si lo incluye, no se
  distingue del ruido muestral.

La media móvil de 4 trimestres promedia cuatro muestras distintas y tiene la mitad de ruido.
""")

code(r'''
reps_t, reps_d = [], []
for b in range(B_BOOT):
    _, d_b, t_b = armar_termometro(DIMENSIONES, pd.DataFrame(ind_boot[b], index=ind.index, columns=ind.columns))
    reps_t.append(t_b)
    reps_d.append(d_b)
boot_t = pd.DataFrame(reps_t).reset_index(drop=True)  # réplicas × trimestres
boot_d = {n: pd.DataFrame([d[n] for d in reps_d]).reset_index(drop=True) for n in DIMENSIONES}

def intervalo(rep, valor):
    """IC 95% percentil, centrado en el valor estimado (corrige el sesgo de las réplicas)."""
    if np.isnan(np.asarray(rep, dtype=float)).all():
        return np.nan, np.nan
    lo, hi = np.nanpercentile(rep, [2.5, 97.5])
    m = np.nanmean(rep)
    return valor - (m - lo), valor + (hi - m)

def resumen_incertidumbre(serie, reps):
    """Por trimestre: valor e IC; variación i.a., su IC y P(sube); media móvil 4T y su variación i.a."""
    mm, mm_b = serie.rolling(4).mean(), reps.T.rolling(4).mean().T
    filas = {}
    for i, q in enumerate(serie.index):
        f = {"Valor": serie[q]}
        f["IC inf"], f["IC sup"] = intervalo(reps[q], serie[q])
        if i >= 4:
            q4 = serie.index[i - 4]
            dv, db = serie[q] - serie[q4], reps[q] - reps[q4]
            f["Var. i.a."] = dv
            f["Var. i.a. IC inf"], f["Var. i.a. IC sup"] = intervalo(db, dv)
            f["P(sube)"] = (db > 0).mean()
        if i >= 3:
            f["MM4T"] = mm[q]
            f["MM4T IC inf"], f["MM4T IC sup"] = intervalo(mm_b[q], mm[q])
        if i >= 7:
            q4 = serie.index[i - 4]
            dv, db = mm[q] - mm[q4], mm_b[q] - mm_b[q4]
            f["Var. i.a. MM4T"] = dv
            f["Var. i.a. MM4T IC inf"], f["Var. i.a. MM4T IC sup"] = intervalo(db, dv)
        filas[q] = f
    return pd.DataFrame(filas).T

def significativa(lo, hi):
    return "significativa" if lo > 0 or hi < 0 else "no se distingue del ruido muestral"

inc = resumen_incertidumbre(termo["Termómetro"], boot_t)
ee_ia = (boot_t - boot_t.shift(4, axis=1)).std().mean()
VAR_MIN = 1.96 * ee_ia  # variación i.a. que en promedio se distingue del ruido
print(f"Error estándar medio: nivel {boot_t.std().mean():.1f} pts | variación i.a. {ee_ia:.1f} pts "
      f"-> una variación i.a. tiene que superar ~{VAR_MIN:.0f} pts para distinguirse del ruido")
inc.tail(8).round(2)
''')

md("""
## 6. El termómetro hoy

Valor del último trimestre (con su intervalo de confianza), comparado con el mismo trimestre del
año anterior (comparación interanual: neutraliza la estacionalidad).
""")

code(r'''
ult = termo.index[-1]
hace_un_anio = termo.index[-5] if len(termo) >= 5 else None
v = termo.loc[ult, "Termómetro"]
lo, hi = inc.loc[ult, "IC inf"], inc.loc[ult, "IC sup"]

fig, (ax_t, ax_d) = plt.subplots(1, 2, figsize=(11, 5.5), gridspec_kw={"width_ratios": [1, 3]})

# Termómetro vertical (la línea fina es el IC 95%)
for lo_f, hi_f, col, nombre in FRANJAS:
    ax_t.axhspan(lo_f, hi_f, xmin=0.3, xmax=0.7, color=col, alpha=0.18, lw=0)
    ax_t.text(0.75, (lo_f + hi_f) / 2, nombre, transform=ax_t.get_yaxis_transform(),
              va="center", color="#52514e", fontsize=10)
ax_t.bar(0.5, v, width=0.28, color=TINTA, zorder=3)
ax_t.scatter([0.5], [0], s=900, color=TINTA, zorder=3)
ax_t.plot([0.5, 0.5], [lo, hi], color="#8a8984", lw=2, zorder=4, solid_capstyle="round")
ax_t.text(0.5, max(v, hi) + 3, f"{v:.0f}", ha="center", va="bottom", fontsize=22, fontweight="bold", color=TINTA)
ax_t.set_xlim(0, 1.3); ax_t.set_ylim(-6, 112)
ax_t.set_xticks([]); ax_t.set_yticks([0, 33, 66, 100]); ax_t.grid(False)
ax_t.spines["bottom"].set_visible(False)
ax_t.set_title(f"Termómetro {ult}\n({franja(v)}; IC 95% {lo:.0f}-{hi:.0f})", color=TINTA)

# Dimensiones: último trimestre (con IC 95%) vs. mismo trimestre del año anterior
nombres = list(DIMENSIONES)
y = np.arange(len(nombres))
if hace_un_anio is not None:
    ax_d.scatter(dims.loc[hace_un_anio, nombres], y, s=90, facecolors="none",
                 edgecolors="#8a8984", linewidths=2, label=hace_un_anio, zorder=3)
for i, n in enumerate(nombres):
    d_lo, d_hi = intervalo(boot_d[n][ult], dims.loc[ult, n])
    ax_d.plot([d_lo, d_hi], [i, i], color=COLOR_DIM[n], lw=2, alpha=0.5, zorder=2, solid_capstyle="round")
ax_d.scatter(dims.loc[ult, nombres], y, s=110, c=[COLOR_DIM[n] for n in nombres],
             edgecolors="#fcfcfb", linewidths=2, label=ult, zorder=4)
for i, n in enumerate(nombres):
    ax_d.text(dims.loc[ult, n], i - 0.18, f"{dims.loc[ult, n]:.0f}", ha="center", va="bottom", color=TINTA)
ax_d.set_yticks(y, nombres); ax_d.set_ylim(len(nombres) - 0.5, -0.7)
ax_d.set_xlim(0, 100); ax_d.set_xlabel("Percentil histórico (0 = mejor, 100 = peor); línea = IC 95%")
ax_d.set_title("Dimensiones")
ax_d.legend(loc="lower right", frameon=False)
plt.tight_layout()
plt.show()

print(f"{ult}: {v:.1f} ({franja(v)}; IC 95% {lo:.1f} a {hi:.1f})")
if hace_un_anio is not None:
    r = inc.loc[ult]
    print(f"{hace_un_anio}: {termo.loc[hace_un_anio, 'Termómetro']:.1f} | variación interanual: "
          f"{r['Var. i.a.']:+.1f} pts (IC 95% {r['Var. i.a. IC inf']:+.1f} a {r['Var. i.a. IC sup']:+.1f}; "
          f"{significativa(r['Var. i.a. IC inf'], r['Var. i.a. IC sup'])})")
''')

md("""
## 7. Lectura del último trimestre

Resumen en texto generado a partir de los datos (se actualiza solo con cada trimestre nuevo
y se exporta en la sección 14). Incluye la posición del trimestre en la serie, la variación
interanual con su intervalo de confianza y si es significativa, qué dimensión la explica (cada
dimensión aporta 1/4 de su cambio), la media móvil y qué indicadores están en niveles extremos o
se movieron más.
""")

code(r'''
from IPython.display import Markdown, display

def f1(x, signo=False):
    """Número con 1 decimal y coma decimal (signo explícito opcional)."""
    return (f"{x:+.1f}" if signo else f"{x:.1f}").replace(".", ",").replace("-", "−")

def fv(c, x):
    """Valor de un indicador con su unidad (% o pesos de dic-2016)."""
    return f"${x:,.0f}".replace(",", ".") if UNIDAD[c] == "$" else f"{f1(x)}%"

def fd(c, x, x0):
    """Diferencia: puntos porcentuales para %, variación % para montos."""
    return f"{f1((x / x0 - 1) * 100, True)}%" if UNIDAD[c] == "$" else f"{f1(x - x0, True)} pp"

def se_movio(c, x, x0):
    """Movimiento relevante de un complementario: ≥ 1 pp (%) o ≥ 5% (montos)."""
    return abs(x / x0 - 1) >= 0.05 if UNIDAD[c] == "$" else abs(x - x0) >= 1

def posicion(serie, q, fem=False):
    """Ranking de q en la serie y desde cuándo no había un valor tan alto (o tan bajo).

    Devuelve (texto del ranking, texto "desde cuándo" o None si no hay trimestres previos).
    """
    serie = serie.dropna()
    v, n = serie[q], len(serie)
    alto = int(serie.rank(ascending=False, method="min")[q])
    bajo = int(serie.rank(ascending=True, method="min")[q])
    palabra = "alto" if alto <= bajo else "bajo"
    art = ("la más " + palabra[:-1] + "a") if fem else ("el valor más " + palabra)
    ranking = f"{min(alto, bajo)}.º trimestre más {palabra} de {n}"
    previos = serie.loc[:q].iloc[:-1]
    if previos.empty:
        return ranking, None
    iguales = previos[previos >= v] if palabra == "alto" else previos[previos <= v]
    if iguales.empty:
        return ranking, f"{art} de la serie" + ("" if q == serie.index[-1] else " hasta entonces")
    return ranking, f"{art} desde {iguales.index[-1]}"

def resumen_trimestre(q):
    t_ = termo["Termómetro"]
    ma = termo["Media móvil 4T"]
    r = inc.loc[q]
    i = termo.index.get_loc(q)
    q_ia = termo.index[i - 4] if i >= 4 else None
    q_ant = termo.index[i - 1] if i >= 1 else None
    L = [f"### Termómetro {q}: {f1(t_[q])} ({franja(t_[q])})", ""]

    ranking, desde = posicion(t_, q)
    L.append(f"- **Posición:** {ranking}" + (f" ({desde})" if desde else "")
             + f". Intervalo de confianza del 95%: {f1(r['IC inf'])} a {f1(r['IC sup'])}.")
    if q_ia is not None:
        contrib = ((dims.loc[q] - dims.loc[q_ia]) / len(DIMENSIONES)).sort_values(key=abs, ascending=False)
        partes = ", ".join(f"{n.split('. ')[1].lower()} {f1(c, True)}" for n, c in contrib.items())
        lo, hi = r["Var. i.a. IC inf"], r["Var. i.a. IC sup"]
        L.append(f"- **Interanual:** {f1(t_[q_ia])} en {q_ia} → {f1(t_[q])} "
                 f"(**{f1(t_[q] - t_[q_ia], True)} pts**; IC 95%: {f1(lo, True)} a {f1(hi, True)}, "
                 f"{significativa(lo, hi)}; sube en el {r['P(sube)'] * 100:.0f}% de las réplicas). "
                 f"Aporte por dimensión: {partes}.")
    if q_ant is not None:
        L.append(f"- **Trimestral:** {f1(t_[q] - t_[q_ant], True)} pts frente a {q_ant} "
                 f"(afectado por estacionalidad).")
    if pd.notna(ma[q]):
        _, desde = posicion(ma, q, fem=True)
        txt = f"- **Media móvil 4T:** {f1(ma[q])}" + (f" ({desde})" if desde else "")
        if pd.notna(r.get("Var. i.a. MM4T", np.nan)):
            lo, hi = r["Var. i.a. MM4T IC inf"], r["Var. i.a. MM4T IC sup"]
            txt += (f"; variación interanual {f1(r['Var. i.a. MM4T'], True)} pts "
                    f"(IC 95%: {f1(lo, True)} a {f1(hi, True)}, {significativa(lo, hi)})")
        L.append(txt + ".")
    L.append("- **Dimensiones:** " + " · ".join(
        f"{n} {f1(dims.loc[q, n])} ({franja(dims.loc[q, n])})" if pd.notna(dims.loc[q, n]) else f"{n} sin dato"
        for n in DIMENSIONES) + ".")
    vacias = [n for n in DIMENSIONES if pd.isna(dims.loc[q, n])]
    if vacias:
        L.append(f"- ⚠ **Provisorio:** sin dato para {', '.join(vacias)} (¿falta el IPC de los meses de "
                 f"referencia?): el termómetro de {q} se calculó con {len(DIMENSIONES) - len(vacias)} dimensiones.")

    # Indicadores en el peor / mejor valor de la serie (misma serie y redondeo que el índice)
    orient = pd.DataFrame({c: s * serie_indice(c).round(1) for c, s in SIGNO.items()})
    peor = [c for c in SIGNO if orient.loc[q, c] == orient[c].max()]
    mejor = [c for c in SIGNO if orient.loc[q, c] == orient[c].min()]
    if peor:
        L.append("- **En su peor nivel de la serie:** " +
                 "; ".join(f"{c} ({fv(c, ind.loc[q, c])})" for c in peor) + ".")
    if mejor:
        L.append("- **En su mejor nivel de la serie:** " +
                 "; ".join(f"{c} ({fv(c, ind.loc[q, c])})" for c in mejor) + ".")
    altos = norm.loc[q].loc[lambda s: (s >= 80)].sort_values(ascending=False).drop(peor, errors="ignore")
    if len(altos):
        L.append("- **Otros indicadores altos (percentil ≥ 80):** " +
                 "; ".join(f"{c} {fv(c, ind.loc[q, c])} (p{norm.loc[q, c]:.0f})" for c in altos.index) + ".")

    if q_ia is not None:
        mov = (norm.loc[q] - norm.loc[q_ia]).sort_values()
        def txt(cs):
            return "; ".join(f"{c} {fv(c, ind.loc[q, c])} ({fd(c, ind.loc[q, c], ind.loc[q_ia, c])}, "
                             f"p{norm.loc[q_ia, c]:.0f}→p{norm.loc[q, c]:.0f})" for c in cs)
        subas = mov[mov >= 20].index[::-1][:3]
        bajas = mov[mov <= -20].index[:3]
        if len(subas):
            L.append(f"- **Mayores deterioros interanuales:** {txt(subas)}.")
        if len(bajas):
            L.append(f"- **Mayores mejoras interanuales:** {txt(bajas)}.")
        comp = [c for c in COMPLEMENTARIOS
                if pd.notna(ind.loc[q, c]) and pd.notna(ind.loc[q_ia, c])
                and se_movio(c, ind.loc[q, c], ind.loc[q_ia, c])]
        if comp:
            L.append("- **Complementarios que se movieron (≥ 1 pp o ≥ 5%) i.a.:** " + "; ".join(
                f"{c} {fv(c, ind.loc[q, c])} ({fd(c, ind.loc[q, c], ind.loc[q_ia, c])})" for c in comp) + ".")
    return "\n".join(L)

resumen = resumen_trimestre(ult)
display(Markdown(resumen))
''')

md("""
## 8. Evolución del termómetro

Índice trimestral con su intervalo de confianza del 95% (banda gris), media móvil de 4
trimestres (suaviza la estacionalidad) y franjas.
""")

code(r'''
x = np.arange(len(termo))
fig, ax = plt.subplots(figsize=(12, 5.5))
for lo_f, hi_f, col, nombre in FRANJAS:
    ax.axhspan(lo_f, hi_f, color=col, alpha=0.08, lw=0)
    ax.text(len(termo) - 0.5, (lo_f + hi_f) / 2, nombre, va="center", ha="left", color="#52514e")
ax.fill_between(x, inc["IC inf"].astype(float), inc["IC sup"].astype(float), color="#8a8984", alpha=0.18,
                lw=0, label="IC 95%")
ax.plot(x, termo["Termómetro"], color="#8a8984", lw=1.5, marker="o", ms=4, label="Trimestral")
ax.plot(x, termo["Media móvil 4T"], color=TINTA, lw=2.5, label="Media móvil 4T")
i_max = int(np.nanargmax(termo["Termómetro"]))
i_min = int(np.nanargmin(termo["Termómetro"]))
for i in {i_max, i_min, len(termo) - 1}:
    ax.annotate(f"{termo.index[i]}: {termo['Termómetro'].iloc[i]:.0f}", (x[i], termo["Termómetro"].iloc[i]),
                xytext=(0, 10), textcoords="offset points", ha="center", color=TINTA, fontsize=9)
ax.set_xticks(x, termo.index, rotation=90)
ax.set_xlim(-0.5, len(termo) + 2); ax.set_ylim(0, 100)
ax.set_ylabel("Termómetro (0 = mejor, 100 = peor)")
ax.set_title("Termómetro de la economía de los hogares - EPH")
ax.legend(loc="upper left", frameon=False)
plt.tight_layout()
plt.show()
''')

md("""
## 9. Evolución por dimensión

Una línea por dimensión (percentil histórico promedio de sus indicadores, media móvil 4T).
""")

code(r'''
fig, ax = plt.subplots(figsize=(12, 5.5))
suav = dims.rolling(4).mean()
for n, col in COLOR_DIM.items():
    ax.plot(x, suav[n], color=col, lw=2, label=n)
# Etiquetas directas al final de cada línea, separadas para que no se pisen
fin = suav.iloc[-1].sort_values()
pos, prev = {}, -np.inf
for n, val in fin.items():
    pos[n] = max(val, prev + 5)
    prev = pos[n]
for n in fin.index:
    ax.text(x[-1] + 0.4, pos[n], f"{n.split('. ')[1]} ({fin[n]:.0f})", color="#52514e", va="center", fontsize=9)
ax.set_xticks(x, termo.index, rotation=90)
ax.set_xlim(-0.5, len(termo) + 5); ax.set_ylim(0, 100)
ax.set_ylabel("Percentil histórico (media móvil 4T)")
ax.set_title("Dimensiones del termómetro (0 = mejor, 100 = peor)")
ax.legend(loc="upper left", frameon=False)
plt.tight_layout()
plt.show()
''')

md("""
## 10. Mapa de calor de los indicadores

Cada celda es el percentil histórico del indicador en ese trimestre (más oscuro = peor).
Permite ver qué indicadores "empujan" el termómetro en cada momento.
""")

code(r'''
orden = [c for cols in DIMENSIONES.values() for c in cols]
fig, ax = plt.subplots(figsize=(13, 7))
im = ax.imshow(norm[orden].T.values, aspect="auto", cmap="Reds", vmin=0, vmax=100)
ax.set_yticks(range(len(orden)), orden)
ax.set_xticks(range(len(norm)), norm.index, rotation=90)
ax.grid(False)
# Separadores entre dimensiones
acum = 0
for cols in list(DIMENSIONES.values())[:-1]:
    acum += len(cols)
    ax.axhline(acum - 0.5, color="#fcfcfb", lw=3)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
cb.set_label("Percentil (100 = peor)")
ax.set_title("Indicadores normalizados por trimestre")
plt.tight_layout()
plt.show()
''')

md("""
## 11. Tabla del último trimestre

Valor de cada indicador, el mismo trimestre del año anterior, la diferencia (puntos
porcentuales para los %, variación % para los ingresos medios) y su percentil histórico.
Incluye los indicadores complementarios (fuera del índice, sin percentil). Los ingresos medios
están en pesos de dic-2016.
""")

code(r'''
filas = []
for dim, cols in DIMENSIONES.items():
    for c, signo in cols.items():
        filas.append((dim, c, signo))
for c in COMPLEMENTARIOS:
    filas.append(("Complementario (fuera del índice)", c, +1))

def dif(c, a, b):
    return (a / b - 1) * 100 if UNIDAD[c] == "$" else a - b

tabla = pd.DataFrame([{
    "Dimensión": dim,
    "Indicador": c,
    "Unidad": "$ dic-2016" if UNIDAD[c] == "$" else "%",
    ult: ind.loc[ult, c],
    **({hace_un_anio: ind.loc[hace_un_anio, c],
        "Dif. i.a. (pp o %)": dif(c, ind.loc[ult, c], ind.loc[hace_un_anio, c])} if hace_un_anio else {}),
    "Percentil histórico": norm.loc[ult, c] if c in norm else np.nan,
    "Sentido": "↑ peor" if signo > 0 else "↓ peor",
} for dim, c, signo in filas]).set_index(["Dimensión", "Indicador"])
tabla.round(1)
''')

md("""
## 12. Promedios anuales

Promedio de los trimestres de cada año (dimensiones y termómetro). El año en curso suele
estar incompleto (columna `Trimestres`): no es comparable con un año completo porque el
T1 tiende a ser peor.
""")

code(r'''
anio = termo.index.str[:4]
anual = termo[[*DIMENSIONES, "Termómetro"]].groupby(anio).mean()
anual.insert(0, "Trimestres", termo.groupby(anio).size())
anual["Estado"] = anual["Termómetro"].map(franja)
anual.index.name = "Año"

col_franja = {nombre: col for _, _, col, nombre in FRANJAS}
fig, ax = plt.subplots(figsize=(11, 4.8))
xa = np.arange(len(anual))
for i, (a, r) in enumerate(anual.iterrows()):
    incompleto = r["Trimestres"] < 4
    ax.bar(i, r["Termómetro"], color=col_franja[r["Estado"]], alpha=0.35 if incompleto else 0.85,
           hatch="//" if incompleto else None, edgecolor="#8a8984" if incompleto else "none", width=0.7)
    ax.text(i, r["Termómetro"] + 1.5, f"{r['Termómetro']:.0f}", ha="center", va="bottom", color=TINTA)
ax.set_xticks(xa, [a if n == 4 else f"{a}\n({n}T)" for a, n in zip(anual.index, anual["Trimestres"])])
ax.set_ylim(0, 100); ax.set_ylabel("Termómetro (promedio anual)")
ax.set_title("Termómetro por año")
ax.legend(handles=[mpatches.Patch(color=col, alpha=0.85, label=nombre) for _, _, col, nombre in FRANJAS],
          loc="upper left", frameon=False, ncol=3)
plt.tight_layout()
plt.show()

anual.round(1)
''')

md("""
## 13. Controles de calidad

Chequeos automáticos para correr después de sumar un trimestre (✓ = OK, ⚠ = revisar):

1. **Cobertura:** todos los indicadores del índice tienen dato en todos los trimestres (un
   faltante en el último trimestre suele indicar una columna que cambió de nombre en la base,
   o que el IPC todavía no cubre los meses de referencia de los ingresos).
2. **Tamaño de muestra:** el último trimestre tiene una cantidad de hogares normal (≥ 80% de
   la mediana), para detectar cargas incompletas.
3. **Chequeo de sentido:** el índice tiene que reconocer los episodios conocidos: máximo en
   la crisis 2019-2021, pandemia (2020T2-2021T1) en Fiebre en promedio, valle 2023T3-T4 en el
   tercio más bajo de la serie y el shock de ingresos de 2024T1-T2 en Fiebre en la dimensión D.
4. **Códigos estables** de `PP11O` (despidos) y `CH08` (cobertura de salud) antes y después del
   cambio de esquema de 4T2023 (referencia `PP11O` entre desocupados: código 1 = 12,7% → 14,2%,
   código 7 = 1,5% → 2,2%; `CH08` = 4 en toda la población: 31,3% → 32,1%).
""")

code(r'''
def chequeo(ok, texto):
    print(("✓ " if ok else "⚠ ") + texto)

# 1. Cobertura
faltan = ind[list(SIGNO)].isna()
chequeo(not faltan.values.any(),
        "Cobertura completa de los indicadores del índice" if not faltan.values.any() else
        "Faltan datos: " + "; ".join(f"{c} en {', '.join(faltan.index[faltan[c]])}"
                                     for c in faltan.columns if faltan[c].any()))

# 2. Tamaño de muestra
n_hog = hog.groupby(["ANIO", "TRIMESTRE"]).size()
n_hog.index = [f"{a}T{p}" for a, p in n_hog.index]
chequeo(n_hog.iloc[-1] >= 0.8 * n_hog.median(),
        f"Hogares en {n_hog.index[-1]}: {n_hog.iloc[-1]:,} (mediana de la serie {n_hog.median():,.0f})".replace(",", "."))

# 3. Chequeo de sentido
t_ = termo["Termómetro"]
q_max = t_.idxmax()
chequeo("2019" <= q_max[:4] <= "2021", f"Máximo de la serie: {q_max} ({f1(t_.max())}), esperado en 2019-2021")
if set(PANDEMIA) <= set(t_.index):
    m = t_.loc[PANDEMIA].mean()
    chequeo(m > 66, f"Pandemia 2020T2-2021T1: promedio {f1(m)} (esperado > 66, Fiebre)")
if set(VALLE) <= set(t_.index):
    p = t_.rank(pct=True).loc[VALLE].mean() * 100
    chequeo(p <= 33, f"Valle 2023T3-T4: promedio {f1(t_.loc[VALLE].mean())}, percentil {p:.0f} de la serie "
                     f"(esperado en el tercio más bajo)")
if {"2024T1", "2024T2"} <= set(t_.index):
    m = dims.loc[["2024T1", "2024T2"], "D. Ingresos reales"].mean()
    chequeo(m > 66, f"Shock de ingresos 2024T1-T2: dimensión D promedio {f1(m)} (esperado > 66, Fiebre)")

# 4. Códigos por esquema
pers["esquema"] = np.where(pers["ANIO"] * 10 + pers["TRIMESTRE"] >= 20234, "desde 2023T4", "hasta 2023T3")
def dist_codigos(sub, var):
    return (sub.groupby(["esquema", var])["PONDERA"].sum()
               .groupby(level=0).transform(lambda s: s / s.sum() * 100).unstack(0))
print("\nPP11O entre desocupados (% ponderado; 1 = despido/cierre, 7 = renuncia obligada/pactada):")
print(dist_codigos(pers[pers["ESTADO"] == 2], "PP11O").round(1).to_string())
print("\nCH08 en toda la población (% ponderado; 4 = sin cobertura de salud):")
print(dist_codigos(pers, "CH08").round(1).to_string())
''')

md("""
## 14. Exportar

Guarda en Drive (`carga_EPH/resultados/`), con separador `;` y decimal `,` para abrir
directo en Excel en español:

| Archivo | Contenido |
|---|---|
| `termometro_EPH.csv` | serie trimestral completa: indicadores (`pct_` en %, `pesos_` en pesos de dic-2016), percentiles (`perc_`), dimensiones, termómetro, media móvil, variación interanual, estado e intervalos de confianza (`Termómetro IC ...`, `P(sube)`) |
| `termometro_EPH_anual.csv` | promedios anuales (sección 12) |
| `termometro_EPH_resumen.md` | lectura del último trimestre (sección 7) |
""")

code(r'''
os.makedirs(RESULTADOS_DIR, exist_ok=True)
pref = {c: ("pesos_" if UNIDAD[c] == "$" else "pct_") + c for c in ind.columns}
ic = inc.drop(columns=["Valor", "MM4T", "Var. i.a."]).add_prefix("Termómetro ")
salida = pd.concat([
    ind.rename(columns=pref),
    norm.add_prefix("perc_"),
    termo,
    ic,
], axis=1)
salida.index.name = "trimestre"
opts = dict(sep=";", decimal=",", encoding="utf-8-sig")
archivos = {
    "termometro_EPH.csv": lambda p: salida.to_csv(p, **opts),
    "termometro_EPH_anual.csv": lambda p: anual.to_csv(p, **opts),
    "termometro_EPH_resumen.md": lambda p: open(p, "w", encoding="utf-8").write(resumen + "\n"),
}
for nombre, guardar in archivos.items():
    path = os.path.join(RESULTADOS_DIR, nombre)
    guardar(path)
    print("Guardado:", path)
print("Serie trimestral:", salida.shape, "| anual:", anual.shape)
''')

md("""
## Anexo A. Diagnóstico de variables candidatas

Herramienta para evaluar si conviene **sumar un indicador al índice**. No hace falta
correrla en la actualización trimestral: con `CANDIDATAS` vacío no hace nada.

**Cómo usarla:**
1. Definir el indicador en `INDICADORES` (sección 3) y agregarlo a `COMPLEMENTARIOS`
   (sección 4); si usa una variable nueva, sumarla a `PERS_COLS`/`HOG_COLS`.
2. Listarlo en `CANDIDATAS` (celda de abajo) con su dimensión, signo (+1 = más alto es
   peor), la variable de origen y el universo donde mirar sus códigos.
3. Correr el notebook y leer la tabla de criterios y el efecto sobre el índice.
4. Si pasa, moverlo a `DIMENSIONES` y repetir el chequeo de sentido (sección 13).

**Criterios (todos deben cumplirse):**
1. **Cobertura:** datos en todos los trimestres desde 2017 (ambos esquemas).
2. **Códigos estables:** la distribución de la variable no cambia bruscamente con el quiebre
   de esquema de 4T2023 (si cambia, el código pudo cambiar de significado). Se evalúa a ojo.
3. **Sentido:** peor (más alto) en la pandemia (2020T2-2021T1) que en el valle 2023T3-T4.
4. **Señal, no ruido:** autocorrelación de orden 1 ≥ 0,3 (la serie tiene persistencia).
5. **Relación con el índice:** correlación de Spearman con el termómetro actual ≥ 0,3.
6. **No redundante:** correlación absoluta < 0,85 con cada indicador que ya está en el índice.

Además conviene mirar el **error muestral** del indicador (desvío estándar de sus réplicas en
`ind_boot`, sección 3) frente a cuánto se mueve en la serie.

**Evaluaciones realizadas:**

| Candidata | Resultado | Motivo |
|---|---|---|
| Desocupados por despido/cierre (`PP11O==1`) | ✅ **Incorporada a A** (v3; luego ampliada con el código 7, renuncia obligada/pactada) | Pasa los 6 criterios: códigos estables entre esquemas (12,7% → 14,2% de los desocupados), pandemia 1,44% vs valle 0,56%, autocorrelación 0,76, Spearman 0,60, corr. máx. 0,83 (con desocupación). Con 1+7: pandemia 1,62% vs valle 0,65%, autocorr. 0,74, corr. máx. 0,82. |
| Pluriempleo (`PP03C==2`) | ❌ Descartada (complementaria) | Procíclica: cae en pandemia (7,8% vs 11,2% en el valle 2023) y en cada T1 (8,4% vs 10,1%); Spearman −0,05. |
| Sin cobertura de salud (`CH08==4`, % población) | ✅ **Incorporada a B** (v4, en lugar de asalariados sin descuento) | Pasa los 6 criterios: códigos estables (31,3% → 32,1%), pandemia > valle (+2,4 pp), autocorr. 0,69, Spearman 0,33, corr. máx. 0,67. Con el cambio: pandemia en el percentil 95 (antes 91), señal/ruido 19,9 (antes 17,9), corr. i.a. con el EMAE −0,42 (antes −0,32). |
| Asalariados sin descuento jubilatorio (estaba en B) | ❌ **Sale del índice** (v4, complementario) | Falla 2 criterios aplicados a los indicadores existentes: cae en la pandemia (35,8% → 23,8% en 2020T2, efecto composición) y tiene Spearman −0,23 con el índice. |
| Ingreso laboral real (`P21`/IPC) y personas con ingreso per cápita real bajo (`IPCF`/IPC) | ✅ **Nueva dimensión D** (v4) | Corr. de ingreso bajo con la pobreza oficial 0,87; entre sí −0,83. Con D: corr. del índice con la pobreza 0,60 (antes 0,29), corr. i.a. con el EMAE −0,53, señal/ruido 22,1, 2024T1 = 57 (antes 44). |
| Ingreso per cápita familiar real (media geométrica) | ❌ Complementaria | Redundante con personas con ingreso bajo (corr. 0,98). |
| Horas trabajadas por persona de 10+, desocupación de jefes, hogares con activos y sin ocupados, despidos + cierres de cuentapropistas (`PP11L`∈{1,2,4}), hogares con 2+ estrategias, jóvenes 18-24 que no estudian ni trabajan, ocupados que quieren más horas (`PP03G`) | ❌ Descartadas | Redundantes: corr. 0,88-0,95 con un indicador del índice (tasa de empleo, desocupación, despidos, vendieron pertenencias o subocupación). Sumarlas mueve el índice ≤ 4 pts. |
| Ocupados ausentes (`INTENSI==4`), asalariados temporarios (`PP07C==1`), préstamos bancarios, cuotas/fiado, indemnización o seguro de desempleo (`V3`/`V4`) | ❌ Descartadas | Ausentes: estacionalidad por vacaciones (R² 0,60) y autocorr. 0,13. Temporarios, préstamos y cuotas: caen en la pandemia. Indemnización/seguro: 0,8% de hogares (ruido). |

Evaluaciones de 2026-10 hechas con los 37 trimestres (T1-2017 a T1-2026) y 300 réplicas
bootstrap, fuera del notebook. Variantes de metodología probadas y descartadas: z-scores, min-max,
desestacionalizar todo el índice, pesos por componentes principales o por indicador, dimensión C
ponderada por personas (correlación 0,93-0,98 con el índice; ninguna mejora clara).
""")

code(r'''
# Candidatas a evaluar: nombre del indicador (sección 3) -> configuración.
#   dimension: dimensión donde entraría | signo: +1 si más alto es peor
#   variable: variable EPH de origen (para mirar sus códigos por esquema; None = no mirar)
#   universo: "ocupados", "desocupados" o "todos" (filas donde mirar los códigos)
# Ejemplo (ya evaluado y descartado):
# CANDIDATAS = {"Pluriempleo": {"dimension": "C. Estrés de los hogares", "signo": +1,
#                               "variable": "PP03C", "universo": "ocupados"}}
CANDIDATAS = {}

UNIVERSOS = {"ocupados": pers["ESTADO"] == 1, "desocupados": pers["ESTADO"] == 2,
             "todos": pd.Series(True, index=pers.index)}

if not CANDIDATAS:
    print("Sin candidatas para evaluar (CANDIDATAS vacío). Ver instrucciones arriba.")
else:
    # Criterio 2: distribución de códigos antes/después del quiebre de esquema 4T2023
    for c, cfg in CANDIDATAS.items():
        var = cfg.get("variable")
        if var is None:
            continue
        print(f"\n{c}: distribución de {var} (% ponderado, universo {cfg.get('universo', 'todos')}):")
        print(dist_codigos(pers[UNIVERSOS[cfg.get("universo", "todos")]], var).round(1).to_string())

    filas = []
    for c, cfg in CANDIDATAS.items():
        s, signo = ind[c], cfg["signo"]
        corr_ind = ind[list(SIGNO)].corrwith(s, method="spearman").abs()
        chk = {
            "Primer trimestre con dato": s.first_valid_index(),
            "Trimestres sin dato": int(s.isna().sum()),
            "Media pandemia": s.loc[PANDEMIA].mean(),
            "Media valle 2023": s.loc[VALLE].mean(),
            "Autocorrelación lag 1": s.autocorr(1),
            "Spearman con termómetro": s.corr(termo["Termómetro"], method="spearman"),
            "Máx. corr. con indicador del índice": corr_ind.max(),
            "Indicador más parecido": corr_ind.idxmax(),
            "Error estándar medio": np.nanstd(ind_boot[:, :, NOMBRES.index(c)], axis=0).mean(),
            "Desvío estándar de la serie": s.std(),
        }
        ok = {
            "1. Cobertura": chk["Trimestres sin dato"] == 0 and chk["Primer trimestre con dato"] == ind.index[0],
            "3. Sentido": signo * (chk["Media pandemia"] - chk["Media valle 2023"]) > 0,
            "4. Señal": chk["Autocorrelación lag 1"] >= 0.3,
            "5. Relación": signo * chk["Spearman con termómetro"] >= 0.3,
            "6. No redundante": chk["Máx. corr. con indicador del índice"] < 0.85,
        }
        filas.append({"Candidata": c, **chk, **ok, "Pasa (sin contar criterio 2)": all(ok.values())})
    display(pd.DataFrame(filas).set_index("Candidata").T)
''')

code(r'''
if CANDIDATAS:
    # Serie de cada candidata, con pandemia y valle 2023 sombreados
    fig, axes = plt.subplots(1, len(CANDIDATAS), figsize=(6.5 * len(CANDIDATAS), 4.5), squeeze=False)
    for ax, c in zip(axes[0], CANDIDATAS):
        for rango, nombre in [(PANDEMIA, "Pandemia"), (VALLE, "Valle 2023")]:
            i0, i1 = ind.index.get_loc(rango[0]), ind.index.get_loc(rango[-1])
            ax.axvspan(i0 - 0.5, i1 + 0.5, color="#e4e3df", lw=0)
            ax.text((i0 + i1) / 2, 1.01, nombre, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", color="#52514e", fontsize=8)
        ax.plot(x, ind[c], color=TINTA, lw=2, marker="o", ms=3)
        ax.set_title(c + (" ($ dic-2016)" if UNIDAD[c] == "$" else " (%)"), pad=16)
        ax.set_xticks(x[::4], ind.index[::4], rotation=90)
    plt.tight_layout()
    plt.show()

    # Efecto sobre el índice si se agregaran las candidatas
    dims_con = {d: dict(cols) for d, cols in DIMENSIONES.items()}
    for c, cfg in CANDIDATAS.items():
        dims_con[cfg["dimension"]][c] = cfg["signo"]
    _, _, t_con = armar_termometro(dims_con)
    comp = pd.DataFrame({"Actual": termo["Termómetro"], "Con candidatas": t_con})
    comp["Diferencia"] = comp["Con candidatas"] - comp["Actual"]
    print(f"Correlación actual vs. con candidatas: {comp['Actual'].corr(comp['Con candidatas']):.3f} | "
          f"diferencia máx.: {comp['Diferencia'].abs().max():.1f} pts")
    print(f"Máximo: {comp['Actual'].idxmax()} -> {comp['Con candidatas'].idxmax()} | "
          f"mínimo: {comp['Actual'].idxmin()} -> {comp['Con candidatas'].idxmin()}")
    display(comp.loc[["2019T2", *PANDEMIA, *VALLE, "2024T1", ult]].round(1))
''')

md("""
## Anexo B. Historial de versiones del índice

| Versión | Cambio | Por qué |
|---|---|---|
| **v1** | 3 dimensiones; A: desocupación, empleo, desocupación > 1 año, desalentados; B: subocupación, buscan otro empleo, sin descuento jubilatorio; C: `V13`, `V14`, `V17`, `V6`, `V7`, niños que aportan | Falló el chequeo de sentido: 2020T2 = 48 (dimensión B = 0,9) por **efecto composición**; desalentados y niños (~0,1%) metían ruido. |
| **v2** | Desalentados y niños pasan a complementarios; B suma la tasa de empleo asalariado registrado sobre población; redondeo a 1 decimal antes de rankear | 2020T2 → 64,7; máximo en 2020T4. |
| **v3** | A suma desocupados por despido/cierre (`PP11O==1`) y renuncia obligada/pactada (`PP11O==7`); pluriempleo evaluado y descartado | Pasó los 6 criterios del Anexo A; adelanta los deterioros (2018T3-T4, 2024T1). |
| v3 (notebook, 2026-09-29) | Sin cambios en el índice. Se suman la lectura automática, promedios anuales, controles de calidad, exportación del anual y del resumen; el diagnóstico pasa a anexo | Dejar la corrida trimestral limpia y autoexplicada. |
| **v4** (2026-10) | (1) **Intervalos de confianza** por bootstrap de viviendas (nivel, variación i.a., media móvil) en la lectura, los gráficos y la exportación. (2) En B, **sin cobertura de salud** (`CH08==4`) reemplaza a asalariados sin descuento jubilatorio. (3) Nueva **dimensión D. Ingresos reales**: ingreso laboral real e ingreso per cápita familiar real bajo (IPC nacional, mes anterior a la entrevista, desestacionalizados por aguinaldo); cada dimensión pesa 1/4 | Con v3, una variación i.a. de +11 era indistinguible del ruido (IC 95% −0,2 a +22,6) y el índice no veía los ingresos: corr. con la pobreza oficial 0,29, valle 2023 como mejor momento con pobreza del 41,7% y 2024T1 (pobreza 52,9%) en 44. Con v4: corr. con la pobreza 0,60, i.a. con el EMAE −0,53, menos ruido y menos revisiones. |

Referencia de resultados v3 (T1-2017 → T1-2026): máximo 2020T4 = 82,1; mínimo 2017T4 = 20,4;
valle 2023T3 = 22,4; 2020T2 = 65,7; 2026T1 = 60,0 (Tibio, +11,0 i.a.).
Referencia v4 (misma serie): máximo 2020T4 = 89,7; mínimo 2017T4 = 13,4; valle 2023T3-T4 =
31,0 / 32,3; 2020T2 = 70,1; 2024T1 = 56,6; 2026T1 = 52,8 (Tibio; IC 95% 44,4 a 60,6), +5,4 i.a.
(IC −4,4 a +15,1: no significativa); media móvil 4T 49,8, −6,3 i.a. (IC −11,3 a −0,6: significativa).
Los valores se mueven levemente al sumar trimestres (los percentiles se recalculan con toda la
historia).
""")

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.10"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("ok", OUT, len(cells), "celdas")
