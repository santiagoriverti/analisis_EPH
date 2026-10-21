"""Nowcast del termómetro de los hogares (notebook 07).

Prototipo de la **dimensión D (ingresos reales)** por microsimulación: se toma una base de la EPH ya
publicada, se actualizan los ingresos de cada persona con índices mensuales que salen antes que la
EPH (salarios por sector, haber mínimo y bono previsional, AUH, IPC) y se recalculan los dos
indicadores de D con las mismas definiciones del notebook 06. Incluye el backtest en pseudo tiempo
real y el registro de versiones (cada corrida guarda lo que proyectó para medir el error cuando sale
la EPH oficial).

Convenciones:
- Trimestres como texto ``"AAAATq"`` (igual que el 06), para reutilizar sus funciones.
- Series mensuales con ``PeriodIndex`` mensual fechado en el **mes de referencia** del dato (el
  índice de salarios no registrado se corre hacia atrás; ver ``SERIES``).
- Los ingresos de la EPH son del mes anterior a la entrevista: el T1 usa diciembre, enero y febrero
  (``meses_ref``).
"""
from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

API_SERIES = "https://apis.datos.gob.ar/series/api/series/"

# nombre -> (id en datos.gob.ar, desfase en meses, rezago de publicación en días)
#   desfase: el dato fechado m en la API corresponde al mes m - desfase. El INDEC publica el índice
#     de salarios no registrado con 5 meses de rezago; contra el P21 de la EPH (fechado en el mes de
#     referencia) ajusta mejor con 6 (corr. de la variación i.a. 0,988, vs 0,982 con 5 y 0,874 sin
#     desfase; verificado 2026-10-20 con los 37 trimestres).
#   rezago: días entre el fin del mes de la fila de la API y su publicación (aproximado, calendario del
#     INDEC). Negativo = se conoce antes de que termine el mes (haberes y AUH se anuncian antes).
#     Solo se usa en el backtest, para simular qué datos había en cada fecha.
SERIES = {
    "ipc": ("148.3_INIVELNAL_DICI_M_26", 0, 14),
    "sal_priv": ("149.1_SOR_PRIADO_OCTU_0_25", 0, 45),   # registrado, sector privado
    "sal_pub": ("149.1_SOR_PUBICO_OCTU_0_14", 0, 45),    # registrado, sector público
    "sal_noreg": ("149.1_SOR_PRIADO_OCTU_0_28", 6, 45),  # no registrado, sector privado
    "haber_min": ("58.1_MP_0_M_24", 0, -30),             # haber mínimo jubilatorio (sin bono)
    "auh": ("165.1_AAUH_0_0_3", 0, -30),
    # Predictores de las dimensiones A, B y C (ecuaciones puente)
    "emae": ("143.3_NO_PR_2004_A_31", 0, 55),             # EMAE desestacionalizado
    "sipa_priv": ("151.1_AARIADOTAC_2012_M_26", 0, 100),  # SIPA asalariados privados, sin estac.
    "sipa_pub": ("151.1_AARIADOTAC_2012_M_25", 0, 100),   # SIPA asalariados públicos, sin estac.
    "sipa_casas": ("151.1_AARIADOTAC_2012_M_40", 0, 100), # SIPA casas particulares, sin estac.
    "eil": ("50.3_ICS_0_M_12", 0, 80),                    # Encuesta de Indicadores Laborales: empleo
    "icc": ("380.3_ICC_NACIONNAL_0_T_12", 0, -10),        # confianza del consumidor UTDT (sale en el mes)
    "icc_dur": ("380.3_DESAGREGACLES_0_T_50", 0, -10),    # ídem, subíndice bienes durables e inmuebles
}
REZAGO_BONO = -30  # el bono previsional se decreta antes de pagarse
# Meses sin dato publicado: se completan con la variación de la guía (si la hay) o con la mediana de
# la variación de los últimos 3 meses. El bono y la confianza del consumidor se mantienen constantes.
GUIA = {"sal_noreg": "sal_priv"}
PLANAS = {"bono", "icc", "icc_dur"}
DIAS_EPH = 85  # la EPH se publica ~85 días después del cierre del trimestre

IND_LABORAL = "Ingreso laboral real"
IND_BAJO = "Personas con ingreso per cápita real bajo"
DIM_D = "D. Ingresos reales"
SIGNOS_D = {IND_LABORAL: -1, IND_BAJO: +1}  # mismos signos que DIMENSIONES del 06
EXCLUIR_ESTACIONAL = ["2020T1", "2020T2", "2020T3", "2020T4", "2021T1", "2021T2"]  # como en el 06
PANDEMIA = ["2020T2", "2020T3", "2020T4", "2021T1"]

# Componentes de ingreso de la base personas (esquema viejo agregado / nuevo desagregado, 4T2023)
COMPONENTES = {
    "jub": ["V2_M", "V2_01_M", "V2_02_M", "V2_03_M",          # jubilaciones y pensiones
            "V21_M", "V21_01_M", "V21_02_M", "V21_03_M"],     # su aguinaldo
    "auh": ["V5_M", "V5_01_M"],  # AUH/AUE + Tarjeta Alimentar (el V5_M viejo incluye otros planes)
    "ipc": ["V3_M", "V4_M", "V8_M", "V9_M", "V10_M", "V11_M", "V11_01_M", "V11_02_M", "V12_M",
            "V18_M", "V19_AM", "V22_01_M", "V22_02_M", "V22_03_M", "V5_02_M", "V5_03_M"],
}
COLS_MICRO = ["CODUSU", "NRO_HOGAR", "ESTADO", "CAT_OCUP", "PP07H", "PP04A", "P21", "TOT_P12",
              "PONDIIO", "IPCF", "PONDIH"] + [c for cs in COMPONENTES.values() for c in cs]

# Clase de ingreso -> índice con que se actualiza
INDICE_DE_CLASE = {
    "sal_priv": "sal_priv",    # asalariados registrados del sector privado (y "otro" empleador)
    "sal_pub": "sal_pub",      # asalariados registrados del sector público
    "sal_noreg": "sal_noreg",  # asalariados no registrados
    "indep": "sal_noreg",      # cuentapropistas y patrones: es el índice que mejor los sigue
    "jub": "haber_min",        # haberes por encima del mínimo + bono: movilidad
    "jub_min": "haber_bono",   # haberes hasta 5% por encima del mínimo + bono
    "auh": "auh",
    "ipc": "ipc",              # resto de los ingresos no laborales: constantes en términos reales
}
CLASES = list(INDICE_DE_CLASE)
TOPE_JUB_MIN = 1.05


# --------------------------------------------------------------------------------------------
# Trimestres y meses
# --------------------------------------------------------------------------------------------
def periodo(q: str) -> pd.Period:
    return pd.Period(q.replace("T", "Q"), "Q")


def etiqueta(p: pd.Period) -> str:
    return f"{p.year}T{p.quarter}"


def desplazar(q: str, n: int) -> str:
    return etiqueta(periodo(q) + n)


def rango(desde: str, hasta: str) -> list[str]:
    """Trimestres de `desde` a `hasta`, ambos incluidos."""
    return [etiqueta(p) for p in pd.period_range(periodo(desde), periodo(hasta), freq="Q")]


def fin_trimestre(q: str) -> pd.Timestamp:
    return periodo(q).to_timestamp(how="end").normalize()


def trimestre_de(fecha: pd.Timestamp) -> str:
    return etiqueta(pd.Period(fecha, "Q"))


def meses_ref(q: str) -> list[pd.Period]:
    """Meses de referencia de los ingresos: el mes anterior a cada mes de entrevista."""
    m0 = periodo(q).asfreq("M", how="start")
    return [m0 - 1, m0, m0 + 1]


def prom_ref(s: pd.Series, q: str) -> float:
    v = s.reindex(meses_ref(q))
    return float(v.mean()) if v.notna().all() else np.nan


# --------------------------------------------------------------------------------------------
# Series de alta frecuencia
# --------------------------------------------------------------------------------------------
def _bajar_distribucion(serie_id: str) -> pd.Series | None:
    """La serie desde el CSV completo de su distribución en el catálogo (la URL y el nombre de la
    columna salen de la metadata de la API, que responde aunque los datos vengan vacíos)."""
    try:
        r = requests.get(API_SERIES, params={"ids": serie_id, "metadata": "full", "limit": 1}, timeout=60)
        r.raise_for_status()
        meta = r.json()["meta"][1]
        url, col = meta["distribution"]["downloadURL"], meta["field"]["title"]
        d = pd.read_csv(io.BytesIO(requests.get(url, timeout=180).content))
        s = pd.Series(pd.to_numeric(d[col], errors="coerce").to_numpy(),
                      index=pd.PeriodIndex(pd.to_datetime(d["indice_tiempo"]), freq="M"))
        return s.dropna() if s.notna().any() else None
    except (requests.RequestException, ValueError, KeyError, IndexError, pd.errors.ParserError):
        return None


def _bajar_serie(serie_id: str, desde: str = "2016-10-01", intentos: int = 5) -> pd.Series | None:
    """Serie de la API de datos.gob.ar (fechada como en la API) o None.

    La API falla de forma intermitente: a veces devuelve una tabla vacía (para algunas series, todo
    un día). Se reintenta, después se baja el CSV de la distribución y nunca se devuelve una serie
    vacía."""
    for k in range(intentos):
        try:
            r = requests.get(API_SERIES, params={"ids": serie_id, "format": "csv", "limit": 1000,
                                                 "start_date": desde}, timeout=60)
            r.raise_for_status()
            d = pd.read_csv(io.StringIO(r.text))
            s = pd.Series(d.iloc[:, 1].to_numpy(float), index=pd.PeriodIndex(pd.to_datetime(d.iloc[:, 0]), freq="M"))
            if s.notna().any():
                return s.dropna()
        except (requests.RequestException, pd.errors.ParserError, pd.errors.EmptyDataError, IndexError):
            pass
        if k < intentos - 1:
            time.sleep(2 * (k + 1))
    s = _bajar_distribucion(serie_id)
    return None if s is None else s[s.index >= pd.Period(desde, "M")]


def leer_bono(ruta: str) -> pd.Series:
    """Bono previsional mensual (pesos; 0 antes de sep-2022), cargado a mano en data/."""
    d = pd.read_csv(ruta, comment="#")
    s = pd.Series(d["bono"].to_numpy(float), index=pd.PeriodIndex(d["periodo"], freq="M"))
    meses = pd.period_range("2016-10", s.index[-1], freq="M")
    return s.reindex(meses).fillna(0.0)


def cargar_series(respaldo: str, bono: str, api: bool = True) -> tuple[dict, dict]:
    """Series mensuales fechadas en el mes de referencia + origen de cada una.

    Primero la API; si falla, el respaldo `respaldo` (CSV con las series tal como vienen de la API,
    sin desfasar). `actualizar_respaldo` lo regenera."""
    resp = None
    if os.path.exists(respaldo):
        resp = pd.read_csv(respaldo, index_col=0)
        resp.index = pd.PeriodIndex(resp.index, freq="M")
    series, origen = {}, {}
    for nombre, (sid, desfase, _) in SERIES.items():
        s = _bajar_serie(sid) if api else None
        origen[nombre] = "API datos.gob.ar"
        if s is None:
            if resp is None or nombre not in resp:
                raise RuntimeError(f"No hay datos para {nombre} ({sid}): falló la API y no hay respaldo")
            s, origen[nombre] = resp[nombre].dropna(), "respaldo del repo"
        s = s.copy()
        s.index = s.index - desfase
        series[nombre] = s
    series["bono"], origen["bono"] = leer_bono(bono), "data/bono_previsional.csv (manual)"
    return series, origen


def actualizar_respaldo(respaldo: str) -> pd.DataFrame:
    """Baja todas las series y reescribe el respaldo (solo si vinieron todas)."""
    d = {n: _bajar_serie(sid) for n, (sid, _, _) in SERIES.items()}
    faltan = [n for n, s in d.items() if s is None]
    if faltan:
        raise RuntimeError(f"La API no devolvió {faltan}: no se toca el respaldo")
    df = pd.DataFrame(d)
    df.index = df.index.astype(str)
    df.to_csv(respaldo, index_label="mes", lineterminator="\n")
    return df


def publicado(s: pd.Series, nombre: str, fecha: pd.Timestamp) -> pd.Series:
    """Parte de la serie que ya estaba publicada en `fecha` (simulación para el backtest)."""
    desfase, rezago = (0, REZAGO_BONO) if nombre == "bono" else SERIES[nombre][1:]
    fila_api = s.index + desfase
    pub = fila_api.to_timestamp(how="end").normalize() + pd.Timedelta(days=rezago)
    return s[pub <= fecha]


def extender(s: pd.Series, hasta: pd.Period, guia: pd.Series | None = None, plana: bool = False) -> pd.Series:
    """Completa la serie hasta el mes `hasta` (ver GUIA)."""
    s = s.dropna()
    if s.index[-1] >= hasta:
        return s
    meses = pd.period_range(s.index[-1] + 1, hasta, freq="M")
    tasa = 0.0 if plana else float(np.log(s).diff().dropna().iloc[-3:].median())
    nivel, vals = s.iloc[-1], []
    for m in meses:
        if guia is not None and m in guia.index and (m - 1) in guia.index:
            nivel *= guia[m] / guia[m - 1]
        else:
            nivel *= np.exp(tasa)
        vals.append(nivel)
    return pd.concat([s, pd.Series(vals, index=meses)])


def preparar_series(series: dict, hasta: pd.Period, fecha: pd.Timestamp | None = None) -> tuple[dict, dict]:
    """Series completas hasta `hasta` y último mes con dato real de cada una.

    Con `fecha` (backtest) se recortan antes a lo publicado en esa fecha; sin `fecha` (tiempo real)
    se usa todo lo que haya."""
    base = {n: publicado(s, n, fecha) if fecha is not None else s.dropna() for n, s in series.items()}
    datos_hasta = {n: s.index[-1] for n, s in base.items()}
    # La guía solo aporta sus meses con dato real; después, cada serie sigue su propia tendencia
    # (seguir también la tendencia de la guía empeoró el backtest: k=2 a −75 días, 14,8 -> 17,8 pts).
    S = {n: extender(s, hasta, guia=base.get(GUIA.get(n)), plana=(n in PLANAS)) for n, s in base.items()}
    S["haber_bono"] = S["haber_min"] + S["bono"].reindex(S["haber_min"].index).fillna(0.0)
    if {"sipa_priv", "sipa_pub", "sipa_casas"} <= set(S):  # asalariados registrados totales
        S["sipa_asal"] = (S["sipa_priv"] + S["sipa_pub"] + S["sipa_casas"]).dropna()
    return S, datos_hasta


def ipc_trimestral(ipc: pd.Series) -> dict:
    """IPC promedio de los meses de referencia (dic-2016 = 1), como IPC_Q del 06."""
    out = {}
    for p in pd.period_range("2017Q1", pd.Period(ipc.index[-1], "Q"), freq="Q"):
        v = prom_ref(ipc, etiqueta(p))
        if not np.isnan(v):
            out[etiqueta(p)] = v / 100
    return out


# --------------------------------------------------------------------------------------------
# Microdatos y microsimulación
# --------------------------------------------------------------------------------------------
@dataclass
class Base:
    """Microdatos de un trimestre, listos para microsimular."""
    trimestre: str
    grupo: np.ndarray    # clase (índice en CLASES) de cada ocupado con ingreso
    log_p21: np.ndarray  # log del P21 nominal de esos ocupados
    w_p21: np.ndarray    # PONDIIO
    hogar: np.ndarray    # hogar de cada persona (fila de Y)
    ipcf: np.ndarray     # IPCF nominal
    w_ipcf: np.ndarray   # PONDIH
    den_ipcf: np.ndarray  # universo del indicador de ingreso bajo (IPCF >= 0)
    Y: np.ndarray        # ingresos de cada hogar por clase (hogares × CLASES)


def _num(df: pd.DataFrame, c: str) -> pd.Series:
    return pd.to_numeric(df[c], errors="coerce") if c in df else pd.Series(np.nan, index=df.index)


def preparar_base(df: pd.DataFrame, trimestre: str, tope_jub_min: float) -> Base:
    """Arma la Base de un trimestre. `tope_jub_min`: haber (nominal, del trimestre) hasta el que un
    jubilado se actualiza con mínimo + bono en vez de con la movilidad."""
    cat, h07, a04 = _num(df, "CAT_OCUP"), _num(df, "PP07H"), _num(df, "PP04A")
    asal_reg = (cat == 3) & (h07 == 1)
    grupo = np.select([asal_reg & (a04 == 1), asal_reg, cat == 3, cat.isin([1, 2])],
                      ["sal_pub", "sal_priv", "sal_noreg", "indep"], "sal_noreg")
    col = {c: i for i, c in enumerate(CLASES)}
    g_idx = np.array([col[g] for g in grupo])
    p21 = _num(df, "P21")
    lab = p21.clip(lower=0).fillna(0) + _num(df, "TOT_P12").clip(lower=0).fillna(0)
    comp = {k: sum(_num(df, c).clip(lower=0).fillna(0) for c in cs) for k, cs in COMPONENTES.items()}
    jub_idx = np.where(comp["jub"] <= tope_jub_min, col["jub_min"], col["jub"])

    n = len(df)
    P = np.zeros((n, len(CLASES)))
    P[np.arange(n), g_idx] += lab.to_numpy()
    P[np.arange(n), jub_idx] += comp["jub"].to_numpy()
    P[:, col["auh"]] += comp["auh"].to_numpy()
    P[:, col["ipc"]] += comp["ipc"].to_numpy()
    hogar, _ = pd.factorize(df["CODUSU"].astype(str).str.strip() + "_" + df["NRO_HOGAR"].astype(str))
    Y = np.zeros((hogar.max() + 1, len(CLASES)))
    np.add.at(Y, hogar, P)

    con_ingreso = ((_num(df, "ESTADO") == 1) & (p21 > 0)).to_numpy()
    ipcf = _num(df, "IPCF")
    return Base(trimestre=trimestre, grupo=g_idx[con_ingreso], log_p21=np.log(p21.to_numpy()[con_ingreso]),
                w_p21=_num(df, "PONDIIO").fillna(0).to_numpy()[con_ingreso], hogar=hogar,
                ipcf=ipcf.to_numpy(), w_ipcf=_num(df, "PONDIH").fillna(0).to_numpy(),
                den_ipcf=(ipcf >= 0).to_numpy(), Y=Y)


def indicadores(base: Base, g: dict, ipc_x: float, umbral: float) -> dict:
    """Los dos indicadores de D con los ingresos actualizados por los factores `g` (índice ->
    factor) y deflactados con `ipc_x` (dic-2016 = 1). Con todos los factores en 1 y el IPC del
    propio trimestre se obtiene el valor oficial (mismas fórmulas que INDICADORES del 06)."""
    gv = np.array([g.get(INDICE_DE_CLASE[c], 1.0) for c in CLASES])
    laboral = np.exp(np.sum(base.w_p21 * (base.log_p21 + np.log(gv)[base.grupo])) / base.w_p21.sum()) / ipc_x
    tot = base.Y.sum(axis=1)
    f = np.where(tot > 0, (base.Y @ gv) / np.where(tot > 0, tot, 1.0), 1.0)
    with np.errstate(invalid="ignore"):
        bajo = (base.ipcf * f[base.hogar] / ipc_x) < umbral
    pct = (base.w_ipcf * bajo).sum() / (base.w_ipcf * base.den_ipcf).sum() * 100
    return {IND_LABORAL: laboral, IND_BAJO: pct}


def mediana_ponderada(v, w):
    """Igual que en el 06."""
    s = np.argsort(np.asarray(v))
    v, w = np.asarray(v)[s], np.asarray(w)[s]
    return np.interp(0.5, (np.cumsum(w) - 0.5 * w) / w.sum(), v)


def cargar_bases(load_panel, out_dir: str, series: dict) -> tuple[dict, pd.DataFrame, float]:
    """Bases de todos los trimestres, indicadores oficiales de D y umbral de ingreso bajo.

    `load_panel` es src.data_loader.load_panel (se pasa para no acoplar el módulo a la carga)."""
    S, _ = preparar_series(series, series["ipc"].index[-1])
    ipc_q = ipc_trimestral(series["ipc"])
    panel = load_panel(columns=["CODUSU", "PONDIH", "IPCF"], out_dir=out_dir)
    trims = sorted({f"{a}T{t}" for a, t in panel[["ANIO", "TRIMESTRE"]].drop_duplicates().itertuples(index=False)})
    # Umbral fijo en pesos de dic-2016: 60% de la mediana del IPCF real 2017-2019 (como el 06)
    panel["IPCF"] = pd.to_numeric(panel["IPCF"], errors="coerce")
    panel["PONDIH"] = pd.to_numeric(panel["PONDIH"], errors="coerce")
    panel["IPC_Q"] = (panel["ANIO"].astype(str) + "T" + panel["TRIMESTRE"].astype(str)).map(ipc_q)
    b = panel[panel["ANIO"].between(2017, 2019) & (panel["PONDIH"] > 0)]
    umbral = 0.6 * mediana_ponderada(b["IPCF"] / b["IPC_Q"], b["PONDIH"])
    del panel, b

    bases, oficiales = {}, {}
    for q in trims:
        p = periodo(q)
        df = load_panel(columns=COLS_MICRO, quarters=[(p.year, p.quarter)], out_dir=out_dir)
        tope = TOPE_JUB_MIN * prom_ref(S["haber_bono"], q)
        bases[q] = preparar_base(df, q, tope)
        if q in ipc_q:
            oficiales[q] = indicadores(bases[q], {}, ipc_q[q], umbral)
    return bases, pd.DataFrame(oficiales).T, umbral


# --------------------------------------------------------------------------------------------
# Normalización (copias exactas del 06) y dimensión D
# --------------------------------------------------------------------------------------------
def factores_estacionales(s: pd.Series) -> pd.Series:
    """Factor estacional aditivo por trimestre del año ('1'..'4'), como `desestacionalizar` del 06."""
    tend = s.rolling(4, center=True).mean().rolling(2).mean().shift(-1)
    trim = s.index.str[-1]
    ok = ~s.index.isin(EXCLUIR_ESTACIONAL)
    fac = (s - tend)[ok].groupby(trim[ok]).median()
    return fac - fac.mean()


def desestacionalizar(s: pd.Series) -> pd.Series:
    return s - factores_estacionales(s).reindex(s.index.str[-1]).to_numpy()


def percentil_orientado(s: pd.Series, signo: int) -> pd.Series:
    r = (signo * s.round(1)).rank(method="average")
    n = r.notna().sum()
    return (r - 1) / (n - 1) * 100 if n > 1 else r * np.nan


def dimension_D(raw: pd.DataFrame) -> pd.Series:
    """Dimensión D (0-100) a partir de los dos indicadores en sus unidades."""
    norm = pd.DataFrame({c: percentil_orientado(desestacionalizar(raw[c]), s) for c, s in SIGNOS_D.items()})
    return norm.mean(axis=1)


def D_tiempo_real(oficiales: pd.DataFrame) -> pd.Series:
    """D de cada trimestre tal como lo mostraba el 06 cuando ese trimestre era el último."""
    return pd.Series({q: dimension_D(oficiales.loc[:q])[q] for q in oficiales.index})


# --------------------------------------------------------------------------------------------
# Proyección
# --------------------------------------------------------------------------------------------
METODOS = ("estacional", "anual")
N_DERIVA, MIN_DERIVA = 8, 4  # errores recientes con que se estima la deriva (y mínimo para usarla)


def _microsim(base: Base, b: str, x: str, S: dict, umbral: float) -> dict:
    """Indicadores de D del trimestre x con los ingresos de la base b actualizados a x."""
    g = {i: prom_ref(S[i], x) / prom_ref(S[i], b) for i in set(INDICE_DE_CLASE.values())}
    return indicadores(base, g, prom_ref(S["ipc"], x) / 100, umbral)


def proyectar_indicadores(objetivo: str, base: str, bases: dict, oficiales: pd.DataFrame, series: dict,
                          umbral: float, fecha: pd.Timestamp | None = None,
                          metodo: str = "estacional", pre: tuple | None = None) -> tuple[pd.DataFrame, dict]:
    """Indicadores de D proyectados de base+1 a `objetivo` (sin corregir la deriva).

    Métodos:
    - "estacional": microsimula desde `base` (la EPH más reciente) y corrige la estacionalidad con
      los factores del 06 estimados hasta `base` (el aguinaldo cae en el T1 y el T3).
    - "anual": microsimula desde el mismo trimestre del año anterior (misma estacionalidad, pero
      con la composición de los hogares de un año atrás).
    `pre`: resultado de `preparar_series` ya calculado (para no repetirlo).
    Devuelve (indicadores por trimestre, último mes con dato real de cada serie)."""
    S, datos_hasta = pre or preparar_series(series, meses_ref(objetivo)[-1], fecha)
    fac = {c: factores_estacionales(oficiales.loc[:base, c]) for c in SIGNOS_D}
    filas = {}
    for x in rango(base, objetivo)[1:]:
        if metodo == "estacional":
            v = _microsim(bases[base], base, x, S, umbral)
            filas[x] = {c: v[c] + fac[c].get(x[-1], 0.0) - fac[c].get(base[-1], 0.0) for c in SIGNOS_D}
        else:
            b4 = desplazar(x, -4)
            filas[x] = _microsim(bases[b4], b4, x, S, umbral)
    return pd.DataFrame(filas).T, datos_hasta


def errores_k1(proy_k1: dict, oficiales: pd.DataFrame) -> pd.DataFrame:
    """Errores de proyecciones a un trimestre de la base: log(oficial/proyectado) para el ingreso
    laboral y oficial − proyectado (pp) para el ingreso bajo. `proy_k1`: trimestre -> proyección."""
    filas = {q: {IND_LABORAL: np.log(oficiales.loc[q, IND_LABORAL] / p.loc[q, IND_LABORAL]),
                 IND_BAJO: oficiales.loc[q, IND_BAJO] - p.loc[q, IND_BAJO]}
             for q, p in proy_k1.items() if q in oficiales.index}
    return pd.DataFrame(filas).T.sort_index()


def estimar_deriva(errores: pd.DataFrame, hasta: str, n: int = N_DERIVA) -> dict | None:
    """Desvío sistemático por trimestre entre la EPH y los índices: promedio de los últimos `n`
    errores a un trimestre de distancia de objetivos ya publicados hasta `hasta` (sin pandemia)."""
    e = errores[(errores.index <= hasta) & ~errores.index.isin(PANDEMIA)].tail(n)
    if len(e) < MIN_DERIVA:
        return None
    return {c: float(e[c].mean()) for c in SIGNOS_D}


def aplicar_deriva(proy: pd.DataFrame, deriva: dict | None) -> pd.DataFrame:
    """Por cada trimestre de distancia a la base, el ingreso laboral se multiplica por
    exp(deriva) y al % con ingreso bajo se le suma su deriva (pp)."""
    if not deriva:
        return proy
    out = proy.copy()
    j = np.arange(1, len(out) + 1)
    out[IND_LABORAL] = out[IND_LABORAL] * np.exp(j * deriva[IND_LABORAL])
    out[IND_BAJO] = out[IND_BAJO] + j * deriva[IND_BAJO]
    return out


def D_objetivo(hist: pd.DataFrame, proy: pd.DataFrame, objetivo: str) -> float:
    """D del objetivo con la historia oficial hasta la base y lo proyectado después."""
    return float(dimension_D(pd.concat([hist[list(SIGNOS_D)], proy]))[objetivo])


def proyectar(objetivo: str, base: str, bases: dict, oficiales: pd.DataFrame, series: dict, umbral: float,
              fecha: pd.Timestamp | None = None, metodo: str = "estacional",
              deriva: dict | None = None) -> tuple[pd.DataFrame, float, dict]:
    """(indicadores proyectados de base+1 a `objetivo`, D del objetivo, último mes con dato de cada serie)."""
    proy, datos_hasta = proyectar_indicadores(objetivo, base, bases, oficiales, series, umbral, fecha, metodo)
    proy = aplicar_deriva(proy, deriva)
    return proy, D_objetivo(oficiales.loc[:base], proy, objetivo), datos_hasta


NOMBRE_INDICE = {"ipc": "IPC", "sal_priv": "Salarios registrados privados", "sal_pub": "Salarios registrados públicos",
                 "sal_noreg": "Salarios no registrados", "haber_min": "Haber mínimo (movilidad)",
                 "haber_bono": "Haber mínimo + bono", "auh": "AUH"}


def variaciones(base: str, objetivo: str, series: dict, fecha: pd.Timestamp | None = None) -> pd.DataFrame:
    """Variación de cada índice entre los meses de referencia de la base y los del objetivo, y cuántos
    de los meses del objetivo son estimados (sin dato publicado)."""
    S, datos_hasta = preparar_series(series, meses_ref(objetivo)[-1], fecha)
    datos_hasta["haber_bono"] = min(datos_hasta["haber_min"], datos_hasta["bono"])
    filas = {}
    for i, nombre in NOMBRE_INDICE.items():
        filas[nombre] = {"Variación %": (prom_ref(S[i], objetivo) / prom_ref(S[i], base) - 1) * 100,
                         "Último mes con dato": str(datos_hasta[i]),
                         "Meses estimados": sum(m > datos_hasta[i] for m in meses_ref(objetivo))}
    return pd.DataFrame(filas).T


def errores_backtest(bt: pd.DataFrame, metodo: str = "estacional") -> pd.DataFrame:
    """Errores de la proyección final (REF_DERIVA) del backtest, en el formato de `errores_k1`."""
    d = bt[(bt["k"] == REF_DERIVA[0]) & (bt["dias"] == REF_DERIVA[1]) & (bt["metodo"] == metodo)].set_index("trimestre")
    return pd.DataFrame({IND_LABORAL: np.log(d["laboral_of"] / d["laboral"]),
                         IND_BAJO: d["bajo_of"] - d["bajo"]}).sort_index()


# --------------------------------------------------------------------------------------------
# Backtest en pseudo tiempo real
# --------------------------------------------------------------------------------------------
REF_DERIVA = (1, 80)  # horizonte (k, días) cuyos errores estiman la deriva: la proyección final


def grilla_horizontes(dias=(-75, -30, 0, 45, 80, 120), ks=(1, 2, 3)) -> list[tuple[int, int]]:
    """(k, días) posibles: k = trimestres entre la base y el objetivo; días = fecha de la proyección
    respecto del cierre del objetivo. Solo combinaciones en que la base ya podía estar publicada."""
    return [(k, d) for k in ks for d in dias if d >= DIAS_EPH - 90 * k]


def backtest(bases: dict, oficiales: pd.DataFrame, series: dict, umbral: float, objetivos: list[str],
             grilla: list[tuple[int, int]] | None = None, metodos=("estacional",)) -> pd.DataFrame:
    """Proyecta cada objetivo con los datos que había en cada fecha de la grilla y lo compara con la
    EPH oficial, sin y con corrección de deriva (`_c`; la deriva usa solo errores ya conocidos en
    esa fecha). Benchmarks: "último publicado" (el D de la base, lo que se ve sin proyección) y
    "persistencia" (los indicadores de la base corregidos por estacionalidad)."""
    grilla = list(grilla or grilla_horizontes())
    if REF_DERIVA not in grilla:
        grilla.insert(0, REF_DERIVA)
    D_rt = D_tiempo_real(oficiales)
    proys = {}
    for q in objetivos:
        for k, dias in grilla:
            b = desplazar(q, -k)
            if b not in oficiales.index or desplazar(q, -4) not in bases:
                continue
            fecha = fin_trimestre(q) + pd.Timedelta(days=dias)
            for metodo in metodos:
                proys[(q, k, dias, metodo)] = (b, proyectar_indicadores(q, b, bases, oficiales, series, umbral, fecha, metodo)[0])
    errores = errores_k1({q: p for (q, k, d, m), (_, p) in proys.items()
                          if (k, d) == REF_DERIVA and m == metodos[0]}, oficiales)
    filas = []
    for (q, k, dias, metodo), (b, proy) in proys.items():
        hist = oficiales.loc[:b]
        proy_c = aplicar_deriva(proy, estimar_deriva(errores, b))
        fac = {c: factores_estacionales(hist[c]) for c in SIGNOS_D}
        persist = {c: hist[c].iloc[-1] + fac[c].get(q[-1], 0.0) - fac[c].get(b[-1], 0.0) for c in SIGNOS_D}
        filas.append({"trimestre": q, "k": k, "dias": dias, "metodo": metodo, "base": b,
                      "laboral": proy.loc[q, IND_LABORAL], "laboral_c": proy_c.loc[q, IND_LABORAL],
                      "laboral_persist": persist[IND_LABORAL], "laboral_of": oficiales.loc[q, IND_LABORAL],
                      "bajo": proy.loc[q, IND_BAJO], "bajo_c": proy_c.loc[q, IND_BAJO],
                      "bajo_persist": persist[IND_BAJO], "bajo_of": oficiales.loc[q, IND_BAJO],
                      "D": D_objetivo(hist, proy, q), "D_c": D_objetivo(hist, proy_c, q),
                      "D_ultimo": D_rt[b], "D_of": D_rt[q]})
    bt = pd.DataFrame(filas)
    for s in ("", "_c", "_ultimo"):
        bt[f"err_D{s}"] = bt[f"D{s}"] - bt["D_of"]
    for s in ("", "_c", "_persist"):
        bt[f"err_laboral{s}_%"] = (bt[f"laboral{s}"] / bt["laboral_of"] - 1) * 100
        bt[f"err_bajo{s}_pp"] = bt[f"bajo{s}"] - bt["bajo_of"]
    return bt


def resumir(bt: pd.DataFrame, sin_pandemia: bool = True) -> pd.DataFrame:
    """Error cuadrático medio por (k, días, método): proyección sin y con deriva (`_c`) y benchmarks."""
    d = bt[~bt["trimestre"].isin(PANDEMIA)] if sin_pandemia else bt
    rmse = lambda x: float(np.sqrt(np.mean(np.square(x))))  # noqa: E731
    return d.groupby(["k", "dias", "metodo"]).agg(
        n=("err_D", "size"),
        D=("err_D", rmse), D_c=("err_D_c", rmse), D_ultimo=("err_D_ultimo", rmse),
        sesgo_D=("err_D", "mean"), sesgo_D_c=("err_D_c", "mean"),
        laboral_pct=("err_laboral_%", rmse), laboral_c_pct=("err_laboral_c_%", rmse),
        laboral_persist_pct=("err_laboral_persist_%", rmse),
        bajo_pp=("err_bajo_pp", rmse), bajo_c_pp=("err_bajo_c_pp", rmse), bajo_persist_pp=("err_bajo_persist_pp", rmse),
    )


def error_esperado(resumen: pd.DataFrame, k: int, dias: int, metodo: str = "estacional",
                   corregido: bool = True) -> pd.Series:
    """Error cuadrático medio del backtest (D, laboral_pct, bajo_pp) para el horizonte más parecido:
    el mismo k (o el más cercano) y los días más cercanos."""
    r = resumen.xs(metodo, level="metodo").reset_index()
    r = r[r["k"] == min(r["k"].unique(), key=lambda x: abs(x - k))]
    f = r.iloc[(r["dias"] - dias).abs().argsort().iloc[0]]
    s = "_c" if corregido else ""
    return pd.Series({"k": f["k"], "dias": f["dias"], "D": f[f"D{s}"],
                      "laboral_pct": f[f"laboral{s}_pct"], "bajo_pp": f[f"bajo{s}_pp"]})


# --------------------------------------------------------------------------------------------
# Dimensiones A, B y C: ecuaciones puente; termómetro completo
# --------------------------------------------------------------------------------------------
DIMENSIONES = {  # copia de DIMENSIONES del 06 (indicador -> signo)
    "A. Cantidad de empleo": {"Desocupación": +1, "Tasa de empleo": -1,
                              "Desocupación >1 año": +1, "Desocupados por despido (incl. renuncia forzada)": +1},
    "B. Calidad del empleo": {"Subocupación": +1, "Ocupados que buscan otro empleo": +1,
                              "Sin cobertura de salud": +1,
                              "Tasa de empleo asalariado registrado": -1},
    "C. Estrés de los hogares": {"Gastaron ahorros": +1, "Préstamos de familiares/amigos": +1,
                                 "Vendieron pertenencias": +1,
                                 "Alimentos de gobierno/instituciones": +1,
                                 "Alimentos de familiares/vecinos": +1},
    DIM_D: dict(SIGNOS_D),
}
DESESTACIONALIZAR = list(SIGNOS_D)  # en el 06 solo se desestacionalizan los ingresos
IND_ABC = [c for dim, cols in DIMENSIONES.items() if dim != DIM_D for c in cols]
TERMO = "Termómetro"
NIVEL = {"icc", "icc_dur"}  # predictores en nivel (el resto, en log × 100)

# Predictores de A, B y C: los mismos tres para todos los indicadores (actividad, empleo registrado
# y confianza del consumidor), sin elegirlos indicador por indicador mirando la muestra (elegir los de
# mayor correlación da un backtest parecido pero optimista: usa información del período evaluado).
PREDICTORES_ABC = ["emae", "sipa_asal", "icc_dur"]
PREDICTORES = {c: list(PREDICTORES_ABC) for c in IND_ABC}


def meses_cal(q: str) -> list[pd.Period]:
    """Meses calendario del trimestre (las preguntas de empleo y de estrategias de los hogares se
    refieren a la semana o a los meses previos a la entrevista, que se reparte en el trimestre)."""
    m0 = periodo(q).asfreq("M", how="start")
    return [m0, m0 + 1, m0 + 2]


def x_trimestral(S: dict, nombres) -> pd.DataFrame:
    """Predictores trimestrales: promedio de los meses calendario (log × 100 salvo NIVEL)."""
    out = {}
    for n in nombres:
        s = S[n]
        g = s.groupby(s.index.asfreq("Q"))
        q = g.mean()[g.count() == 3]
        q.index = [etiqueta(p) for p in q.index]
        out[n] = q if n in NIVEL else np.log(q) * 100
    return pd.DataFrame(out)


def leer_oficiales(csv06: str, oficiales_D: pd.DataFrame) -> pd.DataFrame:
    """Los 15 indicadores del termómetro: A, B y C del CSV del 06 (`pct_`), D recalculado acá."""
    d06 = pd.read_csv(csv06, sep=";", index_col=0, decimal=",")
    abc = pd.DataFrame({c: d06["pct_" + c] for c in IND_ABC})
    return pd.concat([abc, oficiales_D[list(SIGNOS_D)]], axis=1, join="inner")


def termometro(raw: pd.DataFrame) -> pd.DataFrame:
    """Dimensiones y termómetro (0-100) a partir de los indicadores en sus unidades, como el 06."""
    norm = pd.DataFrame({c: percentil_orientado(desestacionalizar(raw[c]) if c in DESESTACIONALIZAR else raw[c], s)
                         for dim in DIMENSIONES.values() for c, s in dim.items()})
    dims = pd.DataFrame({dim: norm[list(cols)].mean(axis=1) for dim, cols in DIMENSIONES.items()})
    dims[TERMO] = dims.mean(axis=1)
    return dims


def termometro_tiempo_real(oficiales: pd.DataFrame) -> pd.DataFrame:
    """Dimensiones y termómetro de cada trimestre tal como los mostró el 06 cuando era el último."""
    return pd.DataFrame({q: termometro(oficiales.loc[:q]).loc[q] for q in oficiales.index}).T


def puente(y: pd.Series, X: pd.DataFrame, base: str, objetivo: str, ar: bool = False) -> pd.Series:
    """Proyección de un indicador de A, B o C de base+1 a `objetivo`.

    Sobre el indicador desestacionalizado (factores del 06 estimados hasta la base):
        Δy_t = Σ β_j·Δx_{j,t}  [+ γ·Δy_{t-1} si `ar`]   (sin constante; MCO con los trimestres
                                                         hasta la base, sin 2020T1-2021T2)
    Sin predictores es la persistencia. El término γ (los cambios de la EPH revierten porque buena
    parte es ruido de muestra) empeoró el backtest: queda desactivado. `y`: oficiales hasta la base;
    `X`: predictores trimestrales hasta el objetivo. Devuelve el indicador proyectado (con su
    estacionalidad)."""
    y = y.loc[:base]
    fac = factores_estacionales(y)
    yd = y - fac.reindex(y.index.str[-1]).fillna(0.0).to_numpy()  # historia corta: sin factor = 0
    dy, dX = yd.diff(), X.diff()
    cols = list(X.columns)
    excl = pd.Series(dy.index.isin(EXCLUIR_ESTACIONAL), index=dy.index)
    ok = ~excl & ~excl.shift(1, fill_value=True) & dy.notna() & (dy.shift(1).notna() | (not ar))
    Xh = dX.reindex(dy.index)[cols]
    ok &= Xh.notna().all(axis=1)
    regresores = ([dy.shift(1)[ok].to_numpy()] if ar else []) + [Xh.loc[ok, c].to_numpy() for c in cols]
    coef = (np.linalg.lstsq(np.column_stack(regresores), dy[ok].to_numpy(), rcond=None)[0]
            if regresores and ok.sum() > len(regresores) else np.zeros(len(regresores)))
    gamma, beta = (coef[0], coef[1:]) if ar else (0.0, coef)
    futuro = dX.reindex(rango(base, objetivo)[1:])[cols].to_numpy()
    prev, nivel, out = dy[base], yd[base], {}
    for i, x in enumerate(rango(base, objetivo)[1:]):
        d = gamma * prev + (float(futuro[i] @ beta) if cols else 0.0)
        nivel, prev = nivel + d, d
        out[x] = nivel + fac.get(x[-1], 0.0)
    return pd.Series(out)


def proyectar_abc(objetivo: str, base: str, oficiales: pd.DataFrame, series: dict,
                  fecha: pd.Timestamp | None = None, predictores: dict | None = None, ar: bool = False,
                  pre: tuple | None = None) -> tuple[pd.DataFrame, dict]:
    """Indicadores de A, B y C proyectados de base+1 a `objetivo` (y último mes con dato de cada serie)."""
    predictores = PREDICTORES if predictores is None else predictores
    S, datos_hasta = pre or preparar_series(series, meses_cal(objetivo)[-1], fecha)
    X = x_trimestral(S, sorted({p for ps in predictores.values() for p in ps}))
    proy = pd.DataFrame({c: puente(oficiales[c], X[predictores.get(c, [])], base, objetivo, ar) for c in IND_ABC})
    return proy, datos_hasta


def proyectar_termometro(objetivo: str, base: str, bases: dict, oficiales: pd.DataFrame, series: dict,
                         umbral: float, fecha: pd.Timestamp | None = None, predictores: dict | None = None,
                         ar: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(los 15 indicadores proyectados de base+1 a `objetivo`, dimensiones y termómetro de esos
    trimestres, último mes con dato de cada serie). D por microsimulación; A, B y C por `puente`."""
    pre = preparar_series(series, meses_cal(objetivo)[-1], fecha)  # cubre también los meses de referencia de D
    proy_d, _ = proyectar_indicadores(objetivo, base, bases, oficiales, series, umbral, fecha, pre=pre)
    proy_abc, datos_hasta = proyectar_abc(objetivo, base, oficiales, series, fecha, predictores, ar, pre=pre)
    proy = pd.concat([proy_abc, proy_d], axis=1)[list(oficiales.columns)]
    termo = termometro(pd.concat([oficiales.loc[:base], proy]))
    return proy, termo.loc[proy.index], datos_hasta


def persistencia(oficiales: pd.DataFrame, base: str, objetivo: str) -> pd.Series:
    """Benchmark: cada indicador de la base corregido por estacionalidad."""
    hist = oficiales.loc[:base]
    fac = {c: factores_estacionales(hist[c]) for c in hist.columns}
    return pd.Series({c: hist[c].iloc[-1] + fac[c].get(objetivo[-1], 0.0) - fac[c].get(base[-1], 0.0)
                      for c in hist.columns})


def backtest_termometro(bases: dict, oficiales: pd.DataFrame, series: dict, umbral: float, objetivos: list[str],
                        grilla: list[tuple[int, int]] | None = None, predictores: dict | None = None,
                        ar: bool = False) -> pd.DataFrame:
    """Backtest en pseudo tiempo real del termómetro completo (formato largo: una fila por objetivo,
    horizonte y serie). `serie` = indicador, dimensión o "Termómetro"; `valor` = proyección,
    `oficial` = valor publicado (para dimensiones y termómetro, tal como lo mostró el 06 cuando ese
    trimestre era el último), `ultimo` = repetir el último publicado (dimensiones y termómetro) o
    persistencia (indicadores)."""
    grilla = list(grilla or grilla_horizontes())
    T_rt = termometro_tiempo_real(oficiales)
    filas = []
    for q in objetivos:
        for k, dias in grilla:
            b = desplazar(q, -k)
            if b not in oficiales.index or desplazar(q, -4) not in bases:
                continue
            fecha = fin_trimestre(q) + pd.Timedelta(days=dias)
            proy, termo, _ = proyectar_termometro(q, b, bases, oficiales, series, umbral, fecha, predictores, ar)
            pers = persistencia(oficiales, b, q)
            for c in oficiales.columns:
                filas.append({"trimestre": q, "k": k, "dias": dias, "base": b, "serie": c, "tipo": "indicador",
                              "valor": proy.loc[q, c], "oficial": oficiales.loc[q, c], "ultimo": pers[c]})
            for c in termo.columns:
                filas.append({"trimestre": q, "k": k, "dias": dias, "base": b, "serie": c,
                              "tipo": "termómetro" if c == TERMO else "dimensión",
                              "valor": termo.loc[q, c], "oficial": T_rt.loc[q, c], "ultimo": T_rt.loc[b, c]})
    bt = pd.DataFrame(filas)
    bt["error"] = bt["valor"] - bt["oficial"]
    bt["error_ultimo"] = bt["ultimo"] - bt["oficial"]
    return bt


def resumir_termometro(bt: pd.DataFrame, sin_pandemia: bool = True) -> pd.DataFrame:
    """RMSE por (k, días, serie) de la proyección y del benchmark, y cuánto lo mejora (%)."""
    d = bt[~bt["trimestre"].isin(PANDEMIA)] if sin_pandemia else bt
    rmse = lambda x: float(np.sqrt(np.mean(np.square(x))))  # noqa: E731
    r = d.groupby(["k", "dias", "serie"], sort=False).agg(
        n=("error", "size"), error=("error", rmse), ultimo=("error_ultimo", rmse), sesgo=("error", "mean"))
    r["mejora_%"] = (1 - r["error"] / r["ultimo"]) * 100
    return r.sort_index()


# --------------------------------------------------------------------------------------------
# Robustez del backtest
# --------------------------------------------------------------------------------------------
HORIZONTES_ROBUSTEZ = [(1, 80), (2, 0), (3, -75)]  # EPH del trimestre anterior; demorada 1 y 2 trimestres
# Versiones de un mismo trimestre con el calendario habitual de la EPH: antes del cierre la última
# EPH es la de dos trimestres atrás; desde el cierre, la del trimestre anterior.
CALENDARIO = [(2, -75), (2, -30), (1, 0), (1, 45), (1, 80)]


def _rmse(x) -> float:
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else np.nan


def _horizonte(k: int, dias: int) -> str:
    return f"k={k}, {dias:+d} días"


def _f(x: float, signo: bool = False) -> str:
    """Número con 1 decimal y coma decimal (como f1 de los notebooks)."""
    return (f"{x:+.1f}" if signo else f"{x:.1f}").replace(".", ",").replace("-", "−")


def robustez_subperiodos(bt: pd.DataFrame, corte: str = "2023T1", horizontes=HORIZONTES_ROBUSTEZ,
                         series: list[str] | None = None) -> pd.DataFrame:
    """RMSE de la proyección y de repetir el último antes y desde `corte` (sin pandemia), por
    horizonte y serie (por defecto termómetro y dimensiones)."""
    series = series or [TERMO] + list(DIMENSIONES)
    d = bt[~bt["trimestre"].isin(PANDEMIA)]
    antes = f"{d['trimestre'].min()[:4]}-{int(corte[:4]) - 1}"
    desde = f"{corte[:4]}-{d['trimestre'].max()[:4]}"
    filas = {}
    for k, dias in horizontes:
        for serie in series:
            x = d[(d["k"] == k) & (d["dias"] == dias) & (d["serie"] == serie)]
            a, b = x[x["trimestre"] < corte], x[x["trimestre"] >= corte]
            filas[(_horizonte(k, dias), serie)] = {
                f"{antes}: proyección": _rmse(a["error"]), f"{antes}: repetir el último": _rmse(a["error_ultimo"]),
                f"{desde}: proyección": _rmse(b["error"]), f"{desde}: repetir el último": _rmse(b["error_ultimo"]),
                "Trimestres": f"{len(a)} + {len(b)}"}
    out = pd.DataFrame(filas).T
    out.index.names = ["Horizonte", "Serie"]
    num = [c for c in out.columns if c != "Trimestres"]
    out[num] = out[num].astype(float)
    return out


def robustez_calibracion(bt: pd.DataFrame, horizontes=HORIZONTES_ROBUSTEZ, serie: str = TERMO,
                         minimo: int = 6) -> pd.DataFrame:
    """Por horizonte: cuántas veces le gana a repetir el último, sesgo (y su error estándar), peor error
    y cobertura de los intervalos de 95% (±1,96 × RMSE): con el RMSE de toda la muestra y con el que se
    conocía en cada fecha (errores de objetivos ya publicados en la base, al menos `minimo`)."""
    d = bt[~bt["trimestre"].isin(PANDEMIA) & (bt["serie"] == serie)]
    filas = {}
    for k, dias in horizontes:
        x = d[(d["k"] == k) & (d["dias"] == dias)].sort_values("trimestre")
        e, r = x["error"], _rmse(x["error"])
        dentro = [abs(f["error"]) <= 1.96 * _rmse(x.loc[x["trimestre"] <= f["base"], "error"])
                  for _, f in x.iterrows() if (x["trimestre"] <= f["base"]).sum() >= minimo]
        peor = x.loc[e.abs().idxmax()]
        filas[_horizonte(k, dias)] = {
            "Trimestres": len(x),
            "Le gana a repetir el último (%)": (e.abs() < x["error_ultimo"].abs()).mean() * 100,
            "Sesgo (pts)": e.mean(), "Error estándar del sesgo": e.std() / np.sqrt(len(x)),
            "Peor error (pts)": peor["error"], "Trimestre del peor error": peor["trimestre"],
            "Cobertura IC 95% (%)": (e.abs() <= 1.96 * r).mean() * 100,
            "Cobertura en tiempo real (%)": np.mean(dentro) * 100 if dentro else np.nan,
            "Trimestres en tiempo real": len(dentro)}
    out = pd.DataFrame(filas).T
    enteros = ["Trimestres", "Trimestres en tiempo real"]
    num = [c for c in out.columns if c not in enteros + ["Trimestre del peor error"]]
    out[num] = out[num].astype(float)
    out[enteros] = out[enteros].astype(int)
    return out


def convergencia(bt: pd.DataFrame, calendario=CALENDARIO, serie: str = TERMO) -> tuple[pd.DataFrame, float]:
    """Versiones sucesivas de cada trimestre con el calendario habitual: RMSE de cada versión, revisión
    media respecto de la anterior y % de revisiones que la acercan al oficial (o la dejan igual). Devuelve
    también el % de trimestres en que la última versión está más cerca del oficial que la primera."""
    d = bt[~bt["trimestre"].isin(PANDEMIA) & (bt["serie"] == serie)]
    etiquetas = [f"{dias:+d} días (base a {k} trim.)" for k, dias in calendario]
    V = pd.DataFrame({et: d[(d["k"] == k) & (d["dias"] == dias)].set_index("trimestre")["valor"]
                      for et, (k, dias) in zip(etiquetas, calendario)}).dropna()
    oficial = d[(d["k"] == calendario[-1][0]) & (d["dias"] == calendario[-1][1])].set_index("trimestre")["oficial"]
    E = V.sub(oficial.reindex(V.index), axis=0)
    rev = V.diff(axis=1)
    acerca = [np.nan] + [((E[c].abs() < E[p].abs()) | (rev[c].abs() < 0.05)).mean() * 100
                         for p, c in zip(etiquetas[:-1], etiquetas[1:])]
    tabla = pd.DataFrame({"RMSE (pts)": [_rmse(E[c]) for c in etiquetas],
                          "Revisión media (pts)": [np.nan] + [rev[c].abs().mean() for c in etiquetas[1:]],
                          "Revisiones que acercan al oficial (%)": acerca}, index=etiquetas)
    return tabla, float((E[etiquetas[-1]].abs() < E[etiquetas[0]].abs()).mean() * 100)


def dependencia_predictores(bases: dict, oficiales: pd.DataFrame, series: dict, umbral: float, objetivos: list[str],
                            base_hoy: str, objetivos_hoy: list[str], horizontes=HORIZONTES_ROBUSTEZ,
                            resumen_elegido: pd.DataFrame | None = None) -> pd.DataFrame:
    """Termómetro sacando cada predictor de A, B y C (y sin ninguno = persistencia): RMSE del backtest
    por horizonte y nowcast de hoy de cada trimestre (cada uno proyectado por separado).
    `resumen_elegido`: `resumir_termometro` del backtest principal (evita recalcular la fila elegida)."""
    variantes = {"Con los tres (elegido)": PREDICTORES}
    variantes.update({f"Sin {NOMBRE_PREDICTOR[p]}": {c: [x for x in PREDICTORES[c] if x != p] for c in IND_ABC}
                      for p in PREDICTORES_ABC})
    variantes["Sin ninguno (persistencia)"] = {c: [] for c in IND_ABC}
    filas = {}
    for nombre, pred in variantes.items():
        if pred is PREDICTORES and resumen_elegido is not None:
            r = resumen_elegido
        else:
            r = resumir_termometro(backtest_termometro(bases, oficiales, series, umbral, objetivos, list(horizontes),
                                                       predictores=pred))
        fila = {f"Backtest {_horizonte(k, dias)}": r.loc[(k, dias, TERMO), "error"] for k, dias in horizontes}
        for q in objetivos_hoy:
            fila[f"Hoy: {q}"] = proyectar_termometro(q, base_hoy, bases, oficiales, series, umbral,
                                                     predictores=pred)[1].loc[q, TERMO]
        filas[nombre] = fila
    return pd.DataFrame(filas).T


def alertas_robustez(sub: pd.DataFrame, cal: pd.DataFrame, conv: pd.DataFrame, dep: pd.DataFrame) -> list[str]:
    """Lectura automática con ✓ / ⚠ de los chequeos de robustez del termómetro.

    Umbrales: sesgo significativo si |sesgo| > 1,96 × su error estándar; intervalos angostos si cubren
    menos de 85%; convergencia si el RMSE no sube entre versiones (tolerancia 0,3 pts); dependencia
    de un predictor si sacarlo sube el error más de 20% en algún horizonte."""
    out = []
    for h, f in cal.iterrows():
        sesgo_ok = abs(f["Sesgo (pts)"]) <= 1.96 * f["Error estándar del sesgo"]
        out.append(f"{'✓' if sesgo_ok else '⚠'} {h}: sesgo {_f(f['Sesgo (pts)'], True)} pts "
                   f"({'no significativo' if sesgo_ok else 'significativo'}); le gana a repetir el último en "
                   f"{f['Le gana a repetir el último (%)']:.0f}% de los trimestres")
        cob = f["Cobertura IC 95% (%)"]
        out.append(f"{'✓' if cob >= 85 else '⚠'} {h}: los intervalos de 95% cubren el oficial en {cob:.0f}% de los "
                   f"trimestres{'' if cob >= 85 else ' (angostos)'} y en {f['Cobertura en tiempo real (%)']:.0f}% con el "
                   "error conocido en cada fecha")
    cols = list(sub.columns)
    for h in sub.index.get_level_values("Horizonte").unique():
        f = sub.loc[(h, TERMO)]
        ok = f[cols[0]] < f[cols[1]] and f[cols[2]] < f[cols[3]]
        detalle = (f"{cols[0].split(':')[0]}: {_f(f[cols[0]])} vs {_f(f[cols[1]])}; "
                   f"{cols[2].split(':')[0]}: {_f(f[cols[2]])} vs {_f(f[cols[3]])}")
        out.append(f"✓ {h}: el termómetro proyectado le gana a repetir el último en los dos subperíodos ({detalle})"
                   if ok else f"⚠ {h}: en algún subperíodo no le gana a repetir el último ({detalle})")
    r = conv["RMSE (pts)"].to_numpy()
    mono = bool(np.all(np.diff(r) <= 0.3))
    out.append(f"{'✓' if mono else '⚠'} Versiones: el error {'baja' if mono else 'no baja siempre'} a medida que llegan "
               f"datos ({' → '.join(_f(x) for x in r)})")
    base = dep.loc["Con los tres (elegido)"]
    bt_cols = [c for c in dep.columns if c.startswith("Backtest")]
    for nombre, f in dep.drop(index=["Con los tres (elegido)", "Sin ninguno (persistencia)"]).iterrows():
        suba = max((f[c] / base[c] - 1) * 100 for c in bt_cols)
        out.append(f"{'⚠' if suba > 20 else '✓'} {nombre}: el error sube hasta {suba:+.0f}%"
                   + (" -> la proyección depende de esa serie" if suba > 20 else ""))
    return out


def error_esperado_serie(resumen: pd.DataFrame, k: int, dias: int) -> tuple[pd.Series, tuple[int, int]]:
    """RMSE del backtest del termómetro (`resumir_termometro`) de cada serie para el horizonte más
    parecido: el mismo k (o el más cercano) y los días más cercanos. Devuelve (RMSE por serie, (k, días))."""
    hs = sorted({(kk, dd) for kk, dd, _ in resumen.index})
    k0 = min({kk for kk, _ in hs}, key=lambda x: abs(x - k))
    d0 = min((dd for kk, dd in hs if kk == k0), key=lambda x: abs(x - dias))
    return resumen.loc[(k0, d0), "error"], (k0, d0)


NOMBRE_PREDICTOR = {"emae": "EMAE (actividad)", "sipa_asal": "Asalariados registrados (SIPA)",
                    "icc_dur": "Confianza del consumidor: bienes durables"}


def variaciones_abc(base: str, objetivo: str, series: dict, fecha: pd.Timestamp | None = None) -> pd.DataFrame:
    """Cambio de cada predictor de A, B y C entre el trimestre base y el objetivo (en % para las
    series en log, en puntos para la confianza) y cuántos meses del objetivo son estimados."""
    S, datos_hasta = preparar_series(series, meses_cal(objetivo)[-1], fecha)
    datos_hasta["sipa_asal"] = min(datos_hasta[n] for n in ("sipa_priv", "sipa_pub", "sipa_casas"))
    X = x_trimestral(S, PREDICTORES_ABC)
    filas = {}
    for n in PREDICTORES_ABC:
        cambio = X.loc[objetivo, n] - X.loc[base, n]
        filas[NOMBRE_PREDICTOR[n]] = {
            "Cambio": f"{cambio:+.1f} pts" if n in NIVEL else f"{np.expm1(cambio / 100) * 100:+.1f}%",
            "Último mes con dato": str(datos_hasta[n]),
            "Meses estimados": sum(m > datos_hasta[n] for m in meses_cal(objetivo))}
    return pd.DataFrame(filas).T


# --------------------------------------------------------------------------------------------
# Registro de versiones
# --------------------------------------------------------------------------------------------
COLUMNAS_REGISTRO = ["fecha_corrida", "version", "trimestre", "dias_al_cierre", "base_EPH", "indicador",
                     "valor", "ic_inf", "ic_sup", "datos_hasta", "oficial", "error"]


def filas_registro(fecha: pd.Timestamp, version: str, trimestre: str, base: str, valores: pd.Series,
                   rmse: pd.Series, datos_hasta: dict) -> pd.DataFrame:
    """Filas del registro para una proyección: una por serie de `valores` (indicadores, dimensiones,
    termómetro). Los IC son ±1,96 × el RMSE del backtest de cada serie (`rmse`), acotados a 0-100
    para dimensiones y termómetro y a ≥ 0 para los indicadores."""
    z = 1.96
    datos = "; ".join(f"{n} {m}" for n, m in datos_hasta.items())
    comunes = {"fecha_corrida": fecha.strftime("%Y-%m-%d"), "version": version, "trimestre": trimestre,
               "dias_al_cierre": int((fecha - fin_trimestre(trimestre)).days), "base_EPH": base,
               "datos_hasta": datos, "oficial": np.nan, "error": np.nan}
    filas = []
    for serie, v in valores.items():
        e = rmse.get(serie, np.nan)
        tope = 100.0 if (serie in DIMENSIONES or serie == TERMO) else np.inf
        filas.append({**comunes, "indicador": serie, "valor": v,
                      "ic_inf": max(0.0, v - z * e), "ic_sup": min(tope, v + z * e)})
    return pd.DataFrame(filas, columns=COLUMNAS_REGISTRO)


def registrar(ruta: str, nuevas: pd.DataFrame) -> pd.DataFrame:
    """Agrega las filas al registro (una corrida del mismo día y versión reemplaza a la anterior)."""
    clave = ["fecha_corrida", "version", "trimestre", "indicador"]
    reg = nuevas
    if os.path.exists(ruta):
        reg = pd.concat([pd.read_csv(ruta), nuevas], ignore_index=True).drop_duplicates(clave, keep="last")
    reg = reg.sort_values(["trimestre", "indicador", "fecha_corrida"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    reg.to_csv(ruta, index=False)
    return reg


def conciliar(reg: pd.DataFrame, oficiales: pd.DataFrame, rt: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Completa el valor oficial y el error (proyectado − oficial) de las proyecciones cuyo trimestre
    ya publicó la EPH. Para dimensiones y termómetro, el oficial es el que mostró el 06 cuando ese
    trimestre era el último (`rt` = `termometro_tiempo_real`; una Series se toma como D)."""
    rt = rt.to_frame(DIM_D) if isinstance(rt, pd.Series) else rt
    reg = reg.copy()
    for i, f in reg.iterrows():
        q, serie = f["trimestre"], f["indicador"]
        if q not in oficiales.index:
            continue
        of = rt.loc[q, serie] if serie in rt.columns else oficiales.loc[q, serie] if serie in oficiales.columns else np.nan
        reg.loc[i, "oficial"] = of
        reg.loc[i, "error"] = f["valor"] - of
    return reg
