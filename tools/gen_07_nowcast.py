"""Genera notebooks/07_nowcast.ipynb.

El notebook 07 NO se edita a mano: se edita este script y se regenera.

Uso (desde la raíz del repo):
    python tools/gen_07_nowcast.py                 # escribe notebooks/07_nowcast.ipynb
    python tools/gen_07_nowcast.py otra/ruta.ipynb

Cada llamada a md()/code() agrega una celda en orden. La lógica vive en src/nowcast.py; el
notebook la usa y muestra los resultados. Ver docs/TECNICO.md §7.
"""
import json
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "notebooks", "07_nowcast.ipynb")

cells = []


def md(s):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)})


def code(s):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": s.strip("\n").splitlines(keepends=True)})


md(r"""
# 07 - Nowcast del termómetro: dimensión D (ingresos reales)

La EPH sale **~85 días después** de cerrar cada trimestre. Este notebook **proyecta** el
termómetro del notebook 06 con datos que se publican antes, lo **corrige** cuando llega la EPH
oficial y **registra cada versión** para medir cuánto erró. Es un **prototipo: por ahora solo
proyecta la dimensión D** (ingresos reales); A, B y C se sumarán con el mismo esquema.

**Método: microsimulación sobre la última EPH.** Se toman los microdatos del último trimestre
publicado y se actualiza el ingreso de cada persona con el índice mensual que le corresponde:

| Ingreso (variables EPH) | Se actualiza con | Rezago aprox. |
|---|---|---|
| Asalariados registrados del sector privado (`P21`, `TOT_P12`) | Índice de salarios INDEC, registrado privado | ~45 días |
| Asalariados registrados del sector público | Índice de salarios, registrado público | ~45 días |
| Asalariados no registrados, cuentapropistas y patrones | Índice de salarios, no registrado (realineado 6 meses; los meses sin dato siguen al registrado privado) | ~7 meses |
| Jubilaciones y pensiones + aguinaldo (`V2`, `V21`) | Haber mínimo (movilidad); hasta 5% sobre mínimo + bono: mínimo + bono | se anuncia antes |
| AUH, AUE, Tarjeta Alimentar (`V5`) | Monto de la AUH | se anuncia antes |
| Resto de los ingresos no laborales | IPC (constantes en términos reales) | ~14 días |

Con los ingresos actualizados se recalculan los dos indicadores de D **con las mismas
definiciones del 06** (ingreso laboral real y personas con ingreso per cápita real bajo), se
corrige la estacionalidad (el aguinaldo cae en el T1 y el T3) con los factores del 06 y se
normalizan con los percentiles del 06. Los meses que todavía no se publicaron se completan con la
tendencia de los últimos 3 meses.

**Cómo se corrige cuando sale la EPH:** el trimestre proyectado pasa a oficial, los percentiles
se recalculan (como en el 06) y la proyección siguiente parte de esa base nueva. Cada corrida se
guarda en el **registro de versiones** (sección 7): cuando sale la EPH se completa el valor
oficial y el error de cada versión.

**Qué tan bien anda (sección 5):** se simula el pasado en *pseudo tiempo real* (para cada
trimestre 2019-2026 se proyecta solo con lo que estaba publicado en cada fecha) y se compara con
la EPH y con no proyectar (repetir el último D publicado).

**Límites:** la microsimulación mueve salarios, haberes y precios, pero no la composición del
empleo (quién perdió o consiguió trabajo): eso lo captan las dimensiones A y B. Las fechas de
publicación de cada serie son aproximadas. El backtest usa las series en su versión actual (no
las versiones de cada momento; los índices de salarios se revisan poco).

**Contenido:** 1-2 setup y series · 3 microdatos e indicadores oficiales (control contra el 06) ·
4 qué mueve la proyección · 5 backtest · 6 nowcast hoy · 7 registro de versiones · 8 exportar ·
Anexo: decisiones y pruebas.

*Versión del prototipo: D-microsim v1 (2026-10).*
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

# Carpeta de resultados en Drive (la misma del 06; el nowcast va en resultados/nowcast/)
RESULTADOS_DIR = "/content/drive/MyDrive/carga_EPH/resultados"
''')

code(r'''
import importlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import src.nowcast as nc
importlib.reload(nc)  # Colab reutiliza sesiones: tomar la versión recién bajada del repo
from src.data_loader import load_panel

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
COLOR_D = "#eda100"  # el color de la dimensión D en el 06
TINTA, GRIS = "#0b0b0b", "#8a8984"
COLOR_K = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}  # trimestres entre la base y el objetivo

NOWCAST_DIR = os.path.join(RESULTADOS_DIR, "nowcast")
GRAFICOS_DIR = os.path.join(NOWCAST_DIR, "graficos")

def guardar_figura(fig, nombre):
    """Guarda el gráfico en carga_EPH/resultados/nowcast/graficos/<nombre>.png (antes de plt.show)."""
    os.makedirs(GRAFICOS_DIR, exist_ok=True)
    fig.savefig(os.path.join(GRAFICOS_DIR, f"{nombre}.png"), dpi=150, bbox_inches="tight", facecolor="white")

def f1(x, signo=False):
    """Número con 1 decimal y coma decimal (signo explícito opcional)."""
    return (f"{x:+.1f}" if signo else f"{x:.1f}").replace(".", ",").replace("-", "−")

FECHA_CORRIDA = pd.Timestamp.today().normalize()  # fecha de la proyección (se puede fijar a mano)
VERSION = "D-microsim v1"
CORREGIR_DERIVA = False  # corrección por sesgo de los errores pasados: no mejoró el backtest (sección 5)
print(f"Proyección al {FECHA_CORRIDA:%d/%m/%Y} | versión {VERSION}")
''')

md("""
## 2. Series de alta frecuencia

Se bajan de la API de Series de Tiempo (datos.gob.ar), que falla de forma intermitente: se
reintenta y, si no responde, se usa la copia `data/series_nowcast.csv` del repo. El bono
previsional no tiene serie pública: se carga a mano en `data/bono_previsional.csv` (la misma tabla
que el proyecto IPC de jubilados). Todas las series quedan fechadas en el **mes de referencia**:
el índice de salarios no registrado de la API se corre 6 meses hacia atrás.
""")

code(r'''
series, origen = nc.cargar_series(os.path.join(REPO_DIR, "data", "series_nowcast.csv"),
                                  os.path.join(REPO_DIR, "data", "bono_previsional.csv"))
tabla_series = pd.DataFrame({
    "Serie": [nc.NOMBRE_INDICE.get(n, "Bono previsional") for n in series],
    "Origen": [origen[n] for n in series],
    "Desde": [str(s.index[0]) for s in series.values()],
    "Último mes con dato": [str(s.index[-1]) for s in series.values()],
}, index=list(series))
display(tabla_series)
''')

md("""
## 3. Microdatos e indicadores oficiales

Se prepara cada trimestre de la EPH para microsimular (ingresos de cada hogar separados según el
índice con que se actualizan) y se calculan los indicadores oficiales de D. **Control:** tienen que
coincidir con los del 06 (`termometro_EPH.csv` en `carga_EPH/resultados/`, si ya se corrió).
""")

code(r'''
bases, oficiales, UMBRAL = nc.cargar_bases(load_panel, PROCESSED_DIR, series)
ULTIMO = oficiales.index[-1]
D_rt = nc.D_tiempo_real(oficiales)  # D de cada trimestre tal como se publicó (cuando era el último)
D_hoy = nc.dimension_D(oficiales)   # D con toda la historia (lo que muestra hoy el 06)
print(f"{len(bases)} trimestres | último con EPH: {ULTIMO} | umbral de ingreso bajo ${UMBRAL:,.0f} de dic-2016".replace(",", "."))

csv06 = os.path.join(RESULTADOS_DIR, "termometro_EPH.csv")
if os.path.exists(csv06):
    d06 = pd.read_csv(csv06, sep=";", index_col=0, decimal=",")
    comunes = oficiales.index.intersection(d06.index)
    D_06 = nc.dimension_D(oficiales.loc[:d06.index[-1]])
    dif = max((oficiales.loc[comunes, nc.IND_LABORAL] - d06.loc[comunes, "pesos_" + nc.IND_LABORAL]).abs().max(),
              (oficiales.loc[comunes, nc.IND_BAJO] - d06.loc[comunes, "pct_" + nc.IND_BAJO]).abs().max(),
              (D_06[comunes] - d06.loc[comunes, nc.DIM_D]).abs().max())
    print(("✓ Indicadores y dimensión D idénticos a los del 06" if dif < 1e-6 else
           f"⚠ Diferencia de {dif:.4f} con el CSV del 06: ¿se corrió el 06 con los mismos trimestres?")
          + f" ({len(comunes)} trimestres comparados)")
else:
    print("(No está el CSV del 06 en", RESULTADOS_DIR, "-> correr el 06 para hacer el control)")
display(pd.concat([oficiales, D_hoy.rename(nc.DIM_D)], axis=1).tail(6).round(1))
''')

md("""
## 4. Qué mueve la proyección

Variación de cada índice entre los meses de referencia de la última EPH y los del trimestre que se
proyecta (el más lejano), y cuántos de esos meses todavía no tienen dato publicado (se estiman con
la tendencia). Si los salarios le ganan al IPC, el ingreso laboral real sube y baja la proporción
de personas con ingreso bajo.
""")

code(r'''
HOY_Q = nc.trimestre_de(FECHA_CORRIDA)
OBJ_HOY = nc.rango(nc.desplazar(ULTIMO, 1), HOY_Q) if HOY_Q > ULTIMO else []
if OBJ_HOY:
    var = nc.variaciones(ULTIMO, OBJ_HOY[-1], series)
    print(f"De {ULTIMO} a {OBJ_HOY[-1]} (meses de referencia {nc.meses_ref(ULTIMO)[0]} → {nc.meses_ref(OBJ_HOY[-1])[-1]}):")
    display(var.assign(**{"Variación %": var["Variación %"].astype(float).round(1)}))
else:
    print("La EPH del trimestre en curso ya está publicada: no hay nada que proyectar.")
''')

md("""
## 5. Backtest en pseudo tiempo real

Para cada trimestre de 2019 a hoy se proyecta D **como si se estuviera en una fecha dada**, con
solo las series publicadas hasta ese día, y se compara con el D que mostró el 06 cuando salió esa
EPH. La grilla combina:

- **k**: trimestres entre la EPH usada como base y el que se proyecta (k = 1 es lo normal; k = 2 o
  3 si la EPH se demora, como ahora).
- **días**: fecha de la proyección respecto del cierre del trimestre proyectado (−75 = recién
  empezado; +80 = justo antes de que salga su EPH).

Benchmark: **repetir el último D publicado** (lo que se ve hoy sin proyección). Error = raíz del
error cuadrático medio (RMSE), sin los trimestres de la pandemia (2020T2-2021T1). Para los
indicadores, el benchmark es la **persistencia** (el valor de la base corregido por estacionalidad).
""")

code(r'''
OBJETIVOS = nc.rango("2019T1", ULTIMO)
bt = nc.backtest(bases, oficiales, series, UMBRAL, OBJETIVOS)
res = nc.resumir(bt)
tabla_bt = res.xs("estacional", level="metodo")[
    ["n", "D", "D_ultimo", "sesgo_D", "laboral_pct", "laboral_persist_pct", "bajo_pp", "bajo_persist_pp"]]
tabla_bt.columns = ["Trimestres", "D: error (pts)", "D: repetir el último (pts)", "D: sesgo (pts)",
                    "Ingreso laboral: error (%)", "Ingreso laboral: persistencia (%)",
                    "Ingreso bajo: error (pp)", "Ingreso bajo: persistencia (pp)"]
display(tabla_bt.round(1))

REF = nc.error_esperado(res, 1, 80, corregido=False)
r_ult = res.loc[(1, 80, "estacional"), "D_ultimo"]
print(f"Con la EPH del trimestre anterior y los datos de 80 días después del cierre, la proyección de D erra "
      f"{f1(REF['D'])} pts (RMSE) contra {f1(r_ult)} de repetir el último D publicado; el ingreso laboral real, "
      f"{f1(REF['laboral_pct'])}% (persistencia: {f1(res.loc[(1, 80, 'estacional'), 'laboral_persist_pct'])}%), y el % con "
      f"ingreso bajo, {f1(REF['bajo_pp'])} pp ({f1(res.loc[(1, 80, 'estacional'), 'bajo_persist_pp'])} pp).")
''')

md("""
**Alternativas probadas** (con la base del trimestre anterior, 80 días después del cierre):
partir del **mismo trimestre del año anterior** (misma estacionalidad, composición más vieja) y
**corregir el sesgo** con el promedio de los últimos 8 errores ya conocidos en cada fecha
(`CORREGIR_DERIVA`).
""")

code(r'''
bt_alt = nc.backtest(bases, oficiales, series, UMBRAL, OBJETIVOS, [nc.REF_DERIVA], metodos=nc.METODOS)
ra = nc.resumir(bt_alt).loc[nc.REF_DERIVA]
alternativas = pd.DataFrame({
    "D: error (pts)": [ra.loc["estacional", "D"], ra.loc["anual", "D"], ra.loc["estacional", "D_c"]],
    "Ingreso laboral: error (%)": [ra.loc["estacional", "laboral_pct"], ra.loc["anual", "laboral_pct"], ra.loc["estacional", "laboral_c_pct"]],
    "Ingreso bajo: error (pp)": [ra.loc["estacional", "bajo_pp"], ra.loc["anual", "bajo_pp"], ra.loc["estacional", "bajo_c_pp"]],
}, index=["Base = último trimestre (elegido)", "Base = mismo trimestre del año anterior", "Último trimestre + corrección de sesgo"])
display(alternativas.round(2))
''')

code(r'''
# Error de D según la fecha de la proyección
fig, ax = plt.subplots(figsize=(11, 5))
for k in (1, 2, 3):
    r = res.xs(("estacional", k), level=("metodo", "k"))
    ax.plot(r.index, r["D"], "-o", color=COLOR_K[k], lw=2, label=f"Proyección, base a {k} trimestre{'s' if k > 1 else ''}")
    ax.axhline(r["D_ultimo"].iloc[0], color=COLOR_K[k], lw=1.2, ls="--", alpha=0.8)
    ax.text(r.index.min(), r["D_ultimo"].iloc[0] + 0.4, f"repetir el último (k={k})", color=COLOR_K[k],
            fontsize=9, va="bottom")
ax.axvline(nc.DIAS_EPH, color=GRIS, lw=1)
ax.text(nc.DIAS_EPH + 2, ax.get_ylim()[1] * 0.95, "sale la EPH", color="#52514e", fontsize=9, va="top")
ax.set_xlabel("Días respecto del cierre del trimestre proyectado")
ax.set_ylabel("Error de D (RMSE, pts)")
ax.set_ylim(0, None)
ax.set_title("Error de la proyección de D: cuanto más cerca de la base y más datos, menor")
ax.legend(frameon=False, loc="lower left")
plt.tight_layout()
guardar_figura(fig, "nowcast_01_error_por_horizonte")
plt.show()
''')

code(r'''
# Proyección final (k = 1, 80 días) vs. D publicado y vs. repetir el último
b1 = bt[(bt["k"] == 1) & (bt["dias"] == 80) & (bt["metodo"] == "estacional")].set_index("trimestre")
x = np.arange(len(b1))
fig, ax = plt.subplots(figsize=(11, 5))
for i, q in enumerate(b1.index):
    if q in nc.PANDEMIA:
        ax.axvspan(i - 0.5, i + 0.5, color="#e4e3df", lw=0, zorder=0)
ax.plot(x, b1["D_of"], "-", color=COLOR_D, lw=2.5, label="D publicado (EPH)", zorder=3)
ax.plot(x, b1["D"], "o", mfc="white", mec=TINTA, mew=1.8, ms=7, label="Proyección (80 días después del cierre)", zorder=4)
ax.step(x, b1["D_ultimo"], where="mid", color=GRIS, lw=1.2, ls="--", label="Repetir el último publicado", zorder=2)
ax.set_xticks(x[::2], b1.index[::2], rotation=45, ha="right")
ax.set_ylim(0, 105)
ax.set_ylabel("Dimensión D (0 = mejor, 100 = peor)")
ax.set_title("Backtest: proyección de D vs. EPH (gris: pandemia, fuera del cálculo del error)")
ax.legend(frameon=False, loc="lower left")
plt.tight_layout()
guardar_figura(fig, "nowcast_02_backtest")
plt.show()
peor = b1.loc[~b1.index.isin(nc.PANDEMIA), "err_D"].abs().sort_values(ascending=False).head(3)
print("Mayores errores:", ", ".join(f"{q} ({f1(b1.loc[q, 'err_D'], True)} pts)" for q in peor.index))
''')

md("""
## 6. Nowcast hoy

Proyección de cada trimestre que todavía no tiene EPH, desde la última publicada hasta el
trimestre en curso. El intervalo es **±1,96 × el error del backtest** para el horizonte más
parecido (mismo k, días más cercanos): incluye el ruido muestral de la EPH que se va a publicar.
""")

code(r'''
deriva = nc.estimar_deriva(nc.errores_backtest(bt), ULTIMO) if CORREGIR_DERIVA else None
nowcast, filas_reg = {}, []
for q in OBJ_HOY:
    k = len(nc.rango(ULTIMO, q)) - 1
    dias = int((FECHA_CORRIDA - nc.fin_trimestre(q)).days)
    proy, D, datos_hasta = nc.proyectar(q, ULTIMO, bases, oficiales, series, UMBRAL, deriva=deriva)
    err = nc.error_esperado(res, k, dias, corregido=CORREGIR_DERIVA)
    filas_reg.append(nc.filas_registro(FECHA_CORRIDA, VERSION, q, ULTIMO, proy, D, err, datos_hasta))
    nowcast[q] = {"k": k, "Días al cierre": dias, "Horizonte del backtest": f"k={int(err['k'])}, {int(err['dias']):+d} días"}
nuevas = pd.concat(filas_reg, ignore_index=True) if filas_reg else pd.DataFrame(columns=nc.COLUMNAS_REGISTRO)

if OBJ_HOY:
    tabla_hoy = pd.DataFrame(nowcast).T
    for ind, fmt in [(nc.DIM_D, "{:.0f}"), (nc.IND_LABORAL, "${:,.0f}"), (nc.IND_BAJO, "{:.1f}%")]:
        sub = nuevas[nuevas["indicador"] == ind].set_index("trimestre")
        tabla_hoy[ind] = [fmt.format(sub.loc[q, "valor"]).replace(",", ".") + " (" + fmt.format(sub.loc[q, "ic_inf"]).replace(",", ".")
                          + " a " + fmt.format(sub.loc[q, "ic_sup"]).replace(",", ".") + ")" for q in tabla_hoy.index]
    display(tabla_hoy)
    sd = nuevas[nuevas["indicador"] == nc.DIM_D].set_index("trimestre")
    q0 = OBJ_HOY[0]
    print(f"Lectura: con la EPH de {ULTIMO} (D = {f1(D_hoy[ULTIMO])}) y los índices hasta hoy, D de {q0} se proyecta en "
          f"{f1(sd.loc[q0, 'valor'])} (IC 95% {f1(sd.loc[q0, 'ic_inf'])} a {f1(sd.loc[q0, 'ic_sup'])})"
          + (f" y el de {OBJ_HOY[-1]}, en {f1(sd.loc[OBJ_HOY[-1], 'valor'])} (IC 95% {f1(sd.loc[OBJ_HOY[-1], 'ic_inf'])} a "
             f"{f1(sd.loc[OBJ_HOY[-1], 'ic_sup'])})" if len(OBJ_HOY) > 1 else "") + ".")
''')

code(r'''
if OBJ_HOY:
    hist = pd.concat([oficiales, D_hoy.rename(nc.DIM_D)], axis=1)
    etiquetas = list(hist.index) + OBJ_HOY
    x_of, x_nc = np.arange(len(hist)), np.arange(len(hist), len(etiquetas))
    ticks = np.arange(len(etiquetas))[::-1][::4][::-1]  # uno cada 4 trimestres, terminando en el último
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    paneles = [(nc.DIM_D, "Dimensión D (0 = mejor, 100 = peor)"),
               (nc.IND_LABORAL, "Ingreso laboral real ($ de dic-2016, media geom.)"),
               (nc.IND_BAJO, "Personas con ingreso per cápita real bajo (%)")]
    for ax, (ind, titulo) in zip(axes, paneles):
        sub = nuevas[nuevas["indicador"] == ind].set_index("trimestre").loc[OBJ_HOY]
        ax.plot(x_of, hist[ind], "-", color=COLOR_D, lw=2, label="EPH")
        ax.plot(np.r_[x_of[-1], x_nc], np.r_[hist[ind].iloc[-1], sub["valor"]], "--", color=TINTA, lw=1.2)
        ax.fill_between(x_nc, sub["ic_inf"], sub["ic_sup"], color=COLOR_D, alpha=0.18, lw=0, label="IC 95%")
        ax.plot(x_nc, sub["valor"], "o", mfc="white", mec=TINTA, mew=1.8, ms=7, label="Proyección")
        ax.set_xticks(ticks, [etiquetas[i] for i in ticks], rotation=45, ha="right")
        ax.set_title(titulo, fontsize=10.5)
        if ind == nc.DIM_D:
            ax.set_ylim(0, 105)
    axes[0].legend(frameon=False, loc="upper left", fontsize=9)
    fig.suptitle(f"Nowcast de la dimensión D al {FECHA_CORRIDA:%d/%m/%Y} (base: EPH {ULTIMO})", color=TINTA)
    plt.tight_layout()
    guardar_figura(fig, "nowcast_03_hoy")
    plt.show()
''')

md("""
## 7. Registro de versiones

Cada corrida agrega sus proyecciones a `carga_EPH/resultados/nowcast/registro_versiones.csv`
(una corrida del mismo día y versión reemplaza a la anterior). Cuando la EPH de un trimestre se
publica, se completan `oficial` y `error` (proyectado − oficial) de todas sus versiones: así se
mide el error real, por días al cierre, y se recalibran los intervalos. Columnas:
`fecha_corrida`, `version`, `trimestre`, `dias_al_cierre`, `base_EPH`, `indicador`, `valor`,
`ic_inf`, `ic_sup`, `datos_hasta` (último mes con dato de cada serie), `oficial`, `error`.
""")

code(r'''
REGISTRO = os.path.join(NOWCAST_DIR, "registro_versiones.csv")
reg = nc.registrar(REGISTRO, nuevas)
reg = nc.conciliar(reg, oficiales, D_rt)
reg.to_csv(REGISTRO, index=False)
print(f"Registro: {len(reg)} filas, {reg['fecha_corrida'].nunique()} corridas, trimestres {', '.join(sorted(reg['trimestre'].unique()))}")
con_oficial = reg[reg["oficial"].notna()]
if len(con_oficial):
    print("Proyecciones que ya tienen su EPH (error = proyectado − oficial):")
    display(con_oficial.groupby(["indicador", "trimestre"])["error"].agg(["count", "mean", "last"]).round(2))
else:
    print(f"Todavía ninguna proyección tiene su EPH: el primer control será cuando se publique {OBJ_HOY[0] if OBJ_HOY else 'la próxima'}.")
display(reg[reg["indicador"] == nc.DIM_D].drop(columns=["datos_hasta"]).tail(9).round(1))
''')

code(r'''
# Evolución de las versiones de D de cada trimestre (se completa corrida a corrida)
rd = reg[reg["indicador"] == nc.DIM_D].copy()
rd["fecha_corrida"] = pd.to_datetime(rd["fecha_corrida"])
fig, ax = plt.subplots(figsize=(11, 4.5))
for i, (q, g) in enumerate(rd.groupby("trimestre")):
    col = list(COLOR_K.values())[i % 3]
    ax.fill_between(g["fecha_corrida"], g["ic_inf"], g["ic_sup"], color=col, alpha=0.12, lw=0)
    ax.plot(g["fecha_corrida"], g["valor"], "-o", color=col, lw=1.8, ms=6, label=f"{q} (proyección)")
    if g["oficial"].notna().any():
        ax.axhline(g["oficial"].dropna().iloc[-1], color=col, ls="--", lw=1.2, label=f"{q} (EPH)")
ax.set_ylim(0, 105)
ax.set_xlim(rd["fecha_corrida"].min() - pd.Timedelta(days=20), rd["fecha_corrida"].max() + pd.Timedelta(days=20))
ax.set_ylabel("Dimensión D")
ax.set_title("Versiones de la proyección de D por fecha de corrida")
ax.legend(frameon=False, fontsize=9, ncol=3)
fig.autofmt_xdate()
plt.tight_layout()
guardar_figura(fig, "nowcast_04_versiones")
plt.show()
''')

md("""
## 8. Exportar

En `carga_EPH/resultados/nowcast/` (separador `;` y decimal `,`, como el 06):
`nowcast_D.csv` (proyección de esta corrida), `backtest_D.csv` (cada proyección del backtest) y
`backtest_D_resumen.csv` (errores por horizonte). El registro de versiones usa formato estándar
(coma y punto) porque lo relee el notebook. Los gráficos `nowcast_01` … `nowcast_04` quedan en
`nowcast/graficos/`.
""")

code(r'''
os.makedirs(NOWCAST_DIR, exist_ok=True)
opts = dict(sep=";", decimal=",", encoding="utf-8-sig", index=False)
archivos = {"nowcast_D.csv": nuevas, "backtest_D.csv": bt, "backtest_D_resumen.csv": res.reset_index()}
for nombre, df in archivos.items():
    path = os.path.join(NOWCAST_DIR, nombre)
    df.to_csv(path, **opts)
    print("Guardado:", path)
graficos = sorted(os.listdir(GRAFICOS_DIR)) if os.path.isdir(GRAFICOS_DIR) else []
print(f"Gráficos en {GRAFICOS_DIR}: " + (", ".join(graficos) if graficos else "ninguno"))
''')

md(r"""
## Anexo: decisiones y pruebas (2026-10-20)

- **Índice de salarios no registrado:** la API lo fecha en el mes de publicación. Contra el `P21`
  nominal de los asalariados no registrados de la EPH, la variación interanual correlaciona 0,874
  sin desfase, 0,982 corrido 5 meses (el rezago que informa el INDEC) y 0,988 corrido 6 (la EPH
  fecha los ingresos en el mes anterior a la entrevista). Se usa 6 (`SERIES` en `src/nowcast.py`).
  En el backtest, 5 o 7 cambian el error de D en menos de 0,7 pts.
- **Índice por grupo:** registrado privado para asalariados registrados privados (RMSE de la
  variación i.a. del `P21` 4,7%), registrado público para el sector público, no registrado para
  no registrados (4,8%), cuentapropistas y patrones (8,3% y 12,5%: es el que mejor los sigue).
  Usar el registrado privado para todos empeora el backtest. Los meses sin dato del no registrado
  siguen al registrado privado mientras éste tiene dato y después su propia tendencia: usar solo la
  tendencia propia da resultados mixtos (mejor D a k = 2, peor ingreso laboral) y seguir también
  la tendencia estimada del registrado privado empeora (k = 2 a −75 días: 14,8 → 17,8 pts).
- **Base:** partir del mismo trimestre del año anterior erra el doble que partir del último
  trimestre con corrección estacional (sección 5).
- **Sesgo:** la proyección tiende a ser algo pesimista (los ingresos de la EPH crecen ~0,3-0,5%
  por trimestre más que los índices) y el sesgo crece con k. Corregirlo con los errores pasados
  (ventanas de 4, 8, 12 o todos) baja el sesgo pero no el error cuadrático (empeora el del ingreso
  laboral), así que queda desactivado (`CORREGIR_DERIVA`). Revisarlo cuando el registro tenga
  errores reales.
- **Ruido del percentil:** con ~40 trimestres, un error de 3% en el ingreso laboral puede mover D
  10 pts si cae en una zona densa de la historia. Los indicadores en sus unidades se proyectan
  mejor de lo que sugiere el error de D (sección 5).
""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print(f"Escrito {os.path.normpath(OUT)} ({len(cells)} celdas)")
