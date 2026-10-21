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
}
REZAGO_BONO = -30  # el bono previsional se decreta antes de pagarse
# Meses sin dato publicado: se completan con la variación de la guía (si la hay) o con la mediana de
# la variación de los últimos 3 meses. El bono se mantiene constante.
GUIA = {"sal_noreg": "sal_priv"}
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
def _bajar_serie(serie_id: str, desde: str = "2016-10-01", intentos: int = 5) -> pd.Series | None:
    """Serie de la API de datos.gob.ar (fechada como en la API) o None.

    La API falla de forma intermitente: a veces devuelve una tabla vacía. Se reintenta y nunca se
    devuelve una serie vacía."""
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
        time.sleep(2 * (k + 1))
    return None


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
    S = {n: extender(s, hasta, guia=base.get(GUIA.get(n)), plana=(n == "bono")) for n, s in base.items()}
    S["haber_bono"] = S["haber_min"] + S["bono"].reindex(S["haber_min"].index).fillna(0.0)
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
                          metodo: str = "estacional") -> tuple[pd.DataFrame, dict]:
    """Indicadores de D proyectados de base+1 a `objetivo` (sin corregir la deriva).

    Métodos:
    - "estacional": microsimula desde `base` (la EPH más reciente) y corrige la estacionalidad con
      los factores del 06 estimados hasta `base` (el aguinaldo cae en el T1 y el T3).
    - "anual": microsimula desde el mismo trimestre del año anterior (misma estacionalidad, pero
      con la composición de los hogares de un año atrás).
    Devuelve (indicadores por trimestre, último mes con dato real de cada serie)."""
    S, datos_hasta = preparar_series(series, meses_ref(objetivo)[-1], fecha)
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
# Registro de versiones
# --------------------------------------------------------------------------------------------
COLUMNAS_REGISTRO = ["fecha_corrida", "version", "trimestre", "dias_al_cierre", "base_EPH", "indicador",
                     "valor", "ic_inf", "ic_sup", "datos_hasta", "oficial", "error"]


def filas_registro(fecha: pd.Timestamp, version: str, trimestre: str, base: str, proy: pd.DataFrame, D: float,
                   err: pd.Series, datos_hasta: dict) -> pd.DataFrame:
    """Filas del registro para una proyección (los IC usan el error del backtest, ±1,96 × RMSE)."""
    z = 1.96
    v_lab, v_bajo = proy.loc[trimestre, IND_LABORAL], proy.loc[trimestre, IND_BAJO]
    datos = "; ".join(f"{n} {m}" for n, m in datos_hasta.items())
    comunes = {"fecha_corrida": fecha.strftime("%Y-%m-%d"), "version": version, "trimestre": trimestre,
               "dias_al_cierre": int((fecha - fin_trimestre(trimestre)).days), "base_EPH": base,
               "datos_hasta": datos, "oficial": np.nan, "error": np.nan}
    filas = [
        {**comunes, "indicador": IND_LABORAL, "valor": v_lab,
         "ic_inf": v_lab * (1 - z * err["laboral_pct"] / 100), "ic_sup": v_lab * (1 + z * err["laboral_pct"] / 100)},
        {**comunes, "indicador": IND_BAJO, "valor": v_bajo,
         "ic_inf": v_bajo - z * err["bajo_pp"], "ic_sup": v_bajo + z * err["bajo_pp"]},
        {**comunes, "indicador": DIM_D, "valor": D,
         "ic_inf": max(0.0, D - z * err["D"]), "ic_sup": min(100.0, D + z * err["D"])},
    ]
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


def conciliar(reg: pd.DataFrame, oficiales: pd.DataFrame, D_rt: pd.Series) -> pd.DataFrame:
    """Completa el valor oficial y el error de las proyecciones cuyo trimestre ya publicó la EPH.

    El D oficial es el que mostró el 06 cuando ese trimestre era el último (`D_tiempo_real`)."""
    reg = reg.copy()
    for i, f in reg.iterrows():
        q = f["trimestre"]
        if q not in oficiales.index:
            continue
        of = D_rt[q] if f["indicador"] == DIM_D else oficiales.loc[q, f["indicador"]]
        reg.loc[i, "oficial"] = of
        reg.loc[i, "error"] = f["valor"] - of
    return reg
