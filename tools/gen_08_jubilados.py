"""Genera notebooks/08_jubilados.ipynb.

El notebook 08 NO se edita a mano: se edita este script y se regenera.

Uso (desde la raíz del repo):
    python tools/gen_08_jubilados.py                 # escribe notebooks/08_jubilados.ipynb
    python tools/gen_08_jubilados.py otra/ruta.ipynb

Cada llamada a md()/code() agrega una celda en orden. La lógica vive en src/jubilados.py; el
notebook la usa, arma las tablas y los gráficos. Ver docs/TECNICO.md §8.
"""
import json
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "notebooks", "08_jubilados.ipynb")

cells = []


def md(s):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)})


def code(s):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
                  "source": s.strip("\n").splitlines(keepends=True)})


md(r"""
# 08 - Adultos mayores y jubilados (EPH)

Cómo viven los **adultos mayores** de los 31 aglomerados urbanos de la EPH: cuántos son, con quién
viven (si viven con sus hijos o los hijos con ellos), si cobran jubilación o pensión y cuánto, qué
parte del ingreso de su hogar aportan, pobreza e indigencia, trabajo, vivienda, estrategias del
hogar, salud, educación y estado civil; por región y aglomerado, y su evolución desde 2017.

**Adultos mayores (AM):** varones de **65 años o más** y mujeres de **60 o más** (las edades
jubilatorias). Para comparar: *pre-jubilables* (varones de 60 a 64 y mujeres de 55 a 59), adultos
más jóvenes y menores de 18.

**Período:** la foto junta los **últimos 4 trimestres** disponibles (el doble de muestra que uno solo
y sin la estacionalidad del aguinaldo); la evolución usa todos los trimestres desde 2017.

**Cómo se mide cada cosa:**

| Tema | Variables EPH | Ponderador |
|---|---|---|
| Edad, sexo, parentesco y con quién viven | `CH06`, `CH04`, `CH03` de todos los integrantes del hogar | `PONDERA` |
| Cobra jubilación o pensión, tipo y monto | `V2_M` (hasta 2023T3); `V2_01_M` por aportes, `V2_02_M` por moratoria y `V2_03_M` otras pensiones (PUAM, discapacidad, madre de 7 hijos), desde 2023T4 | `PONDII` |
| Ingreso individual, del hogar y aporte de los AM | `P47T`, `P21`, `TOT_P12`, `ITF`, `IPCF`, `P_DECCF` | `PONDII`, `PONDIH` |
| Pobreza e indigencia | `ITF` contra la CBT / CBA del hogar (adultos equivalentes del INDEC y canasta de su región) | `PONDIH` |
| Trabajo | `ESTADO`, `CAT_OCUP`, `EMPLEO` (informalidad), `PP3E_TOT` | `PONDERA` |
| Vivienda, estrategias del hogar, salud, educación | `II7`, `II1`, `IV6`, `IV11`, `II8`, `IV12_3`; `V6`, `V7`, `V13`-`V17`; `CH08`, `NIVEL_ED`, `CH07`, `VII1_1`/`VII1_2` | `PONDERA` |

**Decisiones de método** (detalle en `src/jubilados.py` y `docs/TECNICO.md` §8):
- *Jubilado* = declara un monto de jubilación o pensión mayor a cero. La EPH no separa la
  jubilación de la pensión por fallecimiento. `CAT_INAC` (jubilado inactivo) no sirve: cambió de
  códigos en 2023T4 y no viene en la base de 2026T1.
- Quien no declara sus ingresos (~11% de los AM) queda afuera con `PONDII`/`PONDIH` = 0 y los
  ponderadores de ingresos compensan: la cobertura previsional da ~89%, estable entre esquemas.
- **Pobreza**: metodología del INDEC (canasta del trimestre calendario por región y adulto
  equivalente). La réplica coincide con la tasa oficial con un error medio de 0,1 pp (sección 15).
- **Ingresos reales** en pesos del último mes con IPC, con los meses de referencia de los ingresos
  (mes anterior a la entrevista), como el 06 y el 07. **Haber en mínimas**: monto declarado sobre el
  haber mínimo de esos meses; *la mínima (con o sin bono)* va de 0,95 mínimas a 1,05 × (mínima + bono).
  El monto declarado es el que se cobra en mano: puede quedar debajo de la mínima por descuentos
  (cuotas de moratoria, créditos de ANSES) o por ser una pensión no contributiva (PUAM = 80%).
- **Intervalos de confianza del 95%** por bootstrap de viviendas (como el 06). Marcas: `*` usar con
  cautela (coeficiente de variación 20-33% o menos de 100 casos), `**` no confiable (más de 33% o
  menos de 50 casos).

**Contenido:** 1-2 setup y datos · 3 cuántos son · 4 con quién viven · 5 jubilación · 6 ingresos ·
7 pobreza · 8 trabajo · 9 vivienda · 10 estrategias del hogar · 11 salud, educación y estado civil ·
12 regiones y aglomerados · 13 evolución · 14 lectura · 15 controles · 16 exportar.

**Salidas** (en Drive, `carga_EPH/resultados/jubilados/`): `jubilados_EPH.xlsx` (una hoja por tabla
con valor, IC, casos y calidad), `tablas/*.csv`, `graficos/*.png`, `jubilados_EPH_resumen.md` y un
ZIP con todo que se descarga al final.
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

# Carpeta de resultados en Drive (la misma del 06; este notebook escribe en resultados/jubilados/)
RESULTADOS_DIR = "/content/drive/MyDrive/carga_EPH/resultados"
''')

code(r'''
import importlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from IPython.display import Markdown

import src.nowcast as nc
import src.jubilados as jb
importlib.reload(nc)
importlib.reload(jb)  # Colab reutiliza sesiones: tomar la versión recién bajada del repo
from src.data_loader import load_panel, list_available_quarters

jb.estilo()
C, GRIS_CLARO = jb.COLORES, "#c3c2b7"
# Cada grupo de edad con su color en todos los gráficos (los adultos mayores, siempre azul)
COLOR_GRUPO = {jb.GRUPOS[0]: C[3], jb.GRUPOS[1]: C[2], jb.GRUPOS[2]: C[1], jb.GRUPOS[3]: C[0]}
COLOR_RESTO = jb.GRIS

JUB_DIR = os.path.join(RESULTADOS_DIR, "jubilados")
GRAFICOS_DIR = os.path.join(JUB_DIR, "graficos")
os.makedirs(GRAFICOS_DIR, exist_ok=True)
TABLAS, DESCRIPCION = {}, {}

def guardar_figura(fig, nombre, nota=jb.NOTA_CALIDAD, periodo=None):
    """Agrega la fuente (y la nota de precisión) y guarda el PNG en resultados/jubilados/graficos/."""
    fig.text(0.01, 0.0, f"Fuente: elaboración propia con microdatos de la EPH (INDEC), {periodo or PERIODO}, 31 aglomerados "
             f"urbanos. {nota}", fontsize=7.5, color=jb.TEXTO2, ha="left", va="top", wrap=True)
    fig.savefig(os.path.join(GRAFICOS_DIR, f"{nombre}.png"), dpi=150, bbox_inches="tight", facecolor="white")

def guardar_tabla(nombre, tabla, descripcion):
    """Registra la tabla para el Excel y los CSV (sección 16) y la devuelve."""
    TABLAS[nombre], DESCRIPCION[nombre] = tabla, descripcion
    return tabla

def ver(res, fmt=jb.pct):
    """Muestra un resultado como 'valor (IC 95%)' con su marca de calidad."""
    display(jb.tabla_legible(res, fmt).to_frame("valor (IC 95%)"))
''')

md("""
## 2. Datos

Microdatos de los últimos 4 trimestres (foto) y series externas: IPC nacional y haber mínimo
(API de datos.gob.ar; si falla, la copia `data/series_nowcast.csv` del 07), bono previsional (carga
manual, `data/bono_previsional.csv`) y canastas básicas por región (datos.gob.ar; copia en
`data/canastas_regionales.csv`). Si a una región le falta la canasta de algún mes, se estima con la
nacional y la relación región/nacional de los últimos 6 meses (queda avisado en la sección 15).
""")

code(r'''
TRIMESTRES = [jb.a_etiqueta(q) for q in list_available_quarters()]
FOTO = TRIMESTRES[-4:]        # la foto junta los últimos 4 trimestres
N_TRIM = len(FOTO)
def nombre_q(q):
    return f"T{q[-1]}-{q[:4]}"
PERIODO = f"{nombre_q(FOTO[0])} a {nombre_q(FOTO[-1])}"

series, origen = jb.cargar_ipc_haber(os.path.join(REPO_DIR, "data", "series_nowcast.csv"),
                                     os.path.join(REPO_DIR, "data", "bono_previsional.csv"))
canastas, origen["canastas"] = jb.cargar_canastas(os.path.join(REPO_DIR, "data", "canastas_regionales.csv"))
REF, MES_HOY = jb.referencias(TRIMESTRES, series, canastas)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
PESOS_HOY = f"pesos de {MESES[MES_HOY.month - 1]} de {MES_HOY.year}"
display(pd.DataFrame({
    "Origen": origen,
    "Último mes": {"ipc": str(series["ipc"].index[-1]), "haber_min": str(series["haber_min"].index[-1]),
                   "bono": str(series["bono"].index[-1]),
                   "canastas": f"{canastas['cbt_noreste'].dropna().index[-1]} (regiones), "
                               f"{canastas['cbt_nac'].dropna().index[-1]} (nacional)"}}))

d = jb.preparar(jb.cargar(load_panel, PROCESSED_DIR, FOTO), REF)
# Multiplicadores bootstrap para las viviendas de toda la serie (la foto y la evolución usan los mismos)
bs = jb.Bootstrap(load_panel(columns=["CODUSU"], out_dir=PROCESSED_DIR)["CODUSU"])
am = d["ES_AM"].to_numpy()
cobra = am & (d["COBRA"] == 1).to_numpy()
print(f"Foto: {PERIODO} ({N_TRIM} trimestres) | {len(d):,} personas en la muestra, {am.sum():,} adultos mayores".replace(",", "."))
print(f"Ingresos en {PESOS_HOY} (IPC nacional) | evolución: {nombre_q(TRIMESTRES[0])} a {nombre_q(TRIMESTRES[-1])}")
''')

md("""
## 3. Cuántos son

Población de adultos mayores en los aglomerados de la EPH (promedio de los 4 trimestres), por sexo y
edad, y hogares con adultos mayores. La EPH cubre los 31 aglomerados urbanos (~63% de la población
del país): las cantidades no son totales nacionales.
""")

code(r'''
pob = jb.juntar(
    jb.estimar(d, bs, None, "PONDERA", tipo="total", filtro=am, n_trim=N_TRIM),
    jb.estimar(d, bs, None, "PONDERA", tipo="total", filtro=am, por="SEXO", orden=["Mujeres", "Varones"], n_trim=N_TRIM),
    jb.estimar(d, bs, None, "PONDERA", tipo="total", filtro=am, por="TRAMO", orden=jb.TRAMOS, n_trim=N_TRIM))
pob[["valor", "ic_inf", "ic_sup"]] /= 1e6
pob_pct = jb.estimar(d, bs, "ES_AM_F", "PONDERA")
mujeres_pct = jb.distribucion(d, bs, "SEXO", "PONDERA", ["Mujeres", "Varones"], filtro=am)

hog = d[d["CH03"] == 1].copy()  # un registro por hogar (el jefe o la jefa)
con_am = (hog["N_AM"] > 0).to_numpy()
hog["CON_AM"] = con_am.astype(float)
hog["SOLO_AM"] = (hog["N_AM"] == hog["TAM"]).astype(float)
hog["UNIPERSONAL"] = (hog["TAM"] == 1).astype(float)
hogares = jb.juntar(
    jb.estimar(hog, bs, "CON_AM", "PONDERA").rename(index={"Total": "Hogares con al menos un adulto mayor (% de los hogares)"}),
    jb.estimar(hog, bs, "SOLO_AM", "PONDERA", filtro=con_am).rename(index={"Total": "Formados solo por adultos mayores (% de los hogares con AM)"}),
    jb.estimar(hog, bs, "UNIPERSONAL", "PONDERA", filtro=con_am).rename(index={"Total": "Unipersonales (% de los hogares con AM)"}))
n_hog = jb.estimar(hog, bs, None, "PONDERA", tipo="total", filtro=con_am, n_trim=N_TRIM).iloc[0]

guardar_tabla("01_cuantos", pd.concat({"Adultos mayores (millones)": pob,
                                       "% de la población": pob_pct,
                                       "% de los AM por sexo": mujeres_pct.droplevel(0)}, names=["indicador", "grupo"]),
              "Adultos mayores: millones de personas (promedio de los 4 trimestres), % de la población y % por sexo. PONDERA.")
guardar_tabla("02_hogares", hogares, "Hogares con adultos mayores (un registro por hogar). PONDERA.")
print(f"Adultos mayores: {jb.num(pob.loc['Total', 'valor'], 2)} millones ({jb.con_ic(pob_pct.iloc[0])} de la población); "
      f"{jb.pct(mujeres_pct.iloc[0]['valor'])} son mujeres")
print(f"Hogares con adultos mayores: {jb.num(n_hog['valor'] / 1e6, 2)} millones")
ver(pob, lambda x: jb.num(x, 2))
ver(hogares)
''')

code(r'''
# Pirámide de 50 años y más: en azul, quienes ya están en la edad jubilatoria
p = d[d["CH06"] >= 50].copy()
EDADES5 = ["50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
p["EDAD5"] = pd.cut(p["CH06"].clip(upper=99), bins=[50, 55, 60, 65, 70, 75, 80, 85, 200], right=False, labels=EDADES5)
pir = p.groupby(["EDAD5", "SEXO"], observed=True).agg(miles=("PONDERA", "sum"), am=("ES_AM", "max"))
pir["miles"] /= N_TRIM * 1e3
fig, ax = plt.subplots(figsize=(10, 6))
y = np.arange(len(EDADES5))
for sexo, signo in (("Varones", -1), ("Mujeres", 1)):
    t = pir.xs(sexo, level="SEXO").reindex(EDADES5)
    ax.barh(y, signo * t["miles"], height=0.72, color=[C[0] if a else GRIS_CLARO for a in t["am"]], zorder=2)
    for yi, v in zip(y, t["miles"]):
        ax.text(signo * (v + 25), yi, jb.num(v, 0), ha="right" if signo < 0 else "left", va="center", fontsize=8.5, color=jb.TINTA)
tope = pir["miles"].max() * 1.22
ax.set_xlim(-tope, tope)
ax.set_yticks(y, EDADES5)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: jb.num(abs(v), 0)))
ax.axvline(0, color=jb.GRIS, lw=0.8)
ax.text(-tope * 0.97, len(EDADES5) - 0.4, "Varones", fontsize=10, fontweight="bold", color=jb.TEXTO2)
ax.text(tope * 0.97, len(EDADES5) - 0.4, "Mujeres", fontsize=10, fontweight="bold", color=jb.TEXTO2, ha="right")
ax.legend(handles=[Patch(color=C[0], label="Adultos mayores (edad jubilatoria: V 65+, M 60+)"),
                   Patch(color=GRIS_CLARO, label="Todavía no llegan a la edad jubilatoria")],
          loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
ax.set_xlabel("Miles de personas")
ax.set_title(f"Población de 50 años y más por sexo y edad, {PERIODO}")
ax.grid(axis="y", visible=False)
fig.tight_layout()
guardar_figura(fig, "01_piramide", nota="Promedio de los 4 trimestres.")
plt.show()
''')

md("""
## 4. Con quién viven

**Tipología de convivencia** (a partir del parentesco `CH03` de todos los integrantes del hogar):
*solo/a*; *solo con su pareja*; *con hijos* (el AM es jefe/a o cónyuge y en el hogar hay hijos o
hijastros, sin nietos); *con hijos y nietos* (tres generaciones); *con nietos, sin hijos*; *en el
hogar de un hijo/a* (el AM es padre, madre o suegro/a del jefe/a); *otros arreglos* (con hermanos u
otros familiares o no familiares).

Lo que distingue quién es el jefe de hogar: **los hijos viven en el hogar del adulto mayor** (el AM es
jefe/a o cónyuge) o **el adulto mayor vive en el hogar de un hijo/a**.
""")

code(r'''
FILAS_SEXO_TRAMO = ["Total", "Mujeres", "Varones"] + jb.TRAMOS
conv = jb.juntar(
    jb.distribucion(d, bs, "CONVIVENCIA", "PONDERA", jb.CONVIVENCIA, filtro=am),
    jb.distribucion(d, bs, "CONVIVENCIA", "PONDERA", jb.CONVIVENCIA, por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
    jb.distribucion(d, bs, "CONVIVENCIA", "PONDERA", jb.CONVIVENCIA, por="TRAMO", filtro=am, orden=jb.TRAMOS))
guardar_tabla("03_convivencia", conv, "Adultos mayores según con quién viven (% por grupo). PONDERA.")
display(jb.ancho(conv, jb.CONVIVENCIA, FILAS_SEXO_TRAMO).round(1))

fig, ax = plt.subplots(figsize=(12, 5.2))
jb.apiladas(ax, jb.ancho(conv, jb.CONVIVENCIA, FILAS_SEXO_TRAMO), C[:7], ncol=4)
ax.set_title(f"Con quién viven los adultos mayores, {PERIODO} (% de cada grupo)")
fig.tight_layout()
guardar_figura(fig, "02_convivencia")
plt.show()
''')

code(r'''
rol = jb.juntar(
    jb.distribucion(d, bs, "ROL", "PONDERA", jb.ROLES, filtro=am),
    jb.distribucion(d, bs, "ROL", "PONDERA", jb.ROLES, por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
    jb.distribucion(d, bs, "ROL", "PONDERA", jb.ROLES, por="TRAMO", filtro=am, orden=jb.TRAMOS))
hijos_am = jb.juntar(
    jb.distribucion(d, bs, "CON_HIJOS", "PONDERA", jb.CON_HIJOS, filtro=am),
    jb.distribucion(d, bs, "CON_HIJOS", "PONDERA", jb.CON_HIJOS, por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
    jb.distribucion(d, bs, "CON_HIJOS", "PONDERA", jb.CON_HIJOS, por="TRAMO", filtro=am, orden=jb.TRAMOS))
guardar_tabla("04_rol_en_hogar", rol, "Adultos mayores según su parentesco con el jefe/a de hogar (%). PONDERA.")
guardar_tabla("05_con_hijos", hijos_am, "Adultos mayores que viven con hijos: los hijos en el hogar del AM o el AM en el hogar de un hijo/a (%). PONDERA.")
display(jb.ancho(hijos_am, jb.CON_HIJOS, FILAS_SEXO_TRAMO).round(1))

fig, axs = plt.subplots(1, 2, figsize=(15, 5.2))
jb.apiladas(axs[0], jb.ancho(rol, jb.ROLES, FILAS_SEXO_TRAMO), C[:4], ncol=2)
axs[0].set_title("Parentesco con el jefe/a de hogar (%)")
jb.apiladas(axs[1], jb.ancho(hijos_am, jb.CON_HIJOS, FILAS_SEXO_TRAMO), [C[0], C[1], GRIS_CLARO], ncol=2)
axs[1].set_title("¿Viven con hijos? ¿En qué hogar? (%)")
axs[1].set_yticklabels([])
fig.suptitle(f"Quién es el jefe de hogar y si viven con sus hijos, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "03_con_hijos")
plt.show()
''')

md("""
### Los hijos que viven con ellos

Hijos e hijastros que viven en hogares donde un adulto mayor es jefe/a o cónyuge: su edad y si
trabajan. Unidad: los hijos (no los adultos mayores).
""")

code(r'''
h = jb.hijos_convivientes(d)
hijos_edad = jb.distribucion(h, bs, "EDAD_HIJO", "PONDERA", jb.EDAD_HIJOS).droplevel(0)
hijos_cond = jb.distribucion(h, bs, "COND_HIJO", "PONDERA", jb.COND_HIJOS).droplevel(0)
n_hijos = jb.estimar(h, bs, None, "PONDERA", tipo="total", n_trim=N_TRIM).iloc[0]
guardar_tabla("06_hijos_convivientes", pd.concat({"Edad": hijos_edad, "Condición de actividad": hijos_cond}, names=["corte", "categoria"]),
              "Hijos/as que viven en el hogar de un adulto mayor (jefe/a o cónyuge): edad y condición de actividad (% de los hijos). PONDERA.")
print(f"Hijos/as en hogares de adultos mayores: {jb.num(n_hijos['valor'] / 1e6, 2)} millones ({len(h):,} casos)".replace(",", "."))

fig, axs = plt.subplots(1, 2, figsize=(13, 3.8))
jb.barras_ic(axs[0], hijos_edad, C[0])
axs[0].set_title("Edad (% de los hijos)")
jb.barras_ic(axs[1], hijos_cond, C[0])
axs[1].set_title("Condición de actividad (% de los hijos)")
fig.suptitle(f"Los hijos que viven en el hogar de un adulto mayor, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "04_hijos_convivientes")
plt.show()
''')

md("""
### Quién sostiene a quién

Parte del ingreso total del hogar (`ITF`) que aportan los adultos mayores (suma de sus ingresos
individuales `P47T`: jubilación, trabajo y otros), en los hogares con ingresos completos (`PONDIH`).
Las categorías son por adulto mayor. *Solo/a* no se muestra (aporta todo por definición).
""")

code(r'''
FILAS_CONV = jb.CONVIVENCIA[1:]
sosten = jb.distribucion(d, bs, "SOSTEN", "PONDIH", jb.SOSTEN, por="CONVIVENCIA", filtro=am, orden=jb.CONVIVENCIA, total="Total")
sosten_hijos = jb.estimar(d, bs, "AM_SOSTEN", "PONDIH", por="CON_HIJOS", filtro=am, orden=jb.CON_HIJOS, total="Total")
aporte_medio = jb.estimar(d, bs, "APORTE_AM", "PONDIH", tipo="media", por="CONVIVENCIA", filtro=am, orden=jb.CONVIVENCIA, total="Total")
guardar_tabla("07_sosten", jb.juntar(sosten), "Parte del ingreso del hogar que aportan los adultos mayores, según con quién viven (% de los AM). PONDIH.")
guardar_tabla("08_sosten_hijos", pd.concat({"AM aportan más de la mitad (%)": sosten_hijos, "Aporte medio de los AM (% del ITF)": aporte_medio},
                                           names=["indicador", "grupo"]),
              "Adultos mayores cuyo hogar depende de su ingreso: % que aporta más de la mitad del ITF (por si viven con hijos) y aporte medio (por convivencia). PONDIH.")
ver(sosten_hijos)

fig, ax = plt.subplots(figsize=(12, 4.6))
jb.apiladas(ax, jb.ancho(sosten, jb.SOSTEN, FILAS_CONV + ["Total"]), jb.rampa(4)[::-1], ncol=4)
ax.set_title(f"Qué parte del ingreso del hogar aportan los adultos mayores, {PERIODO} (% de los AM)")
fig.tight_layout()
guardar_figura(fig, "05_sosten")
plt.show()
''')

md("""
## 5. Jubilación o pensión

Cobertura (cobra algún monto de jubilación o pensión), tipo de beneficio (desde 2023T4) y cuánto
cobran en haberes mínimos. Universo: adultos mayores que declararon sus ingresos (`PONDII`).
""")

code(r'''
cob = jb.juntar(
    jb.estimar(d, bs, "COBRA", "PONDII", filtro=am),
    jb.estimar(d, bs, "COBRA", "PONDII", por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
    jb.estimar(d, bs, "COBRA", "PONDII", por="TRAMO", filtro=am, orden=jb.TRAMOS))
tipos = jb.juntar(
    jb.distribucion(d, bs, "TIPO_JUB", "PONDII", jb.TIPOS_JUB, filtro=am),
    jb.distribucion(d, bs, "TIPO_JUB", "PONDII", jb.TIPOS_JUB, por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
    jb.distribucion(d, bs, "TIPO_JUB", "PONDII", jb.TIPOS_JUB, por="TRAMO", filtro=am, orden=jb.TRAMOS))
guardar_tabla("09_cobertura", cob, "Adultos mayores que cobran jubilación o pensión (%). PONDII.")
guardar_tabla("10_tipo_beneficio", tipos, "Adultos mayores por tipo de beneficio: por aportes, moratoria, otras pensiones (PUAM y no contributivas), más de uno, no cobra (%). PONDII.")
ver(cob)

fig, axs = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1, 1.6]})
jb.barras_ic(axs[0], cob, C[0], orden=FILAS_SEXO_TRAMO, xmax=100)
axs[0].set_title("Cobran jubilación o pensión (%)")
jb.apiladas(axs[1], jb.ancho(tipos, jb.TIPOS_JUB, FILAS_SEXO_TRAMO), C[:4] + [GRIS_CLARO], ncol=3)
axs[1].set_yticklabels([])
axs[1].set_title("Tipo de beneficio (%)")
fig.suptitle(f"Cobertura previsional de los adultos mayores, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "06_cobertura")
plt.show()
''')

code(r'''
FILAS_TIPO = ["Total"] + jb.TIPOS_JUB[:4]
bandas = jb.juntar(
    jb.distribucion(d, bs, "BANDA_HABER", "PONDII", jb.BANDAS_HABER, filtro=cobra),
    jb.distribucion(d, bs, "BANDA_HABER", "PONDII", jb.BANDAS_HABER, por="TIPO_JUB", filtro=cobra, orden=jb.TIPOS_JUB[:4]),
    jb.distribucion(d, bs, "BANDA_HABER", "PONDII", jb.BANDAS_HABER, por="SEXO", filtro=cobra, orden=["Mujeres", "Varones"]))
haber_med = pd.concat({
    f"Haber mediano ({PESOS_HOY})": jb.juntar(
        jb.estimar(d, bs, "JUB_R", "PONDII", tipo="mediana", filtro=cobra),
        jb.estimar(d, bs, "JUB_R", "PONDII", tipo="mediana", por="TIPO_JUB", filtro=cobra, orden=jb.TIPOS_JUB[:4]),
        jb.estimar(d, bs, "JUB_R", "PONDII", tipo="mediana", por="SEXO", filtro=cobra, orden=["Mujeres", "Varones"])),
    "Haber mediano (en haberes mínimos)": jb.juntar(
        jb.estimar(d, bs, "HABER_EN_MIN", "PONDII", tipo="mediana", filtro=cobra),
        jb.estimar(d, bs, "HABER_EN_MIN", "PONDII", tipo="mediana", por="TIPO_JUB", filtro=cobra, orden=jb.TIPOS_JUB[:4]),
        jb.estimar(d, bs, "HABER_EN_MIN", "PONDII", tipo="mediana", por="SEXO", filtro=cobra, orden=["Mujeres", "Varones"]))},
    names=["indicador", "grupo"])
ultimo = REF.loc[FOTO[-1]]
guardar_tabla("11_haber_en_minimas", bandas, "Adultos mayores que cobran, según el monto en haberes mínimos (%). La mínima (con o sin bono) = 0,95 a 1,05 x (mínima + bono). PONDII.")
guardar_tabla("12_haber_mediano", haber_med, f"Haber mediano de los adultos mayores que cobran, en {PESOS_HOY} y en haberes mínimos. PONDII.")
print(f"Haber mínimo en {nombre_q(FOTO[-1])}: {jb.pesos(ultimo['haber_min'] * ultimo['a_pesos_hoy'])} "
      f"(+ bono: {jb.pesos(ultimo['haber_bono'] * ultimo['a_pesos_hoy'])}), en {PESOS_HOY}")
ver(haber_med.loc[f"Haber mediano ({PESOS_HOY})"], jb.pesos)

fig, ax = plt.subplots(figsize=(12, 4.6))
jb.apiladas(ax, jb.ancho(bandas, jb.BANDAS_HABER, FILAS_TIPO + ["Mujeres", "Varones"]), jb.rampa(5), ncol=5)
ax.set_title(f"Cuánto cobran: haber declarado en haberes mínimos, {PERIODO} (% de los que cobran)")
fig.tight_layout()
guardar_figura(fig, "07_haber",
               nota="El haber declarado es el que se cobra en mano (neto de descuentos como cuotas de moratoria o créditos de ANSES). " + jb.NOTA_CALIDAD)
plt.show()
''')

md("""
## 6. Ingresos

Ingreso per cápita familiar (IPCF) real de cada grupo de edad, en qué decil de ingresos están los
adultos mayores (`P_DECCF`, deciles de personas del INDEC) y de qué está hecho su ingreso individual.
""")

code(r'''
ipcf = jb.estimar(d, bs, "IPCF_R", "PONDIH", tipo="mediana", por="GRUPO", orden=jb.GRUPOS, total="Total")
deciles = jb.distribucion(d, bs, "DECIL", "PONDIH", list(range(1, 11)), filtro=am).droplevel(0)
p47 = jb.juntar(jb.estimar(d, bs, "P47T_R", "PONDII", tipo="mediana", filtro=am),
                jb.estimar(d, bs, "P47T_R", "PONDII", tipo="mediana", por="SEXO", filtro=am, orden=["Mujeres", "Varones"]))
guardar_tabla("13_ipcf", ipcf, f"Ingreso per cápita familiar mediano por grupo de edad ({PESOS_HOY}). PONDIH.")
guardar_tabla("14_deciles", deciles, "Adultos mayores por decil de ingreso per cápita familiar de las personas (P_DECCF del INDEC; % de los AM, 10% = reparto parejo). PONDIH.")
guardar_tabla("15_ingreso_individual", p47, f"Ingreso individual total mediano de los adultos mayores ({PESOS_HOY}). PONDII.")
ver(ipcf, jb.pesos)
ver(p47, jb.pesos)

fig, axs = plt.subplots(1, 2, figsize=(15, 4.6))
jb.barras_ic(axs[0], ipcf, C[0], fmt=jb.pesos)
for barra, g in zip(axs[0].patches, ipcf.index):  # cada grupo con su color
    barra.set_color(COLOR_GRUPO.get(g, jb.GRIS))
axs[0].set_title(f"Ingreso per cápita familiar mediano ({PESOS_HOY})")
axs[0].xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: jb.num(v / 1e3, 0) + " mil"))
x = np.arange(1, 11)
axs[1].bar(x, deciles["valor"], color=C[0], width=0.7, zorder=2)
axs[1].errorbar(x, deciles["valor"], yerr=[deciles["valor"] - deciles["ic_inf"], deciles["ic_sup"] - deciles["valor"]],
                fmt="none", ecolor=jb.TINTA, elinewidth=1, capsize=2.5, zorder=3)
axs[1].axhline(10, color=jb.GRIS, ls="--", lw=1)
axs[1].text(0.55, 10.3, "reparto parejo: 10%", color=jb.TEXTO2, fontsize=8.5, ha="left", va="bottom")
axs[1].set_xticks(x, [f"{i}" for i in x])
axs[1].set_xlabel("Decil de ingreso per cápita familiar (1 = el 10% más pobre)")
axs[1].set_ylabel("% de los adultos mayores")
axs[1].grid(axis="x", visible=False)
axs[1].set_title("En qué decil de ingresos están los adultos mayores")
fig.suptitle(f"Ingresos de los adultos mayores, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "08_ingresos")
plt.show()
''')

code(r'''
# De qué está hecho el ingreso individual de los AM: jubilación (con aguinaldo), trabajo y otros
COMP = {"Jubilación o pensión (con aguinaldo)": "J", "Trabajo": "T", "Otros ingresos": "O"}
cb = d[am & (d["PONDII"] > 0).to_numpy() & (d["P47T"] > 0).to_numpy()].copy()
cb["J"], cb["T"] = cb["JUB_TOTAL"].fillna(0), cb["ING_TRABAJO"].fillna(0)
cb["O"] = (cb["P47T"] - cb["J"] - cb["T"]).clip(lower=0)
def composicion(g):
    w = g["PONDII"]
    tot = (w * (g["J"] + g["T"] + g["O"])).sum()
    return pd.Series({k: 100 * (w * g[c]).sum() / tot for k, c in COMP.items()})
comp = pd.concat([composicion(cb).rename("Total").to_frame().T,
                  cb.groupby("SEXO").apply(composicion, include_groups=False).reindex(["Mujeres", "Varones"]),
                  cb.groupby("TRAMO").apply(composicion, include_groups=False).reindex(jb.TRAMOS)])
guardar_tabla("16_composicion_ingreso", comp, "Composición del ingreso individual de los adultos mayores (% de la suma de sus ingresos; sin IC). PONDII.")
display(comp.round(1))

fig, ax = plt.subplots(figsize=(12, 4.2))
jb.apiladas(ax, comp, C[:3])
ax.set_title(f"De qué está hecho el ingreso de los adultos mayores, {PERIODO} (% de sus ingresos)")
fig.tight_layout()
guardar_figura(fig, "09_composicion_ingreso", nota="Suma de los ingresos individuales (P47T) de los AM con ingresos; sin intervalos de confianza.")
plt.show()
''')

md("""
## 7. Pobreza e indigencia

Personas en hogares con ingreso total familiar debajo de la canasta básica total (pobreza) o
alimentaria (indigencia) de su hogar: metodología del INDEC (sección 15: la réplica coincide con la
tasa oficial). Universo: personas en hogares con ingresos completos (`PONDIH`).
""")

code(r'''
pobreza_g = pd.concat({
    "Pobreza": jb.estimar(d, bs, "POBRE", "PONDIH", por="GRUPO", orden=jb.GRUPOS, total="Total"),
    "Indigencia": jb.estimar(d, bs, "INDIGENTE", "PONDIH", por="GRUPO", orden=jb.GRUPOS, total="Total")},
    names=["indicador", "grupo"])
pobreza_am = pd.concat({
    "Según con quién viven": jb.estimar(d, bs, "POBRE", "PONDIH", por="CONVIVENCIA", filtro=am, orden=jb.CONVIVENCIA),
    "Según si cobran y cuánto": jb.estimar(d, bs, "POBRE", "PONDIH", por="SITUACION_JUB", filtro=am, orden=jb.SITUACION_JUB),
    "Según tipo de beneficio": jb.estimar(d, bs, "POBRE", "PONDIH", por="TIPO_JUB", filtro=am, orden=jb.TIPOS_JUB),
    "Según sexo y edad": jb.juntar(jb.estimar(d, bs, "POBRE", "PONDIH", por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
                                   jb.estimar(d, bs, "POBRE", "PONDIH", por="TRAMO", filtro=am, orden=jb.TRAMOS))},
    names=["corte", "grupo"])
guardar_tabla("17_pobreza_grupos", pobreza_g, "Pobreza e indigencia por grupo de edad (% de personas). PONDIH.")
guardar_tabla("18_pobreza_am", pobreza_am, "Pobreza de los adultos mayores según con quién viven, si cobran y cuánto, tipo de beneficio, sexo y edad (%). PONDIH.")
ver(pobreza_g.loc["Pobreza"])
ver(pobreza_g.loc["Indigencia"])

fig, ax = plt.subplots(figsize=(11, 4.6))
jb.barras_agrupadas(ax, pobreza_g, ["Pobreza", "Indigencia"], jb.GRUPOS + ["Total"], colores=[C[0], C[1]])
ax.set_title(f"Pobreza e indigencia por grupo de edad, {PERIODO} (% de personas)")
fig.tight_layout()
guardar_figura(fig, "10_pobreza")
plt.show()

fig, axs = plt.subplots(1, 2, figsize=(15, 4.6))
jb.barras_ic(axs[0], pobreza_am.loc["Según con quién viven"], C[0])
axs[0].set_title("Según con quién viven")
jb.barras_ic(axs[1], pobreza_am.loc["Según si cobran y cuánto"], C[0])
axs[1].set_title("Según si cobran jubilación y cuánto")
fig.suptitle(f"Pobreza de los adultos mayores, {PERIODO} (%)", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "11_pobreza_am")
plt.show()
''')

md("""
## 8. Trabajo después de la edad jubilatoria

Quiénes siguen trabajando, si cobran además una jubilación y en qué condiciones trabajan; cómo
llegan a la edad jubilatoria los pre-jubilables.
""")

code(r'''
jt = jb.juntar(
    jb.distribucion(d, bs, "JUB_TRABAJO", "PONDII", jb.JUB_TRABAJO, filtro=am),
    jb.distribucion(d, bs, "JUB_TRABAJO", "PONDII", jb.JUB_TRABAJO, por="SEXO", filtro=am, orden=["Mujeres", "Varones"]),
    jb.distribucion(d, bs, "JUB_TRABAJO", "PONDII", jb.JUB_TRABAJO, por="TRAMO", filtro=am, orden=jb.TRAMOS))
ocupado = (d["OCUPADO"] == 1).to_numpy()
GR = jb.GRUPOS[1:]  # adultos, pre-jubilables y adultos mayores
ocupados = jb.juntar(jb.distribucion(d, bs, "CATEGORIA", "PONDERA", list(jb.CATEGORIAS.values()), por="GRUPO",
                                     filtro=ocupado, orden=GR))
ocu_ind = pd.concat({
    "Informales (% de los ocupados)": jb.estimar(d, bs, "INFORMAL", "PONDERA", por="GRUPO", orden=GR),
    "Horas semanales (mediana)": jb.estimar(d, bs, "HORAS", "PONDERA", tipo="mediana", por="GRUPO", orden=GR),
    f"Ingreso de la ocupación principal (mediana, {PESOS_HOY})": jb.estimar(d, bs, "P21_R", "PONDIIO", tipo="mediana", por="GRUPO", orden=GR)},
    names=["indicador", "grupo"])
trab_haber = jb.estimar(d, bs, "OCUPADO", "PONDII", por="SITUACION_JUB", filtro=am, orden=jb.SITUACION_JUB, total="Total")
guardar_tabla("19_jubilacion_trabajo", jt, "Adultos mayores según si cobran jubilación y si trabajan (%). PONDII.")
guardar_tabla("20_ocupados_categoria", ocupados, "Ocupados por categoría ocupacional: adultos, pre-jubilables y adultos mayores (%). PONDERA.")
guardar_tabla("21_ocupados_condiciones", ocu_ind, f"Ocupados: informalidad (EMPLEO), horas y ingreso de la ocupación principal ({PESOS_HOY}), por grupo. PONDERA / PONDIIO.")
guardar_tabla("22_trabajo_segun_haber", trab_haber, "Adultos mayores que trabajan según si cobran jubilación y cuánto (%). PONDII.")
display(jb.ancho(jt, jb.JUB_TRABAJO, FILAS_SEXO_TRAMO).round(1))
display(jb.tabla_legible(ocu_ind.loc["Informales (% de los ocupados)"]).to_frame("Informales (% de los ocupados)"))

fig, axs = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
jb.apiladas(axs[0], jb.ancho(jt, jb.JUB_TRABAJO, FILAS_SEXO_TRAMO), C[:4], ncol=2)
axs[0].set_title("Jubilación y trabajo (%)")
jb.barras_ic(axs[1], trab_haber, C[0])
axs[1].set_title("Trabajan, según si cobran y cuánto (%)")
fig.suptitle(f"Trabajo de los adultos mayores, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "12_jubilacion_trabajo")
plt.show()
''')

code(r'''
# Cómo llegan a la edad jubilatoria: pre-jubilables comparados con los adultos más jóvenes y los AM
IND_PRE = {"Trabajan (% ocupados)": ("OCUPADO", "PONDERA"),
           "Informales (% de los ocupados)": ("INFORMAL", "PONDERA"),
           "Ya cobran jubilación o pensión": ("COBRA", "PONDII"),
           "Sin cobertura de salud": ("SIN_COBERTURA", "PONDERA"),
           "Pobres": ("POBRE", "PONDIH")}
pre = pd.concat({k: jb.estimar(d, bs, c, p, por="GRUPO", orden=GR) for k, (c, p) in IND_PRE.items()}, names=["indicador", "grupo"])
guardar_tabla("23_prejubilables", pre, "Pre-jubilables (V 60-64, M 55-59) comparados con los adultos más jóvenes y los adultos mayores (%).")

fig, ax = plt.subplots(figsize=(12, 6))
jb.barras_agrupadas(ax, pre.swaplevel().sort_index(), GR, list(IND_PRE), colores=[COLOR_GRUPO[g] for g in GR])
ax.set_title(f"Cómo llegan a la edad jubilatoria, {PERIODO} (%)")
fig.tight_layout()
guardar_figura(fig, "13_prejubilables")
plt.show()
''')

md("""
## 9. Vivienda y servicios

Condiciones de la vivienda de los adultos mayores (cada persona con las de su hogar), comparadas con
el resto de la población.
""")

code(r'''
FILAS_VIV = [jb.RESTO, jb.AM]
tenencia = jb.juntar(
    jb.distribucion(d, bs, "TENENCIA", "PONDERA", jb.TENENCIA, por="AM_RESTO", orden=FILAS_VIV),
    jb.distribucion(d, bs, "TENENCIA", "PONDERA", jb.TENENCIA, por="CONVIVENCIA", filtro=am, orden=jb.CONVIVENCIA))
servicios = jb.varios(d, bs, jb.VIVIENDA, "PONDERA", por="AM_RESTO", orden=FILAS_VIV)
guardar_tabla("24_tenencia", tenencia, "Tenencia de la vivienda: adultos mayores (total y según con quién viven) y resto de la población (%). PONDERA.")
guardar_tabla("25_vivienda_servicios", servicios, "Hacinamiento y servicios de la vivienda: adultos mayores y resto de la población (% de personas). PONDERA.")
display(jb.ancho(tenencia, jb.TENENCIA, FILAS_VIV + jb.CONVIVENCIA).round(1))

fig, axs = plt.subplots(1, 2, figsize=(16, 5.2), gridspec_kw={"width_ratios": [1.2, 1]})
jb.apiladas(axs[0], jb.ancho(tenencia, jb.TENENCIA, FILAS_VIV + jb.CONVIVENCIA), C[:4], ncol=2)
axs[0].set_title("Tenencia de la vivienda (%)")
jb.barras_agrupadas(axs[1], servicios.swaplevel().sort_index(), [jb.AM, jb.RESTO], list(jb.VIVIENDA.values()),
                    colores=[C[0], COLOR_RESTO], nombres=["Adultos mayores", "Resto de la población"])
axs[1].set_title("Hacinamiento y servicios (% de personas)")
fig.suptitle(f"Vivienda de los adultos mayores, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "14_vivienda")
plt.show()
''')

md("""
## 10. Estrategias del hogar

Qué hicieron los hogares para vivir en los últimos 3 meses (las mismas preguntas que la dimensión C
del termómetro): adultos mayores contra el resto y, entre los adultos mayores, según cuánto cobran.
""")

code(r'''
ESTR = {f"E_{k}": v for k, v in jb.ESTRATEGIAS.items()}
estrategias = jb.varios(d, bs, ESTR, "PONDERA", por="AM_RESTO", orden=FILAS_VIV)
estr_haber = jb.varios(d, bs, {"E_V13": jb.ESTRATEGIAS["V13"], "E_V14": jb.ESTRATEGIAS["V14"], "E_V16": jb.ESTRATEGIAS["V16"]},
                       "PONDII", por="SITUACION_JUB", filtro=am, orden=jb.SITUACION_JUB)
guardar_tabla("26_estrategias", estrategias, "Estrategias del hogar en los últimos 3 meses: adultos mayores y resto de la población (% de personas). PONDERA.")
guardar_tabla("27_estrategias_haber", estr_haber, "Adultos mayores: gastaron ahorros, pidieron prestado o compraron en cuotas, según si cobran y cuánto (%). PONDII.")
display(estr_haber["valor"].unstack("indicador").reindex(jb.SITUACION_JUB).round(1))

fig, ax = plt.subplots(figsize=(12, 6.2))
jb.barras_agrupadas(ax, estrategias.swaplevel().sort_index(), [jb.AM, jb.RESTO], list(jb.ESTRATEGIAS.values()),
                    colores=[C[0], COLOR_RESTO], nombres=["Adultos mayores", "Resto de la población"])
ax.set_title(f"Qué hicieron los hogares para vivir en los últimos 3 meses, {PERIODO} (% de personas)")
fig.tight_layout()
guardar_figura(fig, "15_estrategias")
plt.show()
''')

md("""
## 11. Salud, educación, estado civil y tareas de la casa
""")

code(r'''
cobertura = jb.juntar(
    jb.distribucion(d, bs, "COBERTURA", "PONDERA", jb.COBERTURA, por="AM_RESTO", orden=FILAS_VIV),
    jb.distribucion(d, bs, "COBERTURA", "PONDERA", jb.COBERTURA, por="TRAMO", filtro=am, orden=jb.TRAMOS))
ADULTOS_25 = "Adultos de 25 años hasta 59 (V) / 54 (M)"  # sin los que todavía estudian
educacion = jb.juntar(
    jb.distribucion(d, bs, "EDUCACION", "PONDERA", jb.EDUCACION, por="GRUPO", orden=GR[:2],
                    filtro=(d["CH06"] >= 25).to_numpy()).rename(index={jb.GRUPOS[1]: ADULTOS_25}),
    jb.distribucion(d, bs, "EDUCACION", "PONDERA", jb.EDUCACION, por="TRAMO", filtro=am, orden=jb.TRAMOS))
civil = jb.distribucion(d, bs, "ESTADO_CIVIL", "PONDERA", jb.ESTADO_CIVIL, por="SEXO_TRAMO", filtro=am, orden=jb.SEXO_TRAMOS)
tareas = jb.estimar(d, bs, "TAREAS_CASA", "PONDERA", por="SEXO_TRAMO", filtro=am, orden=jb.SEXO_TRAMOS)
guardar_tabla("28_cobertura_salud", cobertura, "Cobertura de salud: adultos mayores (total y por edad) y resto de la población (%). PONDERA.")
guardar_tabla("29_educacion", educacion, "Máximo nivel educativo: adultos, pre-jubilables y adultos mayores por edad (%). PONDERA.")
guardar_tabla("30_estado_civil", jb.juntar(civil), "Estado civil de los adultos mayores por sexo y edad (%). PONDERA.")
guardar_tabla("31_tareas_casa", tareas, "Adultos mayores que hacen las tareas de la casa (principal o segunda persona que las hace, VII1_1/VII1_2) por sexo y edad (%). PONDERA.")

FILAS_ED = [ADULTOS_25, GR[1]] + jb.TRAMOS
fig, axs = plt.subplots(2, 2, figsize=(16, 10.5))
jb.apiladas(axs[0, 0], jb.ancho(cobertura, jb.COBERTURA, FILAS_VIV + jb.TRAMOS), C[:4], ncol=2)
axs[0, 0].set_title("Cobertura de salud (%)")
jb.apiladas(axs[0, 1], jb.ancho(educacion, jb.EDUCACION, FILAS_ED), jb.rampa(6), ncol=2)
axs[0, 1].set_title("Máximo nivel educativo (%)")
jb.apiladas(axs[1, 0], jb.ancho(civil, jb.ESTADO_CIVIL, jb.SEXO_TRAMOS), C[:4], ncol=4)
axs[1, 0].set_title("Estado civil (%)")
jb.barras_ic(axs[1, 1], tareas, C[0], orden=jb.SEXO_TRAMOS, xmax=100)
axs[1, 1].set_title("Hacen las tareas de la casa (%)")
fig.suptitle(f"Salud, educación, estado civil y tareas de la casa, {PERIODO}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout(h_pad=3)
guardar_figura(fig, "16_salud_educacion")
plt.show()
''')

md("""
## 12. Regiones y aglomerados

Los indicadores principales por región y por aglomerado, con su intervalo de confianza. La línea
punteada es el total de los 31 aglomerados. Con 4 trimestres juntos, todos los aglomerados tienen al
menos ~300 adultos mayores en la muestra; las estimaciones poco precisas quedan marcadas.
""")

code(r'''
IND_GEO = {
    "Adultos mayores (% de la población)": ("ES_AM_F", "PONDERA", None),
    "Cobran jubilación o pensión (%)": ("COBRA", "PONDII", am),
    "Cobran la mínima (% de los que cobran)": ("COBRA_MINIMA", "PONDII", cobra),
    "Viven solos (%)": ("VIVE_SOLO", "PONDERA", am),
    "Viven con hijos (%)": ("VIVE_CON_HIJOS", "PONDERA", am),
    "Pobres (%)": ("POBRE", "PONDIH", am),
}
total_geo = {k: jb.estimar(d, bs, c, p, filtro=f).iloc[0]["valor"] for k, (c, p, f) in IND_GEO.items()}
geo = {nivel: pd.concat({k: jb.estimar(d, bs, c, p, filtro=f, por=col) for k, (c, p, f) in IND_GEO.items()},
                        names=["indicador", nivel])
       for nivel, col in (("region", "REGION_N"), ("aglomerado", "AGLO_N"))}
guardar_tabla("32_regiones", geo["region"], "Indicadores principales de los adultos mayores por región, con IC 95%.")
guardar_tabla("33_aglomerados", geo["aglomerado"], "Indicadores principales de los adultos mayores por aglomerado, con IC 95%.")
display(geo["region"]["valor"].unstack("indicador")[list(IND_GEO)].round(1))

for nivel, alto, archivo in (("region", 6.5, "17_regiones"), ("aglomerado", 19, "18_aglomerados")):
    fig, axs = plt.subplots(2, 3, figsize=(17, alto))
    for ax, (k, color) in zip(axs.flat, zip(IND_GEO, [C[0]] * len(IND_GEO))):
        jb.puntos_ic(ax, geo[nivel].loc[k], color, ref=total_geo[k])
        ax.set_title(f"{k}\nlínea: total {jb.pct(total_geo[k])}", fontsize=10.5)
        if nivel == "aglomerado":
            ax.tick_params(axis="y", labelsize=8)
    fig.suptitle(f"Adultos mayores por {'región' if nivel == 'region' else 'aglomerado'}, {PERIODO}", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.35 / alto))  # deja lugar al título general
    guardar_figura(fig, archivo)
    plt.show()
''')

md("""
## 13. Evolución 2017-2026

Los indicadores principales trimestre a trimestre, con su intervalo de confianza. Los trimestres
de la pandemia (2020T2-2021T1, sombreados) tuvieron menos muestra y entrevistas telefónicas. El tipo
de beneficio solo existe desde 2023T4; la cobertura es comparable en toda la serie (sección 15).
""")

code(r'''
serie, sumas = {}, {}
for q in TRIMESTRES:
    dq = jb.preparar(jb.cargar(load_panel, PROCESSED_DIR, [q], cols=jb.COLS_SERIE), REF)
    serie[q] = jb.indicadores_trimestre(dq, bs)
    sumas[q] = jb.sumas_pobreza(dq)
del dq
evol = pd.concat(serie, names=["trimestre", "indicador"])
REF_REAL = pd.DataFrame({"Haber mínimo": REF["haber_min"] * REF["a_pesos_hoy"],
                         "Haber mínimo + bono": REF["haber_bono"] * REF["a_pesos_hoy"]})
guardar_tabla("34_evolucion", evol, f"Evolución trimestral de los indicadores principales, con IC 95% (ingresos en {PESOS_HOY}).")
guardar_tabla("35_haber_minimo_real", REF_REAL, f"Haber mínimo y mínimo + bono del período de referencia de cada trimestre, en {PESOS_HOY}.")
ev = evol["valor"].unstack("indicador")
filas_ev = sorted({q for q in TRIMESTRES if q.endswith("T1")} | set(FOTO), key=TRIMESTRES.index)
display(ev.loc[filas_ev, list(serie[TRIMESTRES[-1]].index)].astype(float).round(1).T)

def serie_de(nombre):
    return evol.xs(nombre, level="indicador")

def pandemia(ax):
    i0, i1 = TRIMESTRES.index("2020T2"), TRIMESTRES.index("2021T1")
    ax.axvspan(i0 - 0.5, i1 + 0.5, color=jb.GRILLA, alpha=0.6, lw=0, zorder=0)

fig, axs = plt.subplots(2, 2, figsize=(16, 9.5))
paneles = [
    ("Adultos mayores (% de la población)", [("Adultos mayores (% de la población)", C[0], "Adultos mayores")]),
    ("Cobertura previsional (%)", [("Cobran jubilación o pensión (%)", C[0], "Cobran jubilación o pensión"),
                                   ("Cobran la mínima (% de los que cobran)", C[1], "Cobran la mínima (% de los que cobran)")]),
    ("Con quién viven (% de los adultos mayores)", [("Viven solos (%)", C[0], "Viven solos"),
                                                     ("Viven con hijos (%)", C[1], "Viven con hijos"),
                                                     ("Viven en el hogar de un hijo/a (%)", C[2], "En el hogar de un hijo/a")]),
    ("Pobreza (% de personas)", [("Pobreza: adultos mayores (%)", C[0], "Adultos mayores"),
                                 ("Pobreza: resto de la población (%)", COLOR_RESTO, "Resto de la población")]),
]
for ax, (titulo, lineas) in zip(axs.flat, paneles):
    pandemia(ax)
    for nombre, color, etiqueta in lineas:
        jb.linea_ic(ax, serie_de(nombre).reindex(TRIMESTRES), color, etiqueta)
    jb.eje_trimestres(ax, TRIMESTRES)
    ax.set_title(titulo, fontsize=11)
    if len(lineas) > 1:
        ax.legend(loc="best", fontsize=8.5)
SERIE_TXT = f"{nombre_q(TRIMESTRES[0])} a {nombre_q(TRIMESTRES[-1])}"
fig.suptitle(f"Adultos mayores, {SERIE_TXT}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "19_evolucion", nota="Banda: IC 95% bootstrap por vivienda. Sombreado: pandemia (2020T2-2021T1).", periodo=SERIE_TXT)
plt.show()

fig, axs = plt.subplots(1, 2, figsize=(16, 5.2))
for ax in axs:
    pandemia(ax)
jb.linea_ic(axs[0], serie_de("Haber mediano (pesos de hoy)").reindex(TRIMESTRES), C[0], "Haber mediano declarado")
axs[0].plot(np.arange(len(TRIMESTRES)), REF_REAL["Haber mínimo"].reindex(TRIMESTRES), color=C[1], lw=2, label="Haber mínimo")
axs[0].plot(np.arange(len(TRIMESTRES)), REF_REAL["Haber mínimo + bono"].reindex(TRIMESTRES), color=C[1], lw=1.5, ls="--", label="Haber mínimo + bono")
axs[0].set_title(f"Jubilación: haber mediano y haber mínimo ({PESOS_HOY})", fontsize=11)
for nombre, color, etiqueta in (("IPCF mediano: adultos mayores (pesos de hoy)", C[0], "Adultos mayores"),
                                ("IPCF mediano: resto de la población (pesos de hoy)", COLOR_RESTO, "Resto de la población")):
    s = serie_de(nombre).reindex(TRIMESTRES)
    jb.linea_ic(axs[1], s, color, f"{etiqueta} (trimestral)", lw=1, alpha=0.5)
    axs[1].plot(np.arange(len(TRIMESTRES)), s["valor"].astype(float).rolling(4).mean(), color=color, lw=2.5,
                label=f"{etiqueta} (media móvil 4 trimestres)")
axs[1].set_title(f"Ingreso per cápita familiar mediano ({PESOS_HOY})", fontsize=11)
for ax in axs:
    jb.eje_trimestres(ax, TRIMESTRES)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: jb.num(v / 1e3, 0) + " mil"))
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower left", fontsize=8.5)
fig.suptitle(f"Ingresos reales de los adultos mayores, {SERIE_TXT}", x=0.01, ha="left", fontweight="bold")
fig.tight_layout()
guardar_figura(fig, "20_evolucion_ingresos", periodo=SERIE_TXT,
               nota=f"Pesos constantes ({PESOS_HOY}, IPC nacional). El haber no incluye el aguinaldo; el ingreso per cápita "
                    "familiar sí (picos en T1 y T3). Banda: IC 95% bootstrap. Sombreado: pandemia.")
plt.show()
''')

md("""
## 14. Lectura

Resumen automático con los números de las secciones anteriores (se guarda como
`jubilados_EPH_resumen.md`).
""")

code(r'''
def val(res, clave=None):
    fila = res.iloc[0] if clave is None else res.loc[clave]
    return fila["valor"]

def anual(nombre, anios):
    s = serie_de(nombre)["valor"].astype(float)
    return s[[q for q in s.index if q[:4] in anios]].mean()

conv_t = jb.ancho(conv, jb.CONVIVENCIA, ["Total"]).iloc[0]
hijos_t = jb.ancho(hijos_am, jb.CON_HIJOS, FILAS_SEXO_TRAMO)
tipos_t = jb.ancho(tipos, jb.TIPOS_JUB, ["Total"]).iloc[0]
bandas_t = jb.ancho(bandas, jb.BANDAS_HABER, ["Total"]).iloc[0]
jt_t = jb.ancho(jt, jb.JUB_TRABAJO, ["Total"]).iloc[0]
pobr = pobreza_g.loc["Pobreza"]
sit = pobreza_am.loc["Según si cobran y cuánto"]
ok_geo = lambda r: r[r["calidad"] == ""]["valor"]
cob_reg, pob_reg = ok_geo(geo["region"].loc["Cobran jubilación o pensión (%)"]), ok_geo(geo["region"].loc["Pobres (%)"])
pob_agl = ok_geo(geo["aglomerado"].loc["Pobres (%)"])
cob_agl = ok_geo(geo["aglomerado"].loc["Cobran jubilación o pensión (%)"])
ANIO0 = TRIMESTRES[0][:4]
ult4 = [q[:4] for q in FOTO]
haber_hoy = serie_de("Haber mediano (pesos de hoy)")["valor"].astype(float)
var_haber = lambda anios: 100 * (haber_hoy[FOTO].mean() / haber_hoy[[q for q in haber_hoy.index if q[:4] in anios]].mean() - 1)

resumen = f"""### Adultos mayores en la EPH, {PERIODO}

*Adultos mayores: varones de 65 años o más y mujeres de 60 o más. 31 aglomerados urbanos. Entre paréntesis, IC 95%.*

- **Cuántos son.** {jb.num(pob.loc['Total', 'valor'], 2)} millones de personas ({jb.num(pob.loc['Total', 'ic_inf'], 2)} a {jb.num(pob.loc['Total', 'ic_sup'], 2)}), el {jb.con_ic(pob_pct.iloc[0])} de la población de los aglomerados; el {jb.pct(mujeres_pct.iloc[0]['valor'], 0)} son mujeres. El {jb.pct(val(hogares), 0)} de los hogares tiene al menos un adulto mayor.
- **Con quién viven.** El {jb.pct(conv_t['Solo/a'])} vive solo/a y el {jb.pct(conv_t['Solo con su pareja'])} solo con su pareja. El {jb.pct(100 - hijos_t.loc['Total', jb.CON_HIJOS[2]])} vive con al menos un hijo/a: en el {jb.pct(hijos_t.loc['Total', jb.CON_HIJOS[0]])} los hijos viven en el hogar del adulto mayor y en el {jb.pct(hijos_t.loc['Total', jb.CON_HIJOS[1]])} el adulto mayor vive en el hogar de un hijo/a (entre los de 85 y más, {jb.pct(hijos_t.loc['85 y más', jb.CON_HIJOS[1]])}). El {jb.pct(conv_t['Con hijos y nietos'])} vive con hijos y nietos y el {jb.pct(conv_t['Con nietos, sin hijos'])} con nietos sin los hijos.
- **Los hijos que viven con ellos.** Son {jb.num(n_hijos['valor'] / 1e6, 2)} millones: el {jb.pct(hijos_cond.loc['Ocupado/a', 'valor'], 0)} trabaja, el {jb.pct(hijos_cond.loc['Desocupado/a', 'valor'], 0)} busca trabajo y el {jb.pct(hijos_edad.loc[['30 a 44', '45 y más'], 'valor'].sum(), 0)} tiene 30 años o más.
- **Quién sostiene a quién.** Cuando los hijos viven en el hogar del adulto mayor, los adultos mayores aportan más de la mitad del ingreso del hogar en el {jb.con_ic(sosten_hijos.loc[jb.CON_HIJOS[0]])} de los casos; cuando el adulto mayor vive en el hogar de un hijo/a, en el {jb.con_ic(sosten_hijos.loc[jb.CON_HIJOS[1]])}.
- **Jubilación.** El {jb.con_ic(cob.loc['Total'])} cobra jubilación o pensión (mujeres de 60 a 64: {jb.pct(cob.loc['Mujeres 60-64', 'valor'])}; de 75 a 84: {jb.pct(cob.loc['75 a 84', 'valor'])}). Por aportes {jb.pct(tipos_t['Por aportes'])}, por moratoria {jb.pct(tipos_t['Por moratoria'])}, otras pensiones {jb.pct(tipos_t[jb.TIPOS_JUB[2]])} y más de un beneficio {jb.pct(tipos_t['Más de un beneficio'])}. De los que cobran, el {jb.pct(bandas_t[jb.BANDAS_HABER[1]])} declara la mínima (con o sin bono) y el {jb.pct(bandas_t[jb.BANDAS_HABER[0]])} menos que la mínima; el haber mediano es {jb.pesos(haber_med.loc[(f'Haber mediano ({PESOS_HOY})', 'Total'), 'valor'])} ({PESOS_HOY}).
- **Ingresos.** El ingreso per cápita familiar mediano de los adultos mayores es {jb.pesos(ipcf.loc[jb.AM, 'valor'])}, contra {jb.pesos(ipcf.loc[jb.GRUPOS[0], 'valor'])} de los menores de 18 y {jb.pesos(ipcf.loc['Total', 'valor'])} del total. Solo el {jb.pct(deciles.loc[[1, 2, 3], 'valor'].sum())} de los adultos mayores está en los tres deciles más pobres (con un reparto parejo sería 30%). La jubilación es el {jb.pct(comp.loc['Total', 'Jubilación o pensión (con aguinaldo)'], 0)} de sus ingresos.
- **Pobreza.** El {jb.con_ic(pobr.loc[jb.AM])} de los adultos mayores es pobre y el {jb.pct(pobreza_g.loc[('Indigencia', jb.AM), 'valor'])} indigente, contra {jb.pct(pobr.loc[jb.GRUPOS[1], 'valor'])} de los adultos, {jb.pct(pobr.loc[jb.GRUPOS[0], 'valor'])} de los menores de 18 y {jb.pct(pobr.loc['Total', 'valor'])} del total. Entre los adultos mayores que no cobran jubilación, {jb.con_ic(sit.loc['No cobra'])}; entre los que cobran la mínima, {jb.pct(sit.loc[jb.BANDAS_HABER[1], 'valor'])}.
- **Trabajo.** El {jb.con_ic(pre.loc[('Trabajan (% ocupados)', jb.AM)])} trabaja. Entre los que declaran sus ingresos, {jb.pct(jt_t['Cobra y trabaja'])} cobra y trabaja, {jb.pct(jt_t['Trabaja sin jubilación'])} trabaja sin jubilación y {jb.pct(jt_t['Ni cobra ni trabaja'])} ni cobra ni trabaja; de los que no cobran, trabaja el {jb.pct(trab_haber.loc['No cobra', 'valor'], 0)}. El {jb.pct(ocu_ind.loc[('Informales (% de los ocupados)', jb.AM), 'valor'], 0)} de los adultos mayores ocupados es informal (adultos: {jb.pct(ocu_ind.loc[('Informales (% de los ocupados)', jb.GRUPOS[1]), 'valor'], 0)}). Entre los pre-jubilables, el {jb.pct(pre.loc[('Trabajan (% ocupados)', jb.GRUPOS[2]), 'valor'], 0)} trabaja y el {jb.pct(pre.loc[('Informales (% de los ocupados)', jb.GRUPOS[2]), 'valor'], 0)} de ellos en la informalidad.
- **Regiones y aglomerados.** Cobertura previsional: de {jb.pct(cob_reg.min())} ({cob_reg.idxmin()}) a {jb.pct(cob_reg.max())} ({cob_reg.idxmax()}); por aglomerado, de {jb.pct(cob_agl.min())} ({cob_agl.idxmin()}) a {jb.pct(cob_agl.max())} ({cob_agl.idxmax()}). Pobreza de los adultos mayores: de {jb.pct(pob_reg.min())} ({pob_reg.idxmin()}) a {jb.pct(pob_reg.max())} ({pob_reg.idxmax()}); por aglomerado, de {jb.pct(pob_agl.min())} ({pob_agl.idxmin()}) a {jb.pct(pob_agl.max())} ({pob_agl.idxmax()}).
- **Evolución.** Cobertura previsional: {jb.pct(anual('Cobran jubilación o pensión (%)', [ANIO0]))} en {ANIO0} y {jb.pct(serie_de('Cobran jubilación o pensión (%)')['valor'][FOTO].mean())} en los últimos 4 trimestres. Pobreza de los adultos mayores: {jb.pct(anual('Pobreza: adultos mayores (%)', [ANIO0]))} en {ANIO0}, {jb.pct(anual('Pobreza: adultos mayores (%)', ['2024']))} en 2024 y {jb.pct(serie_de('Pobreza: adultos mayores (%)')['valor'][FOTO].mean())} en los últimos 4 trimestres. El haber mediano real de los últimos 4 trimestres está {jb.num(var_haber([ANIO0]), 1, signo=True)}% contra {ANIO0} y {jb.num(var_haber(['2023']), 1, signo=True)}% contra 2023.
"""
display(Markdown(resumen))
''')

md("""
## 15. Controles de calidad

Muestra, no respuesta de ingresos, réplica de la pobreza oficial del INDEC, continuidad de la
cobertura en el cambio de esquema de 2023T4, consistencia entre tipos de beneficio y cobertura,
canastas y la masa de haberes en la mínima.
""")

code(r'''
controles = []
def chequeo(nombre, ok, detalle):
    controles.append({"Control": nombre, "Resultado": "✓" if ok else "⚠", "Detalle": detalle})

mu = d.groupby("q").agg(personas=("CODUSU", "size"), adultos_mayores=("ES_AM", "sum"))
chequeo("Muestra de adultos mayores por trimestre", mu["adultos_mayores"].min() >= 5000,
        f"{mu['adultos_mayores'].min():,} a {mu['adultos_mayores'].max():,} casos por trimestre".replace(",", "."))
nr_ii, nr_ih = 100 * (d.loc[am, "PONDII"] == 0).mean(), 100 * (d.loc[am, "PONDIH"] == 0).mean()
chequeo("No respuesta de ingresos de los adultos mayores (la compensan PONDII y PONDIH)", nr_ii < 25 and nr_ih < 35,
        f"{jb.pct(nr_ii)} sin ingreso individual y {jb.pct(nr_ih)} en hogares sin ingreso completo (casos)")

oficial, origen_of = jb.cargar_pobreza_oficial(os.path.join(REPO_DIR, "data", "pobreza_oficial.csv"))
replica = jb.pobreza_semestral(sumas)
val_pob = pd.concat({"Réplica": replica, "Oficial INDEC": oficial.reindex(index=replica.index)}, axis=1)
dif = (replica - oficial.reindex(index=replica.index, columns=replica.columns)).dropna(how="all")
mae_total = dif["Total"].abs().mean()
chequeo("Pobreza replicada vs. oficial del INDEC (personas, total)", mae_total < 0.5,
        f"error medio {jb.num(mae_total, 2)} pp, máximo {jb.num(dif['Total'].abs().max(), 2)} pp en "
        f"{dif['Total'].notna().sum()} semestres ({origen_of})")
regiones_of = [c for c in replica.columns if c != "Total" and c in oficial.columns]
mae_reg = dif[regiones_of].abs().mean()
chequeo("Pobreza replicada vs. oficial por región", mae_reg.max() < 1.5,
        "error medio: " + ", ".join(f"{r} {jb.num(mae_reg[r], 2)} pp" for r in regiones_of))

cob_s = serie_de("Cobran jubilación o pensión (%)")["valor"].astype(float)
salto = cob_s.get("2023T4", np.nan) - cob_s.get("2023T3", np.nan)
dif_ia = cob_s.diff().abs().drop(["2023T4"], errors="ignore").quantile(0.9)
chequeo("Cobertura previsional comparable en el cambio de esquema (2023T3 → 2023T4)", abs(salto) <= max(dif_ia, 1.5),
        f"salto de {jb.num(salto, 1, signo=True)} pp (el 90% de los cambios trimestrales del resto de la serie es menor a {jb.num(dif_ia)} pp)")
no_cobra = tipos.loc[("Total", "No cobra"), "valor"]
chequeo("Tipos de beneficio consistentes con la cobertura", abs(100 - no_cobra - cob.loc["Total", "valor"]) < 0.1,
        f"100 − no cobra = {jb.pct(100 - no_cobra, 2)} · cobertura = {jb.pct(cob.loc['Total', 'valor'], 2)}")
estimadas = REF.index[REF["canasta_estimada"].astype(bool)].tolist()
chequeo("Canastas regionales publicadas para todos los trimestres", not estimadas,
        "todas publicadas" if not estimadas else f"estimadas con la canasta nacional: {', '.join(estimadas)}")
minima = bandas.loc[("Total", jb.BANDAS_HABER[1]), "valor"]
chequeo("Masa de haberes en la mínima (alineación de los meses de referencia)", minima > 25,
        f"{jb.pct(minima)} de los que cobran declara la mínima (con o sin bono)")
flojas = sum(int(t["calidad"].isin(["con cautela", "no confiable"]).sum()) for t in TABLAS.values() if "calidad" in t)
total_est = sum(len(t) for t in TABLAS.values() if "calidad" in t)
chequeo("Estimaciones poco precisas (marcadas con * o **)", True, f"{flojas} de {total_est} estimaciones de las tablas")

display(pd.DataFrame(controles))
display(val_pob.xs("Total", axis=1, level=1).assign(**{"Diferencia (pp)": dif["Total"]}).round(1))
guardar_tabla("36_validacion_pobreza", val_pob, "Pobreza de personas por semestre y región: réplica de este notebook y tasa oficial del INDEC (%).")
guardar_tabla("37_referencias", REF, "Valores de referencia de cada trimestre: IPC, haber mínimo y mínimo + bono (meses de referencia), CBA y CBT por adulto equivalente y región (meses calendario).")
guardar_tabla("38_controles", pd.DataFrame(controles).set_index("Control"), "Controles de calidad de la corrida.")
''')

md("""
## 16. Exportar

Excel con una hoja por tabla (y un índice), CSV (`;` y coma decimal), los gráficos en PNG, el resumen
y un ZIP con todo en `carga_EPH/resultados/jubilados/`. En Colab, el ZIP además se descarga.
""")

code(r'''
rutas = jb.exportar(TABLAS, DESCRIPCION, JUB_DIR, resumen)
print(f"Excel: {rutas['excel']} ({len(TABLAS)} tablas)")
print(f"CSV: {rutas['csv']}")
print(f"Gráficos: {GRAFICOS_DIR} ({len(glob.glob(os.path.join(GRAFICOS_DIR, '*.png')))} PNG)")
print(f"ZIP: {rutas['zip']}")
try:
    from google.colab import files
    files.download(rutas["zip"])
except ImportError:
    pass  # fuera de Colab el ZIP queda en la carpeta de resultados
''')

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
