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
**00_preparacion_bases**.

**Tres dimensiones (etapa 1: sin variables monetarias, no requiere deflactar):**

| Dimensión | Indicador | Variables EPH | Base |
|---|---|---|---|
| **A. Cantidad de empleo** | Desocupación | `ESTADO` | % PEA |
| | Tasa de empleo (invertida) | `ESTADO` | % población |
| | Desocupación de larga duración (>1 año buscando) | `ESTADO==2` & `PP10A==5` | % PEA |
| | Desocupados por despido/cierre o renuncia obligada/pactada (ex asalariados) | `ESTADO==2` & `PP11O∈{1,7}` | % PEA |
| **B. Calidad del empleo** | Subocupación horaria | `INTENSI==1` | % PEA |
| | Ocupados demandantes de otro empleo | `ESTADO==1` & `PP03J==1` | % PEA |
| | Asalariados sin descuento jubilatorio | `CAT_OCUP==3` & `PP07H==2` | % asalariados |
| | Tasa de empleo asalariado registrado (invertida) | `CAT_OCUP==3` & `PP07H==1` | % población |
| **C. Estrés de los hogares** (últimos 3 meses) | Gastaron ahorros | `V13==1` | % hogares |
| | Pidieron préstamos a familiares/amigos | `V14==1` | % hogares |
| | Vendieron pertenencias | `V17==1` | % hogares |
| | Recibieron mercadería/alimentos del gobierno, iglesias, escuelas | `V6==1` | % hogares |
| | Recibieron mercadería/alimentos de familiares/vecinos | `V7==1` | % hogares |

**Metodología:**
1. Cada indicador se calcula por trimestre, ponderado con `PONDERA` (hogares: un registro
   por hogar, el jefe/a `CH03==1`).
2. Se orienta para que "más alto = peor" (la tasa de empleo se invierte) y se normaliza
   como **percentil dentro de su propia historia** 2017-hoy (0 = mejor valor observado,
   100 = peor). Percentiles en lugar de min-max para que un outlier (2020T2) no aplaste
   el resto de la serie.
3. Dimensión = promedio de sus indicadores; **Termómetro = promedio simple de las 3
   dimensiones** (cada dimensión pesa 1/3).

**Quedan fuera del índice (se muestran como complementarios):**
- Préstamos bancarios (`V15`) y compras en cuotas/fiado (`V16`): suben tanto por estrés como
  por mayor acceso al crédito (señal ambigua).
- Informalidad `EMPLEO`: solo existe desde 2023T4 (en el índice se usa `PP07H`, serie larga).
- Pluriempleo (`PP03C==2`): evaluado y descartado en la sección 10 (es procíclico: cae en
  la pandemia y en cada T1, se comporta como un indicador de empleo, no de estrés).
- Desalentados (`PP02E==3`) y niños <10 que aportan dinero (`V19_A/B`): niveles de 0,0-0,4%,
  donde la diferencia entre trimestres es ruido muestral; además los desalentados *bajan*
  en 2020 (en cuarentena no se buscaba trabajo por otras razones).

**Efecto composición (por qué hay una tasa sobre población en la dimensión B):** en
2020T2 se perdieron sobre todo empleos informales y de pocas horas, así que los indicadores
calculados *sobre los ocupados* (informalidad, subocupación, ocupados que buscan otro empleo)
**mejoraron** artificialmente. La tasa de empleo asalariado registrado sobre la población no
tiene ese sesgo y compensa la dimensión.

**Advertencias:** la EPH cubre 31 aglomerados urbanos y se publica ~3 meses después del
trimestre. 2020T2-T3 se relevó telefónicamente (pandemia). Hay estacionalidad (el T1 suele
ser peor), por eso también se muestra la **variación interanual** y la media móvil de 4
trimestres. Etapa 2 (pendiente): ingresos reales (`P21`, `IPCF` deflactados por IPC) y
pobreza por canastas.
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
import numpy as np
import pandas as pd
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

# Paleta (validada para daltonismo): una por dimensión + tinta para el índice.
COLOR_DIM = {"A. Cantidad de empleo": "#2a78d6",
             "B. Calidad del empleo": "#eb6834",
             "C. Estrés de los hogares": "#1baf7a"}
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

Personas (mercado laboral) y hogares (estrategias del hogar, un registro por hogar).
Todas las columnas se fuerzan a numéricas (ver gotcha de dtypes en `docs/TECNICO.md`).
""")

code(r'''
PERS_COLS = ["ESTADO", "INTENSI", "PP10A", "PP02E", "PP03J", "PP07H", "CAT_OCUP", "EMPLEO",
             "PP11O", "PP03C", "PONDERA"]
HOG_COLS = ["CH03", "V6", "V7", "V13", "V14", "V15", "V16", "V17", "V19_A", "V19_B", "PONDERA"]

def cargar(cols):
    df = load_panel(columns=cols, out_dir=PROCESSED_DIR)
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = np.nan  # columna inexistente en todos los trimestres
    return df

pers = cargar(PERS_COLS)
hog = cargar(HOG_COLS)
hog = hog[hog["CH03"] == 1].drop(columns="CH03")
print(f"Personas: {len(pers):,} filas | Hogares: {len(hog):,} filas")
''')

md("""
## 3. Indicadores por trimestre

Todos en %. "Más alto = peor" salvo la tasa de empleo (se invierte al normalizar).
""")

code(r'''
def pct(w, num, den):
    """% ponderado: suma de w donde num&den, sobre suma de w donde den."""
    d = w[den].sum()
    return w[num & den].sum() / d * 100 if d > 0 else np.nan

def ind_personas(g):
    w, e = g["PONDERA"], g["ESTADO"]
    todos = pd.Series(True, index=g.index)
    ocup, desoc = e == 1, e == 2
    pea = ocup | desoc
    asal = ocup & (g["CAT_OCUP"] == 3)
    d = w[pea].sum()
    return pd.Series({
        "Desocupación": pct(w, desoc, pea),
        "Tasa de empleo": pct(w, ocup, todos),
        "Desocupación >1 año": w[desoc & (g["PP10A"] == 5)].sum() / d * 100,
        "Desalentados": w[(e == 3) & (g["PP02E"] == 3)].sum() / d * 100,
        "Subocupación": w[g["INTENSI"] == 1].sum() / d * 100,
        "Ocupados que buscan otro empleo": w[ocup & (g["PP03J"] == 1)].sum() / d * 100,
        "Asalariados sin descuento jubilatorio": pct(w, g["PP07H"] == 2, asal),
        "Tasa de empleo asalariado registrado": pct(w, asal & (g["PP07H"] == 1), todos),
        "Desocupados por despido (incl. renuncia forzada)": w[desoc & g["PP11O"].isin([1, 7])].sum() / d * 100,  # 1 despido/cierre, 7 renuncia obligada/pactada
        # complementario (evaluado y descartado para el índice, ver sección 10)
        "Pluriempleo": pct(w, g["PP03C"] == 2, ocup),
        # complementario (solo desde 2023T4)
        "Informalidad (EMPLEO)": pct(w, g["EMPLEO"] == 2, ocup) if g["EMPLEO"].notna().any() else np.nan,
    })

def ind_hogares(g):
    w = g["PONDERA"]
    todos = pd.Series(True, index=g.index)
    return pd.Series({
        "Gastaron ahorros": pct(w, g["V13"] == 1, todos),
        "Préstamos de familiares/amigos": pct(w, g["V14"] == 1, todos),
        "Vendieron pertenencias": pct(w, g["V17"] == 1, todos),
        "Alimentos de gobierno/instituciones": pct(w, g["V6"] == 1, todos),
        "Alimentos de familiares/vecinos": pct(w, g["V7"] == 1, todos),
        "Niños <10 aportan dinero": pct(w, (g["V19_A"] == 1) | (g["V19_B"] == 1), todos),
        # complementarios (señal ambigua: estrés o más acceso al crédito)
        "Préstamos de bancos/financieras": pct(w, g["V15"] == 1, todos),
        "Compras en cuotas/fiado": pct(w, g["V16"] == 1, todos),
    })

ind = pd.concat([
    pers.groupby(["ANIO", "TRIMESTRE"]).apply(ind_personas, include_groups=False),
    hog.groupby(["ANIO", "TRIMESTRE"]).apply(ind_hogares, include_groups=False),
], axis=1).sort_index()
ind.index = [f"{y}T{p}" for y, p in ind.index]
ind.round(1)
''')

md("""
## 4. Normalización y armado del termómetro

Cada indicador se convierte en su **percentil histórico orientado** (0 = mejor trimestre
de la serie, 100 = peor).
""")

code(r'''
DIMENSIONES = {
    "A. Cantidad de empleo": {"Desocupación": +1, "Tasa de empleo": -1,
                              "Desocupación >1 año": +1, "Desocupados por despido (incl. renuncia forzada)": +1},
    "B. Calidad del empleo": {"Subocupación": +1, "Ocupados que buscan otro empleo": +1,
                              "Asalariados sin descuento jubilatorio": +1,
                              "Tasa de empleo asalariado registrado": -1},
    "C. Estrés de los hogares": {"Gastaron ahorros": +1, "Préstamos de familiares/amigos": +1,
                                 "Vendieron pertenencias": +1,
                                 "Alimentos de gobierno/instituciones": +1,
                                 "Alimentos de familiares/vecinos": +1},
}
COMPLEMENTARIOS = ["Informalidad (EMPLEO)", "Préstamos de bancos/financieras", "Compras en cuotas/fiado",
                   "Desalentados", "Niños <10 aportan dinero",
                   "Pluriempleo"]

def percentil_orientado(s, signo):
    """0 = mejor valor de la serie, 100 = peor.

    Se redondea a 1 decimal antes de rankear: diferencias menores a 0,1 pp son ruido
    muestral, y así los empates quedan en el percentil promedio en vez de en los extremos
    (importa en indicadores de nivel muy bajo, como desalentados o niños que aportan).
    """
    r = (signo * s.round(1)).rank(method="average")
    n = r.notna().sum()
    return (r - 1) / (n - 1) * 100 if n > 1 else r * np.nan

def armar_termometro(dimensiones):
    """Devuelve (percentiles por indicador, dimensiones, termómetro) para un set de indicadores."""
    norm = pd.DataFrame({ind_name: percentil_orientado(ind[ind_name], signo)
                         for dim in dimensiones.values() for ind_name, signo in dim.items()})
    dims = pd.DataFrame({dim: norm[list(cols)].mean(axis=1) for dim, cols in dimensiones.items()})
    return norm, dims, dims.mean(axis=1)

norm, dims, t = armar_termometro(DIMENSIONES)
termo = dims.copy()
termo["Termómetro"] = t
termo["Media móvil 4T"] = termo["Termómetro"].rolling(4).mean()
termo["Var. interanual (pts)"] = termo["Termómetro"].diff(4)

def franja(v):
    for lo, hi, _, nombre in FRANJAS:
        if v <= hi:
            return nombre
    return FRANJAS[-1][3]

termo["Estado"] = termo["Termómetro"].map(franja)
termo.round(1)
''')

md("""
## 5. El termómetro hoy

Valor del último trimestre, comparado con el mismo trimestre del año anterior
(comparación interanual: neutraliza la estacionalidad).
""")

code(r'''
ult = termo.index[-1]
hace_un_anio = termo.index[-5] if len(termo) >= 5 else None
v = termo.loc[ult, "Termómetro"]

fig, (ax_t, ax_d) = plt.subplots(1, 2, figsize=(11, 5.5), gridspec_kw={"width_ratios": [1, 3]})

# Termómetro vertical
for lo, hi, col, nombre in FRANJAS:
    ax_t.axhspan(lo, hi, xmin=0.3, xmax=0.7, color=col, alpha=0.18, lw=0)
    ax_t.text(0.75, (lo + hi) / 2, nombre, transform=ax_t.get_yaxis_transform(),
              va="center", color="#52514e", fontsize=10)
ax_t.bar(0.5, v, width=0.28, color=TINTA, zorder=3)
ax_t.scatter([0.5], [0], s=900, color=TINTA, zorder=3)
ax_t.text(0.5, v + 3, f"{v:.0f}", ha="center", va="bottom", fontsize=22, fontweight="bold", color=TINTA)
ax_t.set_xlim(0, 1.3); ax_t.set_ylim(-6, 108)
ax_t.set_xticks([]); ax_t.set_yticks([0, 33, 66, 100]); ax_t.grid(False)
ax_t.spines["bottom"].set_visible(False)
ax_t.set_title(f"Termómetro {ult}\n({franja(v)})", color=TINTA)

# Dimensiones: último trimestre vs. mismo trimestre del año anterior
nombres = list(DIMENSIONES)
y = np.arange(len(nombres))
if hace_un_anio is not None:
    ax_d.scatter(dims.loc[hace_un_anio, nombres], y, s=90, facecolors="none",
                 edgecolors="#8a8984", linewidths=2, label=hace_un_anio, zorder=3)
ax_d.scatter(dims.loc[ult, nombres], y, s=110, c=[COLOR_DIM[n] for n in nombres],
             edgecolors="#fcfcfb", linewidths=2, label=ult, zorder=4)
for i, n in enumerate(nombres):
    ax_d.text(dims.loc[ult, n], i - 0.18, f"{dims.loc[ult, n]:.0f}", ha="center", va="bottom", color=TINTA)
ax_d.set_yticks(y, nombres); ax_d.set_ylim(len(nombres) - 0.5, -0.7)
ax_d.set_xlim(0, 100); ax_d.set_xlabel("Percentil histórico (0 = mejor, 100 = peor)")
ax_d.set_title("Dimensiones")
ax_d.legend(loc="lower right", frameon=False)
plt.tight_layout()
plt.show()

if hace_un_anio is not None:
    delta = termo.loc[ult, "Var. interanual (pts)"]
    print(f"{ult}: {v:.1f} ({franja(v)}) | {hace_un_anio}: {termo.loc[hace_un_anio, 'Termómetro']:.1f} "
          f"| variación interanual: {delta:+.1f} pts")
''')

md("""
## 6. Evolución del termómetro

Índice trimestral, media móvil de 4 trimestres (suaviza la estacionalidad) y franjas.
""")

code(r'''
x = np.arange(len(termo))
fig, ax = plt.subplots(figsize=(12, 5.5))
for lo, hi, col, nombre in FRANJAS:
    ax.axhspan(lo, hi, color=col, alpha=0.08, lw=0)
    ax.text(len(termo) - 0.5, (lo + hi) / 2, nombre, va="center", ha="left", color="#52514e")
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
## 7. Evolución por dimensión

Una línea por dimensión (percentil histórico promedio de sus indicadores).
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
## 8. Mapa de calor de los indicadores

Cada celda es el percentil histórico del indicador en ese trimestre (más oscuro = peor).
Permite ver qué indicadores "empujan" el termómetro en cada momento.
""")

code(r'''
orden = [c for cols in DIMENSIONES.values() for c in cols]
fig, ax = plt.subplots(figsize=(13, 6.5))
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
## 9. Tabla del último trimestre

Valor de cada indicador (en %), el mismo trimestre del año anterior, la diferencia
(puntos porcentuales) y su percentil histórico. Incluye los indicadores complementarios
(fuera del índice).
""")

code(r'''
filas = []
for dim, cols in DIMENSIONES.items():
    for c, signo in cols.items():
        filas.append((dim, c, signo))
for c in COMPLEMENTARIOS:
    filas.append(("Complementario (fuera del índice)", c, +1))

tabla = pd.DataFrame([{
    "Dimensión": dim,
    "Indicador": c,
    ult: ind.loc[ult, c],
    **({hace_un_anio: ind.loc[hace_un_anio, c],
        "Dif. i.a. (pp)": ind.loc[ult, c] - ind.loc[hace_un_anio, c]} if hace_un_anio else {}),
    "Percentil histórico": norm.loc[ult, c] if c in norm else np.nan,
    "Sentido": "↑ peor" if signo > 0 else "↓ peor",
} for dim, c, signo in filas]).set_index(["Dimensión", "Indicador"])
tabla.round(1)
''')

md("""
## 10. Diagnóstico de variables candidatas

Herramienta para evaluar si conviene sumar un indicador al índice: se agrega su cálculo en
la sección 3 y se lo lista en `CANDIDATAS` (nombre → dimensión y signo).

**Evaluaciones realizadas (2026-09, serie 2017T1-2026T1):**

| Candidata | Resultado | Motivo |
|---|---|---|
| Desocupados por despido/cierre (`PP11O==1`) | ✅ **Incorporada a A** (luego ampliada con el código 7, renuncia obligada/pactada = despido encubierto; ~2% de los desocupados) | Pasa los 6 criterios: códigos estables entre esquemas (12,7% → 14,2% de los desocupados), pandemia 1,44% vs valle 0,56%, autocorrelación 0,76, Spearman con termómetro 0,60, corr. máx. 0,83 (con desocupación). Sin estacionalidad. Sube antes en 2018T3-T4 y 2024T1. |
| Pluriempleo (`PP03C==2`) | ❌ **Descartada** (queda como complementaria) | Procíclica: cae en pandemia (7,8% vs 11,2% en el valle 2023) y en cada T1 (8,4% vs 10,1%); corr. 0,77 con la tasa de empleo; leve cambio de códigos con el esquema 4T2023. |

**Criterios (todos deben cumplirse):**
1. **Cobertura:** datos en todos los trimestres desde 2017 (ambos esquemas).
2. **Códigos estables:** la distribución de `PP11O`/`PP03C` no cambia bruscamente con el quiebre
   de esquema de 4T2023 (si cambia, el código pudo cambiar de significado).
3. **Sentido:** peor (más alto) en la pandemia (2020T2-2021T1) que en el valle 2023T3-T4.
4. **Señal, no ruido:** autocorrelación de orden 1 ≥ 0,3 (la serie tiene persistencia).
5. **Relación con el índice:** correlación de Spearman con el termómetro actual ≥ 0,3.
6. **No redundante:** correlación absoluta < 0,85 con cada indicador que ya está en el índice.
""")

code(r'''
# Candidatas a evaluar: nombre del indicador (sección 3) -> (dimensión, signo).
# Se deja Pluriempleo como ejemplo (ya evaluada y descartada).
CANDIDATAS = {"Pluriempleo": ("C. Estrés de los hogares", +1)}
PANDEMIA = ["2020T2", "2020T3", "2020T4", "2021T1"]
VALLE = ["2023T3", "2023T4"]
en_indice = [c for cols in DIMENSIONES.values() for c in cols]

# Criterio 2: distribución de códigos antes/después del quiebre de esquema 4T2023
pers["esquema"] = np.where(pers["ANIO"] * 10 + pers["TRIMESTRE"] >= 20234, "desde 2023T4", "hasta 2023T3")
# PP11O se sigue monitoreando porque está en el índice (códigos 1 y 7)
for var, filtro in [("PP11O", pers["ESTADO"] == 2), ("PP03C", pers["ESTADO"] == 1)]:
    sub = pers[filtro]
    dist = (sub.groupby(["esquema", var])["PONDERA"].sum()
               .groupby(level=0).transform(lambda x: x / x.sum() * 100).unstack(0))
    print(f"\nDistribución de {var} (% ponderado):")
    print(dist.round(1).to_string())

filas = []
for c, (dim, signo) in CANDIDATAS.items():
    s = ind[c]
    corr_ind = ind[en_indice].corrwith(s, method="spearman").abs()
    chk = {
        "Primer trimestre con dato": s.first_valid_index(),
        "Trimestres sin dato": int(s.isna().sum()),
        "Media pandemia": s.loc[PANDEMIA].mean(),
        "Media valle 2023": s.loc[VALLE].mean(),
        "Autocorrelación lag 1": s.autocorr(1),
        "Spearman con termómetro": s.corr(termo["Termómetro"], method="spearman"),
        "Máx. corr. con indicador del índice": corr_ind.max(),
        "Indicador más parecido": corr_ind.idxmax(),
    }
    ok = {
        "1. Cobertura": chk["Trimestres sin dato"] == 0 and chk["Primer trimestre con dato"] == ind.index[0],
        "3. Sentido": signo * (chk["Media pandemia"] - chk["Media valle 2023"]) > 0,
        "4. Señal": chk["Autocorrelación lag 1"] >= 0.3,
        "5. Relación": signo * chk["Spearman con termómetro"] >= 0.3,
        "6. No redundante": chk["Máx. corr. con indicador del índice"] < 0.85,
    }
    filas.append({"Candidata": c, **chk, **ok, "Pasa (sin contar criterio 2)": all(ok.values())})

diag = pd.DataFrame(filas).set_index("Candidata").T
diag
''')

code(r'''
# Serie de cada candidata, con pandemia y valle 2023 sombreados
fig, axes = plt.subplots(1, len(CANDIDATAS), figsize=(13, 4.5), sharex=True)
for ax, c in zip(np.atleast_1d(axes), CANDIDATAS):
    for rango, nombre in [(PANDEMIA, "Pandemia"), (VALLE, "Valle 2023")]:
        i0, i1 = ind.index.get_loc(rango[0]), ind.index.get_loc(rango[-1])
        ax.axvspan(i0 - 0.5, i1 + 0.5, color="#e4e3df", lw=0)
        ax.text((i0 + i1) / 2, 1.01, nombre, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", color="#52514e", fontsize=8)
    ax.plot(x, ind[c], color=TINTA, lw=2, marker="o", ms=3)
    ax.set_title(c + " (%)", pad=16)
    ax.set_xticks(x[::4], ind.index[::4], rotation=90)
plt.tight_layout()
plt.show()

# Efecto sobre el índice si se agregaran las candidatas
dims_con = {d: dict(cols) for d, cols in DIMENSIONES.items()}
for c, (dim, signo) in CANDIDATAS.items():
    dims_con[dim][c] = signo
_, _, t_con = armar_termometro(dims_con)
comp = pd.DataFrame({"Actual": termo["Termómetro"], "Con candidatas": t_con})
comp["Diferencia"] = comp["Con candidatas"] - comp["Actual"]
print(f"Correlación actual vs. con candidatas: {comp['Actual'].corr(comp['Con candidatas']):.3f} | "
      f"diferencia máx.: {comp['Diferencia'].abs().max():.1f} pts")
print(f"Máximo: {comp['Actual'].idxmax()} -> {comp['Con candidatas'].idxmax()} | "
      f"mínimo: {comp['Actual'].idxmin()} -> {comp['Con candidatas'].idxmin()}")
comp.loc[["2019T2", *PANDEMIA, *VALLE, "2024T1", "2025T1", termo.index[-1]]].round(1)
''')

md("""
## 11. Exportar

Guarda la serie completa (indicadores en %, percentiles, dimensiones y termómetro) en
Drive: `carga_EPH/resultados/termometro_EPH.csv` (separador `;`, decimal `,` para abrir
directo en Excel en español).
""")

code(r'''
os.makedirs(RESULTADOS_DIR, exist_ok=True)
salida = pd.concat([
    ind.add_prefix("pct_"),
    norm.add_prefix("perc_"),
    termo,
], axis=1)
salida.index.name = "trimestre"
path = os.path.join(RESULTADOS_DIR, "termometro_EPH.csv")
salida.to_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
print("Guardado:", path, "|", salida.shape)
''')

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.10"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("ok", OUT, len(cells), "celdas")
