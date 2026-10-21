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
# 07 - Nowcast del termómetro de los hogares

La EPH sale **~85 días después** de cerrar cada trimestre. Este notebook **proyecta** el
termómetro del notebook 06 (las cuatro dimensiones) con datos que se publican antes, lo
**corrige** cuando llega la EPH oficial y **registra cada versión** para medir cuánto erró.

**D. Ingresos reales: microsimulación sobre la última EPH.** Se toman los microdatos del último
trimestre publicado y se actualiza el ingreso de cada persona con el índice mensual que le
corresponde, y se recalculan los indicadores de D con las mismas fórmulas del 06:

| Ingreso (variables EPH) | Se actualiza con | Rezago aprox. |
|---|---|---|
| Asalariados registrados del sector privado (`P21`, `TOT_P12`) | Índice de salarios INDEC, registrado privado | ~45 días |
| Asalariados registrados del sector público | Índice de salarios, registrado público | ~45 días |
| Asalariados no registrados, cuentapropistas y patrones | Índice de salarios, no registrado (realineado 6 meses; los meses sin dato siguen al registrado privado) | ~7 meses |
| Jubilaciones y pensiones + aguinaldo (`V2`, `V21`) | Haber mínimo (movilidad); hasta 5% sobre mínimo + bono: mínimo + bono | se anuncia antes |
| AUH, AUE, Tarjeta Alimentar (`V5`) | Monto de la AUH | se anuncia antes |
| Resto de los ingresos no laborales | IPC (constantes en términos reales) | ~14 días |

**A, B y C: ecuaciones puente.** Cada indicador de empleo, calidad del empleo y estrés de los
hogares (desestacionalizado) cambia de un trimestre al siguiente en proporción al cambio de tres
series mensuales:

| Serie | Qué capta | Rezago aprox. |
|---|---|---|
| EMAE desestacionalizado (INDEC) | actividad | ~55 días |
| Asalariados registrados del SIPA (privados + públicos + casas particulares, sin estacionalidad) | empleo formal | ~100 días |
| Confianza del consumidor UTDT, bienes durables e inmuebles | situación y expectativas de los hogares | sale en el mismo mes |

Los coeficientes se estiman, para cada indicador, con la historia disponible hasta la última EPH
(sin la pandemia) y después se suma la estacionalidad del indicador. Si las series no se mueven,
la proyección es la persistencia (el último valor, corregido por estacionalidad).

Los 15 indicadores proyectados se agregan a la serie oficial y pasan por **la misma
normalización del 06** (percentiles históricos, promedio por dimensión y de las cuatro
dimensiones). Los meses que todavía no se publicaron se completan con la tendencia de los
últimos 3 meses (la confianza del consumidor se mantiene constante).

**Cómo se corrige cuando sale la EPH:** el trimestre proyectado pasa a oficial, los percentiles
se recalculan (como en el 06), los coeficientes se reestiman con una observación más y la
proyección siguiente parte de esa base. Cada corrida se guarda en el **registro de versiones**
(sección 8): cuando sale la EPH se completa el valor oficial y el error de cada versión.

**Qué tan bien anda (sección 5):** se simula el pasado en *pseudo tiempo real* (para cada
trimestre 2019-2026 se proyecta solo con lo que estaba publicado en cada fecha) y se compara con
la EPH y con no proyectar (repetir el último termómetro publicado). La **sección 7** chequea la
robustez de ese resultado en cada corrida (subperíodos, calibración de los intervalos, versiones y
dependencia de cada predictor).

**Límites:** el error de la proyección incluye el ruido muestral de la EPH que se va a publicar
(~3,6 pts de termómetro): no puede bajar de ahí. A un trimestre de la base, parte de la mejora del
termómetro en el backtest viene de errores que se compensan entre dimensiones (ver el anexo). La microsimulación de D no capta los cambios de
composición del empleo; B (calidad del empleo) y C (estrés de los hogares) casi no se pueden
anticipar con las series disponibles (sección 5). Las fechas de publicación de cada serie son
aproximadas y el backtest usa las series en su versión actual, no las de cada momento.

**Contenido:** 1-2 setup y series · 3 indicadores oficiales (control contra el 06) · 4 qué mueve
la proyección · 5 backtest · 6 nowcast hoy · 7 robustez · 8 registro de versiones · 9 exportar ·
Anexo: decisiones y pruebas.

**Requisito:** correr antes el 06 (el 07 toma de su CSV los indicadores de A, B y C).

*Versión: termómetro v1 (2026-10): D por microsimulación, A, B y C por ecuaciones puente.*
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
# Mismos colores que el 06: uno por dimensión + tinta para el termómetro
COLOR_DIM = {"A. Cantidad de empleo": "#2a78d6", "B. Calidad del empleo": "#eb6834",
             "C. Estrés de los hogares": "#1baf7a", "D. Ingresos reales": "#eda100"}
TINTA, GRIS = "#0b0b0b", "#8a8984"
COLOR_K = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}  # trimestres entre la base y el objetivo
FRANJAS = [(0, 33, "#0ca30c"), (33, 66, "#fab219"), (66, 100, "#d03b3b")]

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
VERSION = "termómetro v1"
SERIES_T = [nc.TERMO] + list(nc.DIMENSIONES)  # termómetro y dimensiones
print(f"Proyección al {FECHA_CORRIDA:%d/%m/%Y} | versión {VERSION}")
''')

md("""
## 2. Series de alta frecuencia

Se bajan de la API de Series de Tiempo (datos.gob.ar), que falla de forma intermitente: se
reintenta, después se baja el CSV completo de la distribución de la serie y, si tampoco responde,
se usa la copia `data/series_nowcast.csv` del repo. El bono previsional no tiene serie pública:
se carga a mano en `data/bono_previsional.csv` (la misma tabla que el proyecto IPC de jubilados).
Todas las series quedan fechadas en el **mes de referencia**: el índice de salarios no registrado
de la API se corre 6 meses hacia atrás.
""")

code(r'''
series, origen = nc.cargar_series(os.path.join(REPO_DIR, "data", "series_nowcast.csv"),
                                  os.path.join(REPO_DIR, "data", "bono_previsional.csv"))
nombres = {**nc.NOMBRE_INDICE, **nc.NOMBRE_PREDICTOR, "bono": "Bono previsional", "sipa_priv": "SIPA asalariados privados",
           "sipa_pub": "SIPA asalariados públicos", "sipa_casas": "SIPA casas particulares",
           "eil": "Encuesta de Indicadores Laborales (no se usa)", "icc": "Confianza del consumidor: general (no se usa)"}
tabla_series = pd.DataFrame({
    "Serie": [nombres.get(n, n) for n in series],
    "Usada en": ["D" if n in nc.NOMBRE_INDICE or n == "bono" else "A, B, C" for n in series],
    "Origen": [origen[n] for n in series],
    "Último mes con dato": [str(s.index[-1]) for s in series.values()],
}, index=list(series))
display(tabla_series)
''')

md("""
## 3. Indicadores oficiales

Se preparan los microdatos de cada trimestre para microsimular D (ingresos de cada hogar separados
según el índice con que se actualizan) y se recalculan sus dos indicadores; los de A, B y C se
toman del CSV del 06. **Control:** los indicadores de D, las dimensiones y el termómetro tienen que
coincidir con los del 06.
""")

code(r'''
csv06 = os.path.join(RESULTADOS_DIR, "termometro_EPH.csv")
if not os.path.exists(csv06):
    raise FileNotFoundError(f"Falta {csv06}: correr antes el notebook 06 (el 07 toma de ahí A, B y C)")
bases, oficiales_D, UMBRAL = nc.cargar_bases(load_panel, PROCESSED_DIR, series)
oficiales = nc.leer_oficiales(csv06, oficiales_D)   # los 15 indicadores, trimestres del 06
ULTIMO = oficiales.index[-1]
T_rt = nc.termometro_tiempo_real(oficiales)  # tal como se publicó cada trimestre (cuando era el último)
T_hoy = nc.termometro(oficiales)             # con toda la historia (lo que muestra hoy el 06)
print(f"{len(oficiales)} trimestres | último con EPH: {ULTIMO} | umbral de ingreso bajo ${UMBRAL:,.0f} de dic-2016".replace(",", "."))
if oficiales_D.index[-1] > ULTIMO:
    print(f"⚠ Hay microdatos de {oficiales_D.index[-1]} que el CSV del 06 no tiene: correr el 06 y después el 07")

d06 = pd.read_csv(csv06, sep=";", index_col=0, decimal=",")
c = oficiales.index
dif = max((oficiales_D.loc[c, nc.IND_LABORAL] - d06.loc[c, "pesos_" + nc.IND_LABORAL]).abs().max(),
          (oficiales_D.loc[c, nc.IND_BAJO] - d06.loc[c, "pct_" + nc.IND_BAJO]).abs().max(),
          (T_hoy[SERIES_T] - d06.loc[c, SERIES_T]).abs().max().max())
print(("✓ Indicadores de D, dimensiones y termómetro idénticos a los del 06" if dif < 1e-6 else
       f"⚠ Diferencia de {dif:.4f} con el CSV del 06") + f" ({len(c)} trimestres)")
display(T_hoy.tail(6).round(1))
''')

md("""
## 4. Qué mueve la proyección

Cambio de cada serie entre la última EPH y el trimestre que se proyecta (el más lejano), y cuántos
de sus meses todavía no tienen dato publicado (se estiman). **D:** si los salarios y haberes le
ganan al IPC, sube el ingreso real. **A, B y C:** más actividad, más empleo registrado y más
confianza mejoran el empleo y bajan el estrés de los hogares.
""")

code(r'''
HOY_Q = nc.trimestre_de(FECHA_CORRIDA)
OBJ_HOY = nc.rango(nc.desplazar(ULTIMO, 1), HOY_Q) if HOY_Q > ULTIMO else []
if OBJ_HOY:
    q_fin = OBJ_HOY[-1]
    var = nc.variaciones(ULTIMO, q_fin, series)
    print(f"D: de {ULTIMO} a {q_fin} (meses de referencia {nc.meses_ref(ULTIMO)[0]} → {nc.meses_ref(q_fin)[-1]}):")
    display(var.assign(**{"Variación %": var["Variación %"].astype(float).round(1)}))
    print(f"A, B y C: de {ULTIMO} a {q_fin} (promedio de los meses del trimestre):")
    display(nc.variaciones_abc(ULTIMO, q_fin, series))
else:
    print("La EPH del trimestre en curso ya está publicada: no hay nada que proyectar.")
''')

md("""
## 5. Backtest en pseudo tiempo real

Para cada trimestre de 2019 a hoy se proyecta el termómetro **como si se estuviera en una fecha
dada**, con solo las series publicadas hasta ese día (y los coeficientes estimados con la historia
de ese momento), y se compara con lo que mostró el 06 cuando salió esa EPH. La grilla combina:

- **k**: trimestres entre la EPH usada como base y el que se proyecta (k = 1 es lo normal; k = 2 o
  3 si la EPH se demora, como en octubre de 2026).
- **días**: fecha de la proyección respecto del cierre del trimestre proyectado (−75 = recién
  empezado; +80 = justo antes de que salga su EPH).

Benchmark: **repetir el último termómetro publicado** (lo que se ve sin proyección); para los
indicadores, la **persistencia** (el último valor corregido por estacionalidad). Error = raíz del
error cuadrático medio (RMSE), sin los trimestres de la pandemia (2020T2-2021T1). Tarda ~1-3 minutos.
""")

code(r'''
OBJETIVOS = nc.rango("2019T1", ULTIMO)
bt = nc.backtest_termometro(bases, oficiales, series, UMBRAL, OBJETIVOS)
res = nc.resumir_termometro(bt)
err = res["error"].unstack("serie")[SERIES_T]
tabla_bt = err.copy()
tabla_bt.insert(1, "Repetir el último termómetro", res.xs(nc.TERMO, level="serie")["ultimo"])
print("Error (RMSE, pts) por horizonte:")
display(tabla_bt.round(1))
r = res.loc[(1, 80)]
print(f"Con la EPH del trimestre anterior y los datos de 80 días después del cierre, el termómetro proyectado erra "
      f"{f1(r.loc[nc.TERMO, 'error'])} pts (RMSE) contra {f1(r.loc[nc.TERMO, 'ultimo'])} de repetir el último publicado "
      f"(el ruido muestral de la EPH es ~3,6). Por dimensión: " +
      ", ".join(f"{d[:1]} {f1(r.loc[d, 'error'])} ({f1(r.loc[d, 'ultimo'])})" for d in nc.DIMENSIONES) + ".")
''')

code(r'''
# Indicadores: proyección vs persistencia (k = 1, 80 días; % salvo el ingreso laboral, en $ de dic-2016)
ind = res.loc[(1, 80)].loc[list(oficiales.columns), ["error", "ultimo", "mejora_%"]]
ind.columns = ["Error de la proyección", "Error de la persistencia", "Mejora (%)"]
ind.insert(0, "Dimensión", [next(d for d, cs in nc.DIMENSIONES.items() if c in cs)[:1] for c in ind.index])
display(ind.round(2))
''')

md("""
**Alternativas probadas** (base = trimestre anterior, 80 días después del cierre): A, B y C con
**persistencia** (sin las ecuaciones puente); D partiendo del **mismo trimestre del año anterior**;
D con **corrección de sesgo** por los últimos 8 errores ya conocidos en cada fecha.
""")

code(r'''
bt_pers = nc.backtest_termometro(bases, oficiales, series, UMBRAL, OBJETIVOS, [nc.REF_DERIVA],
                                 predictores={c: [] for c in nc.IND_ABC})
rp = nc.resumir_termometro(bt_pers).loc[nc.REF_DERIVA, "error"]
bt_d = nc.backtest(bases, oficiales_D, series, UMBRAL, OBJETIVOS, [nc.REF_DERIVA], metodos=nc.METODOS)
rd = nc.resumir(bt_d).loc[nc.REF_DERIVA]
alternativas = pd.DataFrame([res.loc[nc.REF_DERIVA, "error"][SERIES_T], rp[SERIES_T]],
                            index=["Elegido (puente + microsimulación)", "A, B y C con persistencia"])
alternativas.loc["D desde el mismo trimestre del año anterior", nc.DIM_D] = rd.loc["anual", "D"]
alternativas.loc["D con corrección de sesgo", nc.DIM_D] = rd.loc["estacional", "D_c"]
display(alternativas.round(1))
''')

code(r'''
# Error del termómetro según la fecha de la proyección
fig, ax = plt.subplots(figsize=(11, 5))
for k in (1, 2, 3):
    rk = res.xs((k, nc.TERMO), level=("k", "serie"))
    ax.plot(rk.index, rk["error"], "-o", color=COLOR_K[k], lw=2, label=f"Proyección, base a {k} trimestre{'s' if k > 1 else ''}")
    ax.axhline(rk["ultimo"].iloc[0], color=COLOR_K[k], lw=1.2, ls="--", alpha=0.8)
    ax.text(rk.index.min(), rk["ultimo"].iloc[0] + 0.25, f"repetir el último (k={k})", color=COLOR_K[k],
            fontsize=9, va="bottom")
ax.axhline(3.6, color=GRIS, lw=1, ls=":")
ax.text(ax.get_xlim()[1], 3.6 - 0.25, "ruido muestral de la EPH ", color="#52514e", fontsize=9, ha="right", va="top")
ax.axvline(nc.DIAS_EPH, color=GRIS, lw=1)
ax.text(nc.DIAS_EPH + 2, 0.4, "sale la EPH", color="#52514e", fontsize=9, va="bottom")
ax.set_xlabel("Días respecto del cierre del trimestre proyectado")
ax.set_ylabel("Error del termómetro (RMSE, pts)")
ax.set_ylim(0, None)
ax.set_title("Error de la proyección del termómetro según la fecha y la distancia a la última EPH")
ax.legend(frameon=False, loc="lower left")
plt.tight_layout()
guardar_figura(fig, "nowcast_01_error_por_horizonte")
plt.show()
''')

code(r'''
# Proyección final (k = 1, 80 días) vs. termómetro publicado y vs. repetir el último
b1 = bt[(bt["k"] == 1) & (bt["dias"] == 80) & (bt["serie"] == nc.TERMO)].set_index("trimestre")
x = np.arange(len(b1))
fig, ax = plt.subplots(figsize=(11, 5))
for lo, hi, col in FRANJAS:
    ax.axhspan(lo, hi, color=col, alpha=0.06, lw=0, zorder=0)
for i, q in enumerate(b1.index):
    if q in nc.PANDEMIA:
        ax.axvspan(i - 0.5, i + 0.5, color="#e4e3df", lw=0, zorder=0)
ax.plot(x, b1["oficial"], "-", color=TINTA, lw=2.5, label="Termómetro publicado (EPH)", zorder=3)
ax.plot(x, b1["valor"], "o", mfc="white", mec=COLOR_DIM[nc.DIM_D], mew=2, ms=7,
        label="Proyección (80 días después del cierre)", zorder=4)
ax.step(x, b1["ultimo"], where="mid", color=GRIS, lw=1.2, ls="--", label="Repetir el último publicado", zorder=2)
ax.set_xticks(x[::2], b1.index[::2], rotation=45, ha="right")
ax.set_ylim(0, 100)
ax.set_ylabel("Termómetro (0 = mejor, 100 = peor)")
ax.set_title("Backtest: termómetro proyectado vs. EPH (gris: pandemia, fuera del cálculo del error)")
ax.legend(frameon=False, loc="lower left")
plt.tight_layout()
guardar_figura(fig, "nowcast_02_backtest")
plt.show()
peor = b1.loc[~b1.index.isin(nc.PANDEMIA), "error"].abs().sort_values(ascending=False).head(3)
print("Mayores errores:", ", ".join(f"{q} ({f1(b1.loc[q, 'error'], True)} pts)" for q in peor.index))
''')

md("""
## 6. Nowcast hoy

Proyección de cada trimestre que todavía no tiene EPH, desde la última publicada hasta el
trimestre en curso. El intervalo es **±1,96 × el error del backtest** de cada serie para el
horizonte más parecido (mismo k, días más cercanos): incluye el ruido muestral de la EPH.
""")

code(r'''
nowcast, filas_reg, proyecciones = {}, [], {}
for q in OBJ_HOY:
    k = len(nc.rango(ULTIMO, q)) - 1
    dias = int((FECHA_CORRIDA - nc.fin_trimestre(q)).days)
    proy, termo, datos_hasta = nc.proyectar_termometro(q, ULTIMO, bases, oficiales, series, UMBRAL)
    rmse, (k0, d0) = nc.error_esperado_serie(res, k, dias)
    filas_reg.append(nc.filas_registro(FECHA_CORRIDA, VERSION, q, ULTIMO, pd.concat([termo.loc[q], proy.loc[q]]),
                                       rmse, datos_hasta))
    proyecciones[q] = proy.loc[q]
    nowcast[q] = {"k": k, "Días al cierre": dias, "Horizonte del backtest": f"k={k0}, {d0:+d} días"}
nuevas = pd.concat(filas_reg, ignore_index=True) if filas_reg else pd.DataFrame(columns=nc.COLUMNAS_REGISTRO)

if OBJ_HOY:
    tabla_hoy = pd.DataFrame(nowcast).T
    sub = nuevas.set_index(["trimestre", "indicador"])
    for s in SERIES_T:
        tabla_hoy[s] = [f"{sub.loc[(q, s), 'valor']:.0f} ({sub.loc[(q, s), 'ic_inf']:.0f} a {sub.loc[(q, s), 'ic_sup']:.0f})"
                        for q in OBJ_HOY]
    display(tabla_hoy)
    print(f"Lectura (base: EPH de {ULTIMO}, termómetro {f1(T_hoy.loc[ULTIMO, nc.TERMO])}). Comparar contra el mismo "
          "trimestre del año anterior: las dimensiones A, B y C tienen estacionalidad (como en el 06).")
    for q in OBJ_HOY:
        v, q4 = sub.loc[(q, nc.TERMO)], nc.desplazar(q, -4)
        print(f"  {q}: {f1(v['valor'])} (IC 95% {f1(v['ic_inf'])} a {f1(v['ic_sup'])}) | {q4}: {f1(T_hoy.loc[q4, nc.TERMO])}"
              f" -> {f1(v['valor'] - T_hoy.loc[q4, nc.TERMO], True)} pts interanual")
    # Indicadores: último oficial y proyecciones
    tabla_ind = pd.concat([oficiales.loc[ULTIMO].rename(f"{ULTIMO} (EPH)"), pd.DataFrame(proyecciones)], axis=1)
    display(tabla_ind.round(1))
''')

md("""
**Evolución del termómetro y su proyección.** La serie de la EPH es la del 06, con su intervalo de
confianza muestral (banda gris) y la media móvil de 4 trimestres; los trimestres sin EPH
(fondo gris) muestran la proyección con su intervalo del 95% (error del backtest) y la media
móvil que resulta de sumarla.
""")

code(r'''
proy_t = nuevas[nuevas["indicador"] == nc.TERMO].set_index("trimestre").reindex(OBJ_HOY)
etiquetas = list(T_hoy.index) + OBJ_HOY
x_of, x_nc = np.arange(len(T_hoy)), np.arange(len(T_hoy), len(etiquetas))
serie_of = T_hoy[nc.TERMO]
ic_of = d06.loc[T_hoy.index, ["Termómetro IC inf", "Termómetro IC sup"]].astype(float)  # IC bootstrap del 06
mm = pd.concat([serie_of, proy_t["valor"]]).rolling(4).mean()  # media móvil 4T (con la proyección al final)
COLOR_PROY = "#2a78d6"

fig, ax = plt.subplots(figsize=(13, 5.8))
for (lo, hi, col), nombre in zip(FRANJAS, ["Templado", "Tibio", "Fiebre"]):
    ax.axhspan(lo, hi, color=col, alpha=0.08, lw=0, zorder=0)
    ax.text(len(etiquetas) - 0.3, (lo + hi) / 2, nombre, va="center", ha="left", color="#52514e")
ax.fill_between(x_of, ic_of.iloc[:, 0], ic_of.iloc[:, 1], color=GRIS, alpha=0.18, lw=0, label="IC 95% (muestra de la EPH)")
ax.plot(x_of, serie_of, color=GRIS, lw=1.5, marker="o", ms=4, label="Trimestral (EPH)")
ax.plot(x_of, mm.iloc[:len(x_of)], color=TINTA, lw=2.5, label="Media móvil 4T")
ax.annotate(f"{ULTIMO}: {f1(serie_of.iloc[-1])}", (x_of[-1], serie_of.iloc[-1]), xytext=(-6, 14),
            textcoords="offset points", ha="right", color=TINTA, fontsize=9)
if OBJ_HOY:
    ax.axvspan(x_nc[0] - 0.5, x_nc[-1] + 0.5, color="#e4e3df", alpha=0.7, lw=0, zorder=0)
    ax.text(x_nc.mean(), 98, "sin EPH", ha="center", va="top", color="#52514e", fontsize=9)
    ax.plot(np.r_[x_of[-1], x_nc], np.r_[serie_of.iloc[-1], proy_t["valor"]], ls=":", color=COLOR_PROY, lw=1.5)
    ax.plot(np.arange(len(x_of) - 1, len(etiquetas)), mm.iloc[len(x_of) - 1:], color=TINTA, lw=2.5, ls="--",
            label="Media móvil 4T con la proyección")
    ax.errorbar(x_nc, proy_t["valor"], yerr=[proy_t["valor"] - proy_t["ic_inf"], proy_t["ic_sup"] - proy_t["valor"]],
                fmt="o", color=COLOR_PROY, mfc="white", mew=2, ms=7, capsize=4, lw=1.5,
                label="Proyección (IC 95% del backtest)", zorder=5)
    for xi, (q, f) in zip(x_nc, proy_t.iterrows()):
        ax.annotate(f1(f["valor"]), (xi, f["ic_sup"]), xytext=(0, 4), textcoords="offset points", ha="center",
                    color=COLOR_PROY, fontsize=9)
ax.set_xticks(np.arange(len(etiquetas)), etiquetas, rotation=90, fontsize=8)
ax.set_xlim(-0.5, len(etiquetas) + 1.5)
ax.set_ylim(0, 100)
ax.set_ylabel("Termómetro (0 = mejor, 100 = peor)")
ax.set_title(f"Termómetro de la economía de los hogares: EPH hasta {ULTIMO}"
             + (f" y proyección al {FECHA_CORRIDA:%d/%m/%Y}" if OBJ_HOY else ""))
ax.legend(loc="upper left", frameon=False, fontsize=9)
plt.tight_layout()
guardar_figura(fig, "nowcast_05_evolucion")
plt.show()
''')

code(r'''
if OBJ_HOY:
    etiquetas = list(T_hoy.index) + OBJ_HOY
    x_of, x_nc = np.arange(len(T_hoy)), np.arange(len(T_hoy), len(etiquetas))
    ticks = np.arange(len(etiquetas))[::-1][::4][::-1]  # uno cada 4 trimestres, terminando en el último
    fig = plt.figure(figsize=(15, 6.5))
    gs = fig.add_gridspec(2, 4)
    paneles = [(fig.add_subplot(gs[:, :2]), nc.TERMO, TINTA)] + [
        (fig.add_subplot(gs[i // 2, 2 + i % 2]), d, COLOR_DIM[d]) for i, d in enumerate(nc.DIMENSIONES)]
    for ax, serie, col in paneles:
        sub = nuevas[nuevas["indicador"] == serie].set_index("trimestre").loc[OBJ_HOY]
        ax.plot(x_of, T_hoy[serie], "-", color=col, lw=2.2 if serie == nc.TERMO else 1.6, label="EPH")
        ax.plot(np.r_[x_of[-1], x_nc], np.r_[T_hoy[serie].iloc[-1], sub["valor"]], "--", color=col, lw=1.2)
        ax.fill_between(x_nc, sub["ic_inf"], sub["ic_sup"], color=col, alpha=0.15, lw=0, label="IC 95%")
        ax.plot(x_nc, sub["valor"], "o", mfc="white", mec=col, mew=1.8, ms=7 if serie == nc.TERMO else 5, label="Proyección")
        ax.set_ylim(0, 105)
        if serie == nc.TERMO:
            for lo, hi, c_ in FRANJAS:
                ax.axhspan(lo, hi, color=c_, alpha=0.06, lw=0, zorder=0)
            ax.set_xticks(ticks, [etiquetas[i] for i in ticks], rotation=45, ha="right")
            ax.legend(frameon=False, loc="upper left", fontsize=9)
            ax.set_title(f"Termómetro (0 = mejor, 100 = peor)", fontsize=11)
        else:
            ax.set_xticks(ticks[::2], [etiquetas[i] for i in ticks[::2]], rotation=45, ha="right", fontsize=8)
            ax.set_title(serie, fontsize=10)
    fig.suptitle(f"Nowcast del termómetro al {FECHA_CORRIDA:%d/%m/%Y} (base: EPH {ULTIMO})", color=TINTA)
    plt.tight_layout()
    guardar_figura(fig, "nowcast_03_hoy")
    plt.show()
''')

md("""
## 7. Robustez (se recalcula en cada corrida)

Chequeos sobre el backtest de la sección 5 (sin pandemia), para tres horizontes: EPH del
trimestre anterior (k = 1, 80 días después del cierre) y EPH demorada uno y dos trimestres:

- **Subperíodos:** ¿la ventaja sobre repetir el último se sostiene en 2019-2022 y en 2023-2026?
- **Calibración:** sesgo (y si es significativo), cuántas veces le gana a repetir el último, peor
  error y cobertura de los intervalos de 95%: con el error de toda la muestra y con el que se
  conocía en cada fecha (errores de trimestres ya publicados en la base de la proyección).
- **Versiones:** con el calendario habitual de la EPH, cuánto erra cada versión de un mismo
  trimestre, cuánto se revisa y si las revisiones lo acercan al oficial.
- **Dependencia de cada predictor de A, B y C:** backtest y nowcast de hoy sacando cada serie
  (recalcula el backtest tres veces más: tarda ~1-2 minutos).

Al final, una lectura automática con ✓ / ⚠ (umbrales en `nc.alertas_robustez`).
""")

code(r'''
rob_sub = nc.robustez_subperiodos(bt)
print("Error (RMSE, pts) por subperíodo:")
display(rob_sub.round(1))
rob_cal = nc.robustez_calibracion(bt)
print("Calibración del termómetro:")
display(rob_cal.round(1))
rob_conv, rob_fin = nc.convergencia(bt)
print("Versiones de un mismo trimestre (calendario habitual):")
display(rob_conv.round(1))
print(f"La última versión está más cerca del oficial que la primera en {rob_fin:.0f}% de los trimestres.")
''')

code(r'''
rob_dep = nc.dependencia_predictores(bases, oficiales, series, UMBRAL, OBJETIVOS, ULTIMO, OBJ_HOY, resumen_elegido=res)
print("Termómetro sacando cada predictor (backtest: RMSE en pts; hoy: valor proyectado):")
display(rob_dep.round(1))
alertas = nc.alertas_robustez(rob_sub, rob_cal, rob_conv, rob_dep)
print("\n".join(alertas))
''')

md("""
## 8. Registro de versiones

Cada corrida agrega sus proyecciones (termómetro, dimensiones y los 15 indicadores) a
`carga_EPH/resultados/nowcast/registro_versiones.csv`; una corrida del mismo día y versión
reemplaza a la anterior. Cuando la EPH de un trimestre se publica, se completan `oficial` y
`error` (proyectado − oficial) de todas sus versiones: así se mide el error real, por días al
cierre, y se recalibran los intervalos. Columnas: `fecha_corrida`, `version`, `trimestre`,
`dias_al_cierre`, `base_EPH`, `indicador`, `valor`, `ic_inf`, `ic_sup`, `datos_hasta` (último mes
con dato de cada serie), `oficial`, `error`. Las versiones `D-microsim v1` (oct-2026) solo tienen D.
""")

code(r'''
REGISTRO = os.path.join(NOWCAST_DIR, "registro_versiones.csv")
reg = nc.registrar(REGISTRO, nuevas)
reg = nc.conciliar(reg, oficiales, T_rt)
reg.to_csv(REGISTRO, index=False)
print(f"Registro: {len(reg)} filas, {reg['fecha_corrida'].nunique()} corridas, trimestres {', '.join(sorted(reg['trimestre'].unique()))}")
con_oficial = reg[reg["oficial"].notna() & reg["indicador"].isin(SERIES_T)]
if len(con_oficial):
    print("Proyecciones que ya tienen su EPH (error = proyectado − oficial):")
    display(con_oficial.groupby(["indicador", "trimestre"])["error"].agg(["count", "mean", "last"]).round(2))
else:
    print(f"Todavía ninguna proyección tiene su EPH: el primer control será cuando se publique {OBJ_HOY[0] if OBJ_HOY else 'la próxima'}.")
display(reg[reg["indicador"] == nc.TERMO].drop(columns=["datos_hasta"]).tail(9).round(1))
''')

code(r'''
# Evolución de las versiones del termómetro de cada trimestre (se completa corrida a corrida)
rt = reg[reg["indicador"] == nc.TERMO].copy()
if len(rt):
    rt["fecha_corrida"] = pd.to_datetime(rt["fecha_corrida"])
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for i, (q, g) in enumerate(rt.groupby("trimestre")):
        col = list(COLOR_K.values())[i % 3]
        ax.fill_between(g["fecha_corrida"], g["ic_inf"], g["ic_sup"], color=col, alpha=0.12, lw=0)
        ax.plot(g["fecha_corrida"], g["valor"], "-o", color=col, lw=1.8, ms=6, label=f"{q} (proyección)")
        if g["oficial"].notna().any():
            ax.axhline(g["oficial"].dropna().iloc[-1], color=col, ls="--", lw=1.2, label=f"{q} (EPH)")
    ax.set_ylim(0, 100)
    ax.set_xlim(rt["fecha_corrida"].min() - pd.Timedelta(days=20), rt["fecha_corrida"].max() + pd.Timedelta(days=20))
    ax.set_ylabel("Termómetro")
    ax.set_title("Versiones de la proyección del termómetro por fecha de corrida")
    ax.legend(frameon=False, fontsize=9, ncol=3)
    fig.autofmt_xdate()
    plt.tight_layout()
    guardar_figura(fig, "nowcast_04_versiones")
    plt.show()
''')

md("""
## 9. Exportar

En `carga_EPH/resultados/nowcast/` (separador `;` y decimal `,`, como el 06):
`nowcast_termometro.csv` (proyección de esta corrida), `backtest_termometro.csv` (cada proyección
del backtest, en formato largo: una fila por trimestre, horizonte y serie) y
`backtest_termometro_resumen.csv` (errores por horizonte y serie) y `robustez_termometro.md` (la
lectura de la sección 7). El registro de versiones usa
formato estándar (coma y punto) porque lo relee el notebook. Los gráficos quedan en
`nowcast/graficos/`: `nowcast_01_error_por_horizonte`, `nowcast_02_backtest`, `nowcast_03_hoy`,
`nowcast_04_versiones` y `nowcast_05_evolucion`.
""")

code(r'''
os.makedirs(NOWCAST_DIR, exist_ok=True)
opts = dict(sep=";", decimal=",", encoding="utf-8-sig", index=False)
archivos = {"nowcast_termometro.csv": nuevas, "backtest_termometro.csv": bt,
            "backtest_termometro_resumen.csv": res.reset_index()}
for nombre, df in archivos.items():
    path = os.path.join(NOWCAST_DIR, nombre)
    df.to_csv(path, **opts)
    print("Guardado:", path)
path = os.path.join(NOWCAST_DIR, "robustez_termometro.md")
with open(path, "w", encoding="utf-8") as fh:
    fh.write(f"### Robustez del nowcast del termómetro ({FECHA_CORRIDA:%d/%m/%Y}, base EPH {ULTIMO})\n\n"
             + "\n".join(f"- {a}" for a in alertas) + "\n")
print("Guardado:", path)
graficos = sorted(os.listdir(GRAFICOS_DIR)) if os.path.isdir(GRAFICOS_DIR) else []
print(f"Gráficos en {GRAFICOS_DIR}: " + (", ".join(graficos) if graficos else "ninguno"))
''')

md(r"""
## Anexo: decisiones y pruebas (oct-2026)

**D (microsimulación, 2026-10-20):**
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
- **Sesgo:** la proyección de D tiende a ser algo pesimista (los ingresos de la EPH crecen
  ~0,3-0,5% por trimestre más que los índices) y el sesgo crece con k. Corregirlo con los errores
  pasados (ventanas de 4, 8, 12 o todos) baja el sesgo pero no el error cuadrático (empeora el del
  ingreso laboral), así que no se usa. Revisarlo cuando el registro tenga errores reales.

**A, B y C (ecuaciones puente, 2026-10-21):**
- **Predictores candidatos:** EMAE, SIPA (asalariados privados, totales, monotributo), Encuesta de
  Indicadores Laborales, confianza del consumidor (general, situación personal, bienes durables) y
  gasto real en seguro de desempleo. Correlación de los cambios trimestrales con los de la EPH
  (desestacionalizados, 2017-2026 sin pandemia): la confianza en bienes durables es la que más
  anticipa (−0,59 con despidos, −0,52 con gastaron ahorros, −0,45 con desocupación); los
  asalariados registrados del SIPA, la subocupación (−0,53) y alimentos de familiares (−0,44); el
  EMAE, la tasa de empleo (0,42) y despidos (−0,49). Sin cobertura de salud, ocupados que buscan
  otro empleo y alimentos del gobierno no correlacionan con ninguna (|corr.| < 0,33).
- **Especificación neutral:** los mismos tres predictores (EMAE, asalariados SIPA, confianza en
  bienes durables) para los 13 indicadores. Elegir los mejores para cada indicador da un backtest
  parecido (termómetro 4,2 contra 4,3 a k = 1) pero optimista, porque la elección usa el período
  evaluado.
- **Rebote de la EPH:** los cambios trimestrales de la EPH revierten (autocorrelación de hasta
  −0,48: buena parte es ruido de muestra), pero sumar ese término a la ecuación empeora el backtest
  (sobreajuste con ~30 trimestres): no se usa.
- **Resultado por dimensión** (k = 1, 80 días; puente vs persistencia): A 11,4 vs 12,0; B 14,2 vs
  14,1 (sin mejora); C 7,4 vs 8,7 (a k = 2, peor: 14,8 vs 13,8); termómetro 4,1 vs 5,5 (con D por
  microsimulación en los dos casos). Por indicador, el puente le gana a la persistencia en 5 de 13.
- **Ojo con el 4,1:** a k = 1, la mayor parte de la mejora del termómetro viene de que los errores
  de B quedan correlacionados negativamente con los de A y C (−0,30 y −0,40; con persistencia,
  −0,04 y −0,08) y se compensan en el promedio. Puede no repetirse: lo esperable está entre 4,1 y
  5,5. A k ≥ 2 la mejora de A sí es sólida (k = 2 al cierre: 11,9 vs 15,4).
- **Ruido del percentil:** con ~40 trimestres, un error chico en un indicador puede mover su
  percentil muchos puntos si cae en una zona densa de la historia; por eso las dimensiones (4 o 5
  indicadores) y sobre todo el termómetro (15) se proyectan mejor que cada indicador por separado.
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
