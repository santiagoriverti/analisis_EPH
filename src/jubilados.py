"""Adultos mayores en la EPH (notebook 08).

Cuántos son, con quién viven (y si viven con sus hijos o los hijos con ellos), si cobran jubilación o
pensión y cuánto, qué parte del ingreso del hogar aportan, pobreza e indigencia, trabajo, vivienda,
estrategias del hogar, salud, educación y estado civil; por región y aglomerado, con intervalos de
confianza bootstrap.

Convenciones:
- Adultos mayores (AM): varones de 65 años o más y mujeres de 60 o más (edades jubilatorias).
  Pre-jubilables: varones de 60 a 64 y mujeres de 55 a 59.
- Trimestres como texto ``"AAAATq"`` (igual que el 06 y el 07).
- Ponderadores del INDEC: ``PONDERA`` para todo salvo ingresos; ``PONDII`` para la jubilación y el
  ingreso individual (``P47T``); ``PONDIIO`` para el ingreso de la ocupación principal (``P21``);
  ``PONDIH`` para el ingreso familiar, el IPCF y la pobreza. Quien no declara ingresos tiene el
  ponderador de ingresos en 0 y los demás lo compensan (no hace falta imputar).
- Jubilación o pensión: monto ``V2_M`` (hasta 2023T3) o ``V2_01_M + V2_02_M + V2_03_M`` (desde
  2023T4, separado en por aportes, por moratoria y otras pensiones: PUAM, discapacidad, madre de 7
  hijos). La EPH no separa la jubilación de la pensión por fallecimiento. ``CAT_INAC`` no sirve para
  identificar jubilados: cambió de códigos en 2023T4 (el 20% de los AM pasó de "jubilado" a "ama de
  casa") y no viene en la base de 2026T1.
- Pobreza e indigencia: metodología del INDEC (adulto equivalente; CBT y CBA de la región, promedio
  de los tres meses calendario del trimestre). Replica la tasa oficial de personas con un error medio
  de 0,1 pp (2017S1-2025S2).
- Ingresos reales y en haberes mínimos: meses de referencia de los ingresos (el mes anterior a cada
  mes de entrevista), como el 06 y el 07; en esos meses el haber declarado se alinea mejor con el
  haber mínimo que en los meses calendario.
"""
from __future__ import annotations

import io
import os
import zipfile

import numpy as np
import pandas as pd
import requests

from src import nowcast as nc

# --------------------------------------------------------------------------------------------
# Definiciones
# --------------------------------------------------------------------------------------------
EDAD_JUB = {1: 65, 2: 60}   # varones, mujeres
EDAD_PREJ = {1: 60, 2: 55}
SEXOS = {1: "Varones", 2: "Mujeres"}
GRUPOS = ["Menores de 18", "Adultos (V 18-59, M 18-54)", "Pre-jubilables (V 60-64, M 55-59)",
          "Adultos mayores (V 65+, M 60+)"]
AM = GRUPOS[-1]
RESTO = "Resto de la población"
TRAMOS = ["Mujeres 60-64", "65 a 74", "75 a 84", "85 y más"]

REGIONES = {1: "Gran Buenos Aires", 40: "Noroeste", 41: "Noreste", 42: "Cuyo", 43: "Pampeana",
            44: "Patagonia"}
AGLOMERADOS = {
    2: "Gran La Plata", 3: "Bahía Blanca-Cerri", 4: "Gran Rosario", 5: "Gran Santa Fe",
    6: "Gran Paraná", 7: "Posadas", 8: "Gran Resistencia", 9: "Comodoro Rivadavia-Rada Tilly",
    10: "Gran Mendoza", 12: "Corrientes", 13: "Gran Córdoba", 14: "Concordia", 15: "Formosa",
    17: "Neuquén-Plottier", 18: "Santiago del Estero-La Banda", 19: "Jujuy-Palpalá",
    20: "Río Gallegos", 22: "Gran Catamarca", 23: "Gran Salta", 25: "La Rioja", 26: "Gran San Luis",
    27: "Gran San Juan", 29: "Gran Tucumán-Tafí Viejo", 30: "Santa Rosa-Toay",
    31: "Ushuaia-Río Grande", 32: "Ciudad de Buenos Aires", 33: "Partidos del GBA",
    34: "Mar del Plata", 36: "Río Cuarto", 38: "San Nicolás-Villa Constitución",
    91: "Rawson-Trelew", 93: "Viedma-Carmen de Patagones",
}

CONVIVENCIA = ["Solo/a", "Solo con su pareja", "Con hijos (sin nietos)", "Con hijos y nietos",
               "Con nietos, sin hijos", "En el hogar de un hijo/a", "Otros arreglos"]
CON_HIJOS = ["Hijos en el hogar del adulto mayor", "Adulto mayor en el hogar de un hijo/a",
             "No vive con hijos"]
TIPOS_JUB = ["Por aportes", "Por moratoria", "Otras pensiones (PUAM, no contributivas)",
             "Más de un beneficio", "No cobra"]
BANDAS_HABER = ["Menos de la mínima", "La mínima (con o sin bono)", "Más de la mínima, hasta 2",
                "De 2 a 3 mínimas", "Más de 3 mínimas"]
SITUACION_JUB = ["No cobra"] + BANDAS_HABER
ROLES = ["Jefe/a de hogar", "Cónyuge del jefe/a", "Padre, madre o suegro/a del jefe/a", "Otro parentesco"]
SEXO_TRAMOS = ["Mujeres 60-64", "Mujeres 65 a 74", "Mujeres 75 a 84", "Mujeres 85 y más",
               "Varones 65 a 74", "Varones 75 a 84", "Varones 85 y más"]
JUB_TRABAJO = ["Cobra y no trabaja", "Cobra y trabaja", "Trabaja sin jubilación", "Ni cobra ni trabaja"]
SOSTEN = ["Aportan todo el ingreso", "Más de la mitad", "Hasta la mitad", "Nada"]
TENENCIA = ["Propietario/a", "Inquilino/a", "Ocupante o prestada", "Otra (sucesión, otra)"]
COBERTURA = ["Obra social (incl. PAMI)", "Solo prepaga o mutual", "Solo plan o seguro público",
             "Sin cobertura"]
EDUCACION = ["Sin instrucción o primario incompleto", "Primario completo", "Secundario incompleto",
             "Secundario completo", "Superior incompleto", "Superior completo"]
ESTADO_CIVIL = ["Casado/a o unido/a", "Viudo/a", "Separado/a o divorciado/a", "Soltero/a"]
CATEGORIAS = {1: "Patrón/a", 2: "Cuenta propia", 3: "Asalariado/a", 4: "Trabajador/a familiar"}
EDAD_HIJOS = ["Menos de 18", "18 a 29", "30 a 44", "45 y más"]
COND_HIJOS = ["Ocupado/a", "Desocupado/a", "Estudia", "Otro inactivo/a"]
ESTRATEGIAS = {  # variables de la base hogar (últimos 3 meses; 1 = sí, 2 = no)
    "V13": "Gastaron ahorros",
    "V14": "Pidieron prestado a familiares o amigos",
    "V15": "Pidieron préstamo a bancos o financieras",
    "V16": "Compraron en cuotas o al fiado",
    "V17": "Vendieron pertenencias",
    "V6": "Recibieron mercadería o alimentos del gobierno, iglesias o escuelas",
    "V7": "Recibieron mercadería o alimentos de familiares o vecinos",
}
VIVIENDA = {  # indicador -> etiqueta (todas en % de personas)
    "HACINAMIENTO": "Hacinamiento (más de 2 personas por cuarto)",
    "HACIN_CRITICO": "Hacinamiento crítico (más de 3 por cuarto)",
    "SIN_AGUA_DENTRO": "Sin agua por cañería dentro de la vivienda",
    "SIN_CLOACA": "Sin cloaca",
    "SIN_GAS_RED": "Cocinan sin gas de red",
    "EN_VILLA": "Vivienda en villa de emergencia",
}

# Tabla de equivalencias de necesidades energéticas del INDEC (adulto equivalente), por edad y sexo
_AE_NINOS = [0.35, 0.37, 0.46, 0.51, 0.55, 0.60, 0.64, 0.66, 0.68, 0.69]       # 0 a 9 años
_AE_10_17 = {1: [0.79, 0.82, 0.85, 0.90, 0.96, 1.00, 1.03, 1.04],              # varones 10 a 17
             2: [0.70, 0.72, 0.74, 0.76, 0.76, 0.77, 0.77, 0.77]}              # mujeres 10 a 17
_AE_ADULTOS = [(18, 29, 1.02, 0.76), (30, 45, 1.00, 0.77), (46, 60, 1.00, 0.76),
               (61, 75, 0.83, 0.67), (76, 200, 0.74, 0.63)]                    # (desde, hasta, V, M)

# Columnas de los parquets que usa el notebook (load_panel saltea las que no existen en un trimestre)
COLS = [
    "CODUSU", "NRO_HOGAR", "COMPONENTE", "REGION", "AGLOMERADO", "PONDERA", "PONDII", "PONDIIO",
    "PONDIH", "CH03", "CH04", "CH06", "CH07", "CH08", "CH10", "NIVEL_ED", "ESTADO", "CAT_OCUP",
    "PP3E_TOT", "EMPLEO", "P21", "TOT_P12", "P47T", "T_VI", "V2_M", "V2_01_M", "V2_02_M", "V2_03_M",
    "V21_M", "V21_01_M", "V21_02_M", "V21_03_M", "V22_01_M", "V22_02_M", "V22_03_M", "ITF", "IPCF",
    "P_DECCF", "II1", "II7", "II8", "IV1", "IV6", "IV11", "IV12_3", "V6", "V7", "V13", "V14", "V15",
    "V16", "V17", "VII1_1", "VII1_2",
]
# Las necesarias para la serie trimestral (indicadores_trimestre)
COLS_SERIE = ["CODUSU", "NRO_HOGAR", "REGION", "PONDERA", "PONDII", "PONDIIO", "PONDIH", "CH03",
              "CH04", "CH06", "ESTADO", "P21", "P47T", "V2_M", "V2_01_M", "V2_02_M", "V2_03_M", "ITF",
              "IPCF"]

SEMILLA = 20261022  # bootstrap reproducible
B_BOOT = 200


# --------------------------------------------------------------------------------------------
# Series externas: IPC, haber mínimo, bono, canastas y pobreza oficial
# --------------------------------------------------------------------------------------------
URL_CANASTAS = {  # CBA y CBT mensuales por adulto equivalente, por región (INDEC, en datos.gob.ar)
    "cba": "https://infra.datos.gob.ar/catalog/sspm/dataset/445/distribution/445.1/download/"
           "canasta-basica-alimentaria-regiones-del-pais.csv",
    "cbt": "https://infra.datos.gob.ar/catalog/sspm/dataset/446/distribution/446.1/download/"
           "canasta-basica-total-regiones-del-pais.csv",
}
SERIES_CANASTA_NAC = {"cba": "150.1_CSTA_BARIA_0_D_26", "cbt": "150.1_CSTA_BATAL_0_D_20"}  # GBA, mensual
REG_COL = {1: "gran_buenos_aires", 40: "noroeste", 41: "noreste", 42: "cuyo", 43: "pampeana",
           44: "patagonia"}
URL_POBREZA = ("https://infra.datos.gob.ar/catalog/sspm/dataset/64/distribution/64.2/download/"
               "poblacion-con-ingresos-por-debajo-linea-pobreza-eph-continua.csv")
COLS_POBREZA = {"poblacion_pobre_pct_total_continua": "Total",
                "poblacion_pobre_pct_gba_continua": "Gran Buenos Aires",
                "poblacion_pobre_pct_region_noroeste_continua": "Noroeste",
                "poblacion_pobre_pct_region_nordeste_continua": "Noreste",
                "poblacion_pobre_pct_region_cuyo_continua": "Cuyo",
                "poblacion_pobre_pct_region_pampeana_continua": "Pampeana",
                "poblacion_pobre_pct_region_patagonia_continua": "Patagonia"}


def _bajar_csv(url: str) -> pd.DataFrame | None:
    """CSV de una distribución de datos.gob.ar con índice mensual (o None si falla)."""
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        t = pd.read_csv(io.BytesIO(r.content))
        t.index = pd.PeriodIndex(pd.to_datetime(t.pop("indice_tiempo")), freq="M")
        return t
    except (requests.RequestException, ValueError, KeyError, pd.errors.ParserError):
        return None


def _leer_respaldo(ruta: str) -> pd.DataFrame:
    t = pd.read_csv(ruta, index_col=0, comment="#")
    t.index = pd.PeriodIndex(t.index, freq="M")
    return t


def cargar_ipc_haber(respaldo: str, bono: str) -> tuple[dict, dict]:
    """IPC nacional y haber mínimo (API; si falla, el respaldo del 07) + bono previsional (manual)."""
    resp = _leer_respaldo(respaldo) if os.path.exists(respaldo) else None
    series, origen = {}, {}
    for nombre in ("ipc", "haber_min"):
        s, origen[nombre] = nc._bajar_serie(nc.SERIES[nombre][0]), "API datos.gob.ar"
        if s is None:
            if resp is None or nombre not in resp:
                raise RuntimeError(f"No hay datos de {nombre}: falló la API y no hay respaldo")
            s, origen[nombre] = resp[nombre].dropna(), f"respaldo del repo ({os.path.basename(respaldo)})"
        series[nombre] = s
    series["bono"], origen["bono"] = nc.leer_bono(bono), f"{os.path.basename(bono)} (manual)"
    return series, origen


def bajar_canastas() -> pd.DataFrame | None:
    """CBA y CBT por región (cba_<región>, cbt_<región>) y la nacional (cba_nac, cbt_nac)."""
    partes = {}
    for k, url in URL_CANASTAS.items():
        t = _bajar_csv(url)
        if t is None or not set(REG_COL.values()) <= set(t.columns):
            return None
        for col in REG_COL.values():
            partes[f"{k}_{col}"] = t[col]
    for k, sid in SERIES_CANASTA_NAC.items():
        s = nc._bajar_serie(sid, desde="2016-04-01")
        if s is None:
            return None
        partes[f"{k}_nac"] = s
    return pd.DataFrame(partes).sort_index()


def cargar_canastas(respaldo: str) -> tuple[pd.DataFrame, str]:
    t = bajar_canastas()
    if t is not None:
        return t, "datos.gob.ar (INDEC)"
    if not os.path.exists(respaldo):
        raise RuntimeError("No se pudieron bajar las canastas y no hay respaldo")
    return _leer_respaldo(respaldo), f"respaldo del repo ({os.path.basename(respaldo)})"


def actualizar_respaldo_canastas(respaldo: str) -> pd.DataFrame:
    """Baja las canastas y reescribe el respaldo (solo si vinieron todas)."""
    t = bajar_canastas()
    if t is None:
        raise RuntimeError("No se pudieron bajar las canastas: no se toca el respaldo")
    out = t.copy()
    out.index = out.index.astype(str)
    with open(respaldo, "w", encoding="utf-8", newline="\n") as f:
        f.write("# CBA y CBT mensuales por adulto equivalente (pesos), por región y nacional (GBA), INDEC via\n"
                "# datos.gob.ar. Respaldo de src/jubilados.py; se regenera con tools/probar_08_local.py --respaldos.\n")
        out.to_csv(f, index_label="mes", lineterminator="\n")
    return t


def cargar_pobreza_oficial(respaldo: str) -> tuple[pd.DataFrame, str]:
    """% de personas pobres publicado por el INDEC (semestral; índice '2017S1'), total y por región."""
    t, origen = _bajar_csv(URL_POBREZA), "datos.gob.ar (INDEC)"
    if t is not None:
        t = t[[c for c in COLS_POBREZA if c in t.columns]].rename(columns=COLS_POBREZA) * 100
        t.index = [f"{p.year}S{1 if p.month <= 6 else 2}" for p in t.index]
        return t.dropna(how="all"), origen
    if not os.path.exists(respaldo):
        raise RuntimeError("No se pudo bajar la pobreza oficial y no hay respaldo")
    return pd.read_csv(respaldo, index_col=0, comment="#"), f"respaldo del repo ({os.path.basename(respaldo)})"


def actualizar_respaldo_pobreza(respaldo: str) -> pd.DataFrame:
    """Baja la pobreza oficial y reescribe el respaldo."""
    t, origen = cargar_pobreza_oficial(respaldo)
    if origen != "datos.gob.ar (INDEC)":
        raise RuntimeError("No se pudo bajar la pobreza oficial: no se toca el respaldo")
    with open(respaldo, "w", encoding="utf-8", newline="\n") as f:
        f.write("# % de personas bajo la línea de pobreza publicado por el INDEC (31 aglomerados, semestral),\n"
                "# via datos.gob.ar. Respaldo de src/jubilados.py; se regenera con tools/probar_08_local.py --respaldos.\n")
        t.round(1).to_csv(f, index_label="semestre", lineterminator="\n")
    return t


def meses_calendario(q: str) -> list[pd.Period]:
    m0 = nc.periodo(q).asfreq("M", how="start")
    return [m0, m0 + 1, m0 + 2]


def referencias(trimestres: list[str], series: dict, canastas: pd.DataFrame) -> tuple[pd.DataFrame, pd.Period]:
    """Valores de referencia de cada trimestre.

    - ``ipc``, ``haber_min``, ``haber_bono``: promedio de los meses de referencia de los ingresos.
    - ``a_pesos_hoy``: multiplica un monto del trimestre para llevarlo a pesos del último mes con IPC.
    - ``cba_<región>``, ``cbt_<región>``: por adulto equivalente, promedio de los meses calendario
      (convención del INDEC). Si a una región le faltan meses, se completan con la canasta nacional
      por la relación región/nacional de los últimos 6 meses con dato (``canasta_estimada``)."""
    ipc = series["ipc"].dropna()
    haber = series["haber_min"].dropna()
    haber_bono = haber + series["bono"].reindex(haber.index).fillna(0.0)
    filas = {}
    for q in trimestres:
        f = {"ipc": nc.prom_ref(ipc, q), "haber_min": nc.prom_ref(haber, q),
             "haber_bono": nc.prom_ref(haber_bono, q)}
        f["a_pesos_hoy"] = ipc.iloc[-1] / f["ipc"]
        meses, estimada = meses_calendario(q), False
        for k in ("cba", "cbt"):
            nac = canastas[f"{k}_nac"].dropna()
            for col in REG_COL.values():
                s = canastas[f"{k}_{col}"].dropna()
                v = s.reindex(meses)
                if v.isna().any():
                    rel = (s / nac.reindex(s.index)).dropna().iloc[-6:].mean()
                    v = v.fillna(nac.reindex(meses) * rel)
                    estimada = True
                f[f"{k}_{col}"] = v.mean() if v.notna().all() else np.nan
        f["canasta_estimada"] = estimada
        filas[q] = f
    return pd.DataFrame.from_dict(filas, orient="index"), ipc.index[-1]


# --------------------------------------------------------------------------------------------
# Microdatos
# --------------------------------------------------------------------------------------------
def a_etiqueta(anio_trim: tuple[int, int]) -> str:
    return f"{anio_trim[0]}T{anio_trim[1]}"


def cargar(load_panel, out_dir: str, trimestres: list[str], cols: list[str] = COLS) -> pd.DataFrame:
    df = load_panel(columns=cols, quarters=[(int(q[:4]), int(q[-1])) for q in trimestres], out_dir=out_dir)
    for c in df.columns:
        if c != "CODUSU":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["q"] = df["ANIO"].astype(int).astype(str) + "T" + df["TRIMESTRE"].astype(int).astype(str)
    return df


def _col(d: pd.DataFrame, c: str) -> pd.Series:
    return d[c] if c in d else pd.Series(np.nan, index=d.index)


def adulto_equivalente(edad, sexo) -> np.ndarray:
    e = np.clip(np.asarray(edad, float), 0, None)
    s = np.asarray(sexo, float)
    out = np.full(len(e), np.nan)
    for k, v in enumerate(_AE_NINOS):
        out[e == k] = v
    for sx, vals in _AE_10_17.items():
        for k, v in enumerate(vals, start=10):
            out[(e == k) & (s == sx)] = v
    for lo, hi, v, m in _AE_ADULTOS:
        rango_e = (e >= lo) & (e <= hi)
        out[rango_e & (s == 1)], out[rango_e & (s == 2)] = v, m
    return out


def _si_no(x: pd.Series) -> np.ndarray:
    """1 = sí, 2 = no -> 1.0 / 0.0; el resto (0, 9, NaN) -> NaN."""
    return np.where(x.isin([1, 2]), (x == 1).astype(float), np.nan)


def _categoria(cond: np.ndarray, valores: np.ndarray) -> np.ndarray:
    """Valores (texto) donde `cond`, None en el resto."""
    return np.where(cond, valores, None)


def preparar(df: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Agrega a los microdatos las variables del análisis (personas; las del hogar se repiten en
    cada integrante). `ref` = salida de `referencias` para los trimestres de `df`."""
    d = df.copy()
    edad, sexo = d["CH06"].clip(lower=0), d["CH04"]
    d["ES_AM"] = edad >= sexo.map(EDAD_JUB)
    d["ES_AM_F"] = d["ES_AM"].astype(float)
    d["PREJ"] = (edad >= sexo.map(EDAD_PREJ)) & ~d["ES_AM"]
    d["GRUPO"] = np.select([edad < 18, d["ES_AM"], d["PREJ"]], [GRUPOS[0], GRUPOS[3], GRUPOS[2]], GRUPOS[1])
    d["AM_RESTO"] = np.where(d["ES_AM"], AM, RESTO)
    d["SEXO"] = sexo.map(SEXOS)
    d["TRAMO"] = _categoria(d["ES_AM"], np.select([edad < 65, edad < 75, edad < 85], TRAMOS[:3], TRAMOS[3]))
    d["SEXO_TRAMO"] = _categoria(d["ES_AM"], d["SEXO"] + " " + d["TRAMO"].astype(str).str.replace("Mujeres ", ""))
    d["REGION_N"] = d["REGION"].map(REGIONES)
    if "AGLOMERADO" in d:
        d["AGLO_N"] = d["AGLOMERADO"].map(AGLOMERADOS)
    r = ref.reindex(d["q"])

    # Jubilación o pensión (universo: PONDII > 0, que excluye a quien no declaró montos)
    nuevo = (d["ANIO"] * 10 + d["TRIMESTRE"] >= 20234).to_numpy()
    tipos = pd.DataFrame({c: _col(d, c) for c in ("V2_01_M", "V2_02_M", "V2_03_M")})
    no_resp = np.where(nuevo, (tipos == -9).any(axis=1), _col(d, "V2_M") == -9)
    monto = np.where(nuevo, tipos.clip(lower=0).sum(axis=1, min_count=1), _col(d, "V2_M"))
    valido = (d["PONDII"] > 0).to_numpy() & ~no_resp
    d["JUB_M"] = np.where(valido, np.clip(np.nan_to_num(monto, nan=0.0), 0, None), np.nan)
    d["COBRA"] = np.where(valido, (d["JUB_M"] > 0).astype(float), np.nan)
    ap, mo, ot = (tipos[c].fillna(0).to_numpy() > 0 for c in tipos)
    k = ap.astype(int) + mo + ot
    tipo = np.select([k >= 2, ap, mo, ot], [TIPOS_JUB[3], TIPOS_JUB[0], TIPOS_JUB[1], TIPOS_JUB[2]], TIPOS_JUB[4])
    d["TIPO_JUB"] = _categoria(valido & nuevo, tipo)
    hmin, hbono = r["haber_min"].to_numpy(), r["haber_bono"].to_numpy()
    j = d["JUB_M"].to_numpy()
    d["HABER_EN_MIN"] = np.where(j > 0, j / hmin, np.nan)
    banda = np.select([j < 0.95 * hmin, j <= 1.05 * hbono, j <= 2 * hmin, j <= 3 * hmin], BANDAS_HABER[:4], BANDAS_HABER[4])
    d["BANDA_HABER"] = _categoria(j > 0, banda)
    d["SITUACION_JUB"] = _categoria(valido, np.where(j > 0, banda, SITUACION_JUB[0]))
    d["COBRA_MINIMA"] = np.where(j > 0, (banda == BANDAS_HABER[1]).astype(float), np.nan)
    aguinaldo = pd.DataFrame({c: _col(d, c) for c in ("V21_M", "V21_01_M", "V21_02_M", "V21_03_M",
                                                      "V22_01_M", "V22_02_M", "V22_03_M")})
    d["JUB_TOTAL"] = np.where(valido, d["JUB_M"] + aguinaldo.clip(lower=0).sum(axis=1), np.nan)
    trabajo = d["P21"].clip(lower=0).fillna(0) + _col(d, "TOT_P12").clip(lower=0).fillna(0)
    d["ING_TRABAJO"] = np.where(valido & (d["P47T"] >= 0).to_numpy(), trabajo, np.nan)

    # Ingresos en pesos del último mes con IPC (meses de referencia, como el 06)
    a_hoy = r["a_pesos_hoy"].to_numpy()
    d["JUB_R"] = np.where(j > 0, j * a_hoy, np.nan)
    d["P47T_R"] = np.where((d["PONDII"] > 0) & (d["P47T"] >= 0), d["P47T"] * a_hoy, np.nan)
    d["IPCF_R"] = np.where((d["PONDIH"] > 0) & (d["IPCF"] >= 0), d["IPCF"] * a_hoy, np.nan)
    d["P21_R"] = np.where((d["PONDIIO"] > 0) & (d["P21"] > 0), d["P21"] * a_hoy, np.nan)

    # Composición del hogar
    d["HOG"] = d["CODUSU"] + "_" + d["NRO_HOGAR"].astype(int).astype(str) + "_" + d["q"]
    por_hogar = d.groupby("HOG", sort=False)
    d["TAM"] = por_hogar["CH03"].transform("size")
    for codigo, nombre in ((2, "N_CONYUGE"), (3, "N_HIJOS"), (5, "N_NIETOS")):
        d[nombre] = (d["CH03"] == codigo).groupby(d["HOG"]).transform("sum")
    d["N_AM"] = d["ES_AM"].groupby(d["HOG"]).transform("sum")
    d["AE"] = adulto_equivalente(d["CH06"], d["CH04"])
    d["AE_HOG"] = d["AE"].groupby(d["HOG"]).transform("sum")

    # Con quién viven (solo AM): rol en el hogar y tipología
    jefe_cony = d["CH03"].isin([1, 2])
    padre_del_jefe = d["CH03"].isin([6, 7])
    conv = np.select(
        [jefe_cony & (d["TAM"] == 1),
         jefe_cony & (d["N_HIJOS"] > 0) & (d["N_NIETOS"] > 0),
         jefe_cony & (d["N_HIJOS"] > 0),
         jefe_cony & (d["N_NIETOS"] > 0),
         jefe_cony & (d["TAM"] == 2) & (d["N_CONYUGE"] > 0),
         padre_del_jefe],
        [CONVIVENCIA[0], CONVIVENCIA[3], CONVIVENCIA[2], CONVIVENCIA[4], CONVIVENCIA[1], CONVIVENCIA[5]],
        CONVIVENCIA[6])
    hijos = np.select([jefe_cony & (d["N_HIJOS"] > 0), padre_del_jefe], CON_HIJOS[:2], CON_HIJOS[2])
    am = d["ES_AM"].to_numpy()
    rol = np.select([d["CH03"] == 1, d["CH03"] == 2, padre_del_jefe], ROLES[:3], ROLES[3])
    d["ROL"] = _categoria(am, rol)
    d["CONVIVENCIA"] = _categoria(am, conv)
    d["CON_HIJOS"] = _categoria(am, hijos)
    d["VIVE_SOLO"] = np.where(am, (conv == CONVIVENCIA[0]).astype(float), np.nan)
    d["VIVE_CON_HIJOS"] = np.where(am, (hijos != CON_HIJOS[2]).astype(float), np.nan)
    d["EN_HOGAR_HIJO"] = np.where(am, (hijos == CON_HIJOS[1]).astype(float), np.nan)

    # Qué parte del ingreso del hogar aportan los AM (hogares con ingresos completos)
    ing_am = (d["P47T"].clip(lower=0) * d["ES_AM"]).groupby(d["HOG"]).transform("sum")
    ok = ((d["PONDIH"] > 0) & (d["ITF"] > 0)).to_numpy() & am
    parte = np.clip(ing_am / d["ITF"], 0, 1).to_numpy()
    d["APORTE_AM"] = np.where(ok, 100 * parte, np.nan)
    d["SOSTEN"] = _categoria(ok, np.select([parte >= 0.995, parte > 0.5, parte > 0], SOSTEN[:3], SOSTEN[3]))
    d["AM_SOSTEN"] = np.where(ok, (parte > 0.5).astype(float), np.nan)

    # Pobreza e indigencia (metodología INDEC; personas, PONDIH)
    lp, li = np.full(len(d), np.nan), np.full(len(d), np.nan)
    for codigo, col in REG_COL.items():
        m = (d["REGION"] == codigo).to_numpy()
        lp[m], li[m] = r[f"cbt_{col}"].to_numpy()[m], r[f"cba_{col}"].to_numpy()[m]
    lp, li = lp * d["AE_HOG"].to_numpy(), li * d["AE_HOG"].to_numpy()
    okh = (d["PONDIH"] > 0).to_numpy() & ~np.isnan(lp) & d["ITF"].notna().to_numpy()
    d["POBRE"] = np.where(okh, (d["ITF"] < lp).astype(float), np.nan)
    d["INDIGENTE"] = np.where(okh, (d["ITF"] < li).astype(float), np.nan)
    d["ITF_EN_LP"] = np.where(okh & (lp > 0), d["ITF"] / lp, np.nan)  # ingreso del hogar / su línea de pobreza
    if "P_DECCF" in d:  # decil de IPCF de las personas (INDEC, desde 2023T4)
        d["DECIL"] = np.where((d["PONDIH"] > 0) & d["P_DECCF"].between(1, 10), d["P_DECCF"], np.nan)

    # Trabajo
    ocu = (d["ESTADO"] == 1).to_numpy()
    entrevista = d["ESTADO"].isin([1, 2, 3, 4]).to_numpy()
    d["OCUPADO"] = np.where(entrevista, ocu.astype(float), np.nan)
    cobra = d["COBRA"].to_numpy()
    jt = np.select([(cobra == 1) & ~ocu, (cobra == 1) & ocu, (cobra == 0) & ocu], JUB_TRABAJO[:3], JUB_TRABAJO[3])
    d["JUB_TRABAJO"] = _categoria(~np.isnan(cobra) & entrevista, jt)
    if "EMPLEO" in d:
        d["INFORMAL"] = np.where(ocu & d["EMPLEO"].isin([1, 2]), (d["EMPLEO"] == 2).astype(float), np.nan)
    if "CAT_OCUP" in d:
        d["CATEGORIA"] = _categoria(ocu & d["CAT_OCUP"].isin(list(CATEGORIAS)), d["CAT_OCUP"].map(CATEGORIAS))
    if "PP3E_TOT" in d:
        h = d["PP3E_TOT"]
        d["HORAS"] = np.where(ocu & (h > 0) & (h < 999), h, np.nan)

    # Vivienda (personas: cada uno con las condiciones de su hogar)
    if "II7" in d:
        t = d["II7"]
        d["TENENCIA"] = _categoria(t.between(1, 9), np.select([t.isin([1, 2]), t == 3, t.between(4, 7)], TENENCIA[:3], TENENCIA[3]))
        d["PROPIETARIO"] = np.where(t.between(1, 9), t.isin([1, 2]).astype(float), np.nan)
    if "II1" in d:
        pxc = d["TAM"] / d["II1"].where(d["II1"] > 0)
        d["HACINAMIENTO"] = np.where(pxc.notna(), (pxc > 2).astype(float), np.nan)
        d["HACIN_CRITICO"] = np.where(pxc.notna(), (pxc > 3).astype(float), np.nan)
    if "IV6" in d:
        d["SIN_AGUA_DENTRO"] = np.where(d["IV6"].between(1, 3), (d["IV6"] != 1).astype(float), np.nan)
    if "IV11" in d:
        d["SIN_CLOACA"] = np.where(d["IV11"].between(1, 4), (d["IV11"] != 1).astype(float), np.nan)
    if "II8" in d:
        d["SIN_GAS_RED"] = np.where(d["II8"].between(1, 4), (d["II8"] != 1).astype(float), np.nan)
    if "IV12_3" in d:
        d["EN_VILLA"] = _si_no(d["IV12_3"])

    # Estrategias del hogar
    for v in ESTRATEGIAS:
        if v in d:
            d[f"E_{v}"] = _si_no(d[v])

    # Salud, educación, estado civil y tareas de la casa
    if "CH08" in d:
        c = d["CH08"]
        cob = np.select([c.isin([1, 12, 13, 123]), c.isin([2, 23]), c == 3], COBERTURA[:3], COBERTURA[3])
        d["COBERTURA"] = _categoria(c.isin([1, 2, 3, 4, 12, 13, 23, 123]), cob)
        d["SIN_COBERTURA"] = np.where(c.isin([1, 2, 3, 4, 12, 13, 23, 123]), (c == 4).astype(float), np.nan)
    if "NIVEL_ED" in d:
        n = d["NIVEL_ED"]
        d["EDUCACION"] = _categoria(n.between(1, 7), n.map({7: EDUCACION[0], 1: EDUCACION[0], 2: EDUCACION[1],
                                                            3: EDUCACION[2], 4: EDUCACION[3], 5: EDUCACION[4],
                                                            6: EDUCACION[5]}))
        d["SECUNDARIO_COMPLETO"] = np.where(n.between(1, 7), n.isin([4, 5, 6]).astype(float), np.nan)
    if "CH07" in d:
        e = d["CH07"]
        d["ESTADO_CIVIL"] = _categoria(e.between(1, 5), e.map({1: ESTADO_CIVIL[0], 2: ESTADO_CIVIL[0],
                                                              4: ESTADO_CIVIL[1], 3: ESTADO_CIVIL[2], 5: ESTADO_CIVIL[3]}))
        d["VIUDO"] = np.where(e.between(1, 5), (e == 4).astype(float), np.nan)
    if "VII1_1" in d:
        hace = (d["COMPONENTE"] == d["VII1_1"]) | (d["COMPONENTE"] == d["VII1_2"])
        d["TAREAS_CASA"] = np.where(d["VII1_1"] > 0, hace.astype(float), np.nan)
    return d


def hijos_convivientes(d: pd.DataFrame) -> pd.DataFrame:
    """Hijos e hijastros (CH03 = 3) que viven en hogares donde un AM es jefe/a o cónyuge."""
    hogares = d.loc[d["ES_AM"] & d["CH03"].isin([1, 2]), "HOG"].unique()
    h = d[d["HOG"].isin(hogares) & (d["CH03"] == 3)].copy()
    e = h["CH06"]
    h["EDAD_HIJO"] = np.select([e < 18, e < 30, e < 45], EDAD_HIJOS[:3], EDAD_HIJOS[3])
    estudia = (h["CH10"] == 1) if "CH10" in h else pd.Series(False, index=h.index)
    h["COND_HIJO"] = np.select([h["ESTADO"] == 1, h["ESTADO"] == 2, estudia], COND_HIJOS[:3], COND_HIJOS[3])
    h["HIJO_OCUPADO"] = (h["ESTADO"] == 1).astype(float)
    return h


# --------------------------------------------------------------------------------------------
# Estimación con intervalos de confianza (bootstrap por vivienda, como el 06)
# --------------------------------------------------------------------------------------------
class Bootstrap:
    """Multiplicadores Poisson(1) por vivienda (CODUSU), los mismos en todos los trimestres: respeta
    el panel rotativo (la misma vivienda aparece en varios trimestres) y el agrupamiento de las personas
    de un mismo hogar. No conoce los estratos del diseño muestral: los IC son aproximados."""

    def __init__(self, viviendas, B: int = B_BOOT, semilla: int = SEMILLA):
        self.indice = pd.Index(pd.unique(np.asarray(viviendas)))
        self.R = np.random.default_rng(semilla).poisson(1.0, size=(len(self.indice), B)).astype(np.uint8)
        self.B = B

    def replicas(self, codusu, w) -> np.ndarray:
        vi = self.indice.get_indexer(np.asarray(codusu))
        if (vi < 0).any():
            raise ValueError("Hay viviendas sin multiplicador: crear el Bootstrap con todas las viviendas")
        return self.R[vi].astype(np.float32) * np.asarray(w, dtype=np.float32)[:, None]


def calidad(n: int, cv: float) -> str:
    """Criterio del INDEC para el coeficiente de variación, más un mínimo de casos."""
    if n < 50 or (cv == cv and cv > 1 / 3):
        return "no confiable"
    if n < 100 or (cv == cv and cv > 0.2):
        return "con cautela"
    return ""


def _mediana(v: np.ndarray, w: np.ndarray):
    """Mediana ponderada (primer valor cuyo peso acumulado llega a la mitad). `w`: (n,) o (n, B)."""
    o = np.argsort(v, kind="stable")
    c = np.cumsum(w[o], axis=0)
    return v[o][(c >= c[-1] / 2).argmax(axis=0)]


def _fila(punto: float, rep: np.ndarray, n: int, es_pct: bool) -> dict:
    lo, hi = np.nanpercentile(rep, [2.5, 97.5])
    m = np.nanmean(rep)
    ic_inf, ic_sup = punto - (m - lo), punto + (hi - m)  # centrado en el valor (como el 06)
    if es_pct:
        ic_inf, ic_sup = max(ic_inf, 0.0), min(ic_sup, 100.0)
    cv = float(np.nanstd(rep) / abs(punto)) if punto else np.nan
    return {"valor": punto, "ic_inf": ic_inf, "ic_sup": ic_sup, "n": n, "cv": cv, "calidad": calidad(n, cv)}


def _grupos(sub: pd.DataFrame, por, orden, total):
    if por is None:
        return [("Total", np.ones(len(sub), bool))]
    g = sub[por]
    cats = orden if orden is not None else sorted(g.dropna().unique())
    claves = [(c, (g == c).to_numpy()) for c in cats]
    if total:
        claves.append((total, np.ones(len(sub), bool)))
    return claves


def _universo(d, peso, filtro, cols):
    m = (d[peso] > 0).to_numpy()
    if filtro is not None:
        m &= np.asarray(filtro, dtype=bool)
    for c in cols:
        m &= d[c].notna().to_numpy()
    return d.loc[m]


def estimar(d: pd.DataFrame, bs: Bootstrap, valor: str | None, peso: str, por: str | None = None,
            tipo: str = "pct", filtro=None, orden=None, total: str | None = None, n_trim: int = 1) -> pd.DataFrame:
    """Valor, IC 95%, casos (n), coeficiente de variación y calidad, en total o por grupo.

    tipo: 'pct' (% de `valor` = 1 entre los casos con dato), 'media', 'mediana' o 'total' (suma de
    los ponderadores dividida por `n_trim`, para promediar varios trimestres). `filtro`: máscara del
    universo. `total`: nombre de una fila con todos los grupos juntos."""
    sub = _universo(d, peso, filtro, [] if tipo == "total" else [valor] + ([por] if por else []))
    filas = {}
    for nombre, mk in _grupos(sub, por, orden, total):
        s = sub.loc[mk]
        if len(s) == 0:
            filas[nombre] = {"valor": np.nan, "ic_inf": np.nan, "ic_sup": np.nan, "n": 0, "cv": np.nan,
                             "calidad": "sin casos"}
            continue
        w = s[peso].to_numpy(float)
        W = bs.replicas(s["CODUSU"], w)
        if tipo == "total":
            punto, rep = w.sum() / n_trim, W.sum(axis=0) / n_trim
        else:
            v = s[valor].to_numpy(float)
            if tipo == "mediana":
                punto, rep = float(_mediana(v, w)), _mediana(v, W)
            else:
                esc = 100.0 if tipo == "pct" else 1.0
                punto, rep = esc * (w @ v) / w.sum(), esc * (v @ W) / W.sum(axis=0)
        filas[nombre] = _fila(float(punto), rep, len(s), tipo == "pct")
    out = pd.DataFrame.from_dict(filas, orient="index")
    out.index.name = por or "grupo"
    return out


def distribucion(d: pd.DataFrame, bs: Bootstrap, var: str, peso: str, categorias: list, por: str | None = None,
                 filtro=None, orden=None, total: str | None = None) -> pd.DataFrame:
    """% de cada categoría de `var` (suman 100 en cada grupo), con IC. Índice (grupo, categoría)."""
    sub = _universo(d, peso, filtro, [var] + ([por] if por else []))
    filas = []
    for nombre, mk in _grupos(sub, por, orden, total):
        s = sub.loc[mk]
        if len(s) == 0:
            continue
        w = s[peso].to_numpy(float)
        W = bs.replicas(s["CODUSU"], w)
        tot, tot_r = w.sum(), W.sum(axis=0)
        x_all = s[var].to_numpy()
        for c in categorias:
            x = (x_all == c).astype(float)
            filas.append({"grupo": nombre, "categoria": c,
                          **_fila(100 * (w @ x) / tot, 100 * (x @ W) / tot_r, len(s), True)})
    out = pd.DataFrame(filas).set_index(["grupo", "categoria"])
    out.index.names = [por or "grupo", var]
    return out


def juntar(*partes: pd.DataFrame) -> pd.DataFrame:
    """Une resultados de `estimar` (o de `distribucion`) calculados con distintos cortes; el primer
    nivel del índice pasa a llamarse 'grupo'."""
    return pd.concat([p.rename_axis(["grupo"] + list(p.index.names[1:])) for p in partes])


def ancho(dist: pd.DataFrame, categorias: list, grupos: list | None = None) -> pd.DataFrame:
    """Tabla grupos x categorías con los valores de `distribucion` (para gráficos apilados)."""
    t = dist["valor"].unstack(dist.index.names[1])[categorias]
    return t.reindex(grupos) if grupos is not None else t


def varios(d: pd.DataFrame, bs: Bootstrap, indicadores: dict, peso: str, por: str | None = None, filtro=None,
           orden=None, total: str | None = None) -> pd.DataFrame:
    """Varios indicadores 0/1 (columna -> etiqueta) con el mismo ponderador. Índice (indicador, grupo)."""
    partes = {et: estimar(d, bs, col, peso, por=por, filtro=filtro, orden=orden, total=total)
              for col, et in indicadores.items() if col in d}
    out = pd.concat(partes, names=["indicador"])
    return out


def indicadores_trimestre(d: pd.DataFrame, bs: Bootstrap) -> pd.DataFrame:
    """Indicadores de la serie trimestral (un trimestre ya preparado). Índice: indicador."""
    am = d["ES_AM"].to_numpy()
    cobra = am & (d["COBRA"] == 1).to_numpy()
    d = d.assign(ES_AM_F=d["ES_AM"].astype(float))
    defs = {
        "Adultos mayores (% de la población)": ("ES_AM_F", "PONDERA", "pct", None),
        "Adultos mayores (millones)": (None, "PONDERA", "total", am),
        "Cobran jubilación o pensión (%)": ("COBRA", "PONDII", "pct", am),
        "Cobran la mínima (% de los que cobran)": ("COBRA_MINIMA", "PONDII", "pct", cobra),
        "Haber mediano (pesos de hoy)": ("JUB_R", "PONDII", "mediana", cobra),
        "Viven solos (%)": ("VIVE_SOLO", "PONDERA", "pct", am),
        "Viven con hijos (%)": ("VIVE_CON_HIJOS", "PONDERA", "pct", am),
        "Viven en el hogar de un hijo/a (%)": ("EN_HOGAR_HIJO", "PONDERA", "pct", am),
        "Pobreza: adultos mayores (%)": ("POBRE", "PONDIH", "pct", am),
        "Pobreza: resto de la población (%)": ("POBRE", "PONDIH", "pct", ~am),
        "Pobreza: total (%)": ("POBRE", "PONDIH", "pct", None),
        "Indigencia: adultos mayores (%)": ("INDIGENTE", "PONDIH", "pct", am),
        "Indigencia: resto de la población (%)": ("INDIGENTE", "PONDIH", "pct", ~am),
        "Trabajan (% ocupados)": ("OCUPADO", "PONDERA", "pct", am),
        "IPCF mediano: adultos mayores (pesos de hoy)": ("IPCF_R", "PONDIH", "mediana", am),
        "IPCF mediano: resto de la población (pesos de hoy)": ("IPCF_R", "PONDIH", "mediana", ~am),
    }
    filas = {}
    for nombre, (col, peso, tipo, filtro) in defs.items():
        e = estimar(d, bs, col, peso, tipo=tipo, filtro=filtro).iloc[0].to_dict()
        if nombre == "Adultos mayores (millones)":
            for c in ("valor", "ic_inf", "ic_sup"):
                e[c] /= 1e6
        filas[nombre] = e
    return pd.DataFrame.from_dict(filas, orient="index")


def sumas_pobreza(d: pd.DataFrame) -> pd.DataFrame:
    """Personas pobres y total (sumas de PONDIH) por región y en total, para armar semestres."""
    s = d.loc[d["POBRE"].notna() & (d["PONDIH"] > 0)]
    w = s["PONDIH"]
    t = pd.DataFrame({"pobres": (w * s["POBRE"]).groupby(s["REGION_N"]).sum(), "total": w.groupby(s["REGION_N"]).sum()})
    t.loc["Total"] = [(w * s["POBRE"]).sum(), w.sum()]
    return t


def pobreza_semestral(sumas: dict) -> pd.DataFrame:
    """% de personas pobres por semestre (filas, '2017S1') y región (columnas), como publica el INDEC,
    a partir de {trimestre: sumas_pobreza(...)}. Solo semestres con sus dos trimestres."""
    largo = pd.concat(sumas, names=["q", "region"]).reset_index()
    largo["sem"] = [f"{q[:4]}S{1 if int(q[-1]) <= 2 else 2}" for q in largo["q"]]
    g = largo.groupby(["sem", "region"]).agg(pobres=("pobres", "sum"), total=("total", "sum"), n=("q", "size"))
    return (100 * g["pobres"] / g["total"])[g["n"] == 2].unstack("region")


# --------------------------------------------------------------------------------------------
# Formato y gráficos
# --------------------------------------------------------------------------------------------
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
TINTA, TEXTO2, GRIS, GRILLA = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
_AZULES = {250: "#86b6ef", 300: "#6da7ec", 350: "#5598e7", 400: "#3987e5", 450: "#2a78d6", 500: "#256abf",
           550: "#1c5cab", 600: "#184f95", 650: "#104281", 700: "#0d366b"}


def rampa(n: int) -> list[str]:
    """n pasos ordinales de la rampa azul (de claro a oscuro, el más claro con contraste 2:1)."""
    pasos = {2: [300, 600], 3: [250, 450, 650], 4: [250, 400, 550, 700], 5: [250, 350, 500, 600, 700],
             6: [250, 300, 400, 500, 600, 700]}[n]
    return [_AZULES[p] for p in pasos]


def estilo():
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.figsize": (11, 5.5), "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRILLA, "grid.linewidth": 0.8, "axes.edgecolor": GRIS,
        "axes.labelcolor": TEXTO2, "xtick.color": TEXTO2, "ytick.color": TEXTO2, "font.size": 10,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "legend.frameon": False,
    })


def num(x: float, dec: int = 1, signo: bool = False) -> str:
    """Número con separador de miles '.', coma decimal y signo menos tipográfico."""
    if x is None or x != x:
        return "s/d"
    s = f"{x:+,.{dec}f}" if signo else f"{x:,.{dec}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".").replace("-", "−")


def pct(x: float, dec: int = 1) -> str:
    return num(x, dec) + "%"


def pesos(x: float) -> str:
    return "$" + num(x, 0)


MARCA = {"con cautela": "*", "no confiable": "**"}
NOTA_CALIDAD = ("IC 95% bootstrap por vivienda. * coeficiente de variación 20-33% o menos de 100 casos "
                "(usar con cautela); ** más de 33% o menos de 50 casos (no confiable).")


def con_ic(fila, fmt=pct) -> str:
    return f"{fmt(fila['valor'])} ({fmt(fila['ic_inf'])} a {fmt(fila['ic_sup'])}){MARCA.get(fila['calidad'], '')}"


def tabla_legible(res: pd.DataFrame, fmt=pct) -> pd.Series:
    """Serie de textos 'valor (IC)' para mostrar en pantalla."""
    return res.apply(lambda f: con_ic(f, fmt), axis=1)


def _texto_sobre(color: str) -> str:
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return TINTA if lum > 0.55 else "white"


def barras_ic(ax, res: pd.DataFrame, color: str = COLORES[0], fmt=pct, orden=None, xmax=None):
    """Barras horizontales con IC 95% y el valor (las estimaciones poco precisas, marcadas)."""
    r = res if orden is None else res.reindex(orden)
    y = np.arange(len(r))[::-1]
    ax.barh(y, r["valor"], color=color, height=0.62, zorder=2)
    ax.errorbar(r["valor"], y, xerr=[(r["valor"] - r["ic_inf"]).clip(lower=0), (r["ic_sup"] - r["valor"]).clip(lower=0)],
                fmt="none", ecolor=TINTA, elinewidth=1, capsize=2.5, zorder=3)
    tope = np.nanmax(r["ic_sup"]) if xmax is None else xmax
    for yi, (_, f) in zip(y, r.iterrows()):
        if f["valor"] == f["valor"]:
            ax.text(f["ic_sup"] + tope * 0.015, yi, fmt(f["valor"]) + MARCA.get(f["calidad"], ""),
                    va="center", color=TINTA, fontsize=9)
    ax.set_yticks(y, r.index)
    ax.set_xlim(0, tope * 1.18)
    ax.grid(axis="y", visible=False)


def barras_agrupadas(ax, res: pd.DataFrame, series: list, grupos: list, colores=None, fmt=pct, nombres=None):
    """Barras horizontales agrupadas con IC: `res` con índice (serie, grupo)."""
    colores = colores or COLORES
    n = len(series)
    alto = 0.8 / n
    y0 = np.arange(len(grupos))[::-1]
    tope = np.nanmax(res["ic_sup"])
    for i, s in enumerate(series):
        r = res.loc[s].reindex(grupos)
        y = y0 + (n - 1 - i - (n - 1) / 2) * alto
        ax.barh(y, r["valor"], height=alto * 0.9, color=colores[i], label=(nombres or series)[i], zorder=2)
        ax.errorbar(r["valor"], y, xerr=[(r["valor"] - r["ic_inf"]).clip(lower=0), (r["ic_sup"] - r["valor"]).clip(lower=0)],
                    fmt="none", ecolor=TINTA, elinewidth=0.9, capsize=2, zorder=3)
        for yi, (_, f) in zip(y, r.iterrows()):
            if f["valor"] == f["valor"]:
                ax.text(f["ic_sup"] + tope * 0.012, yi, fmt(f["valor"]) + MARCA.get(f["calidad"], ""),
                        va="center", color=TINTA, fontsize=8.5)
    ax.set_yticks(y0, grupos)
    ax.set_xlim(0, tope * 1.2)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")


def apiladas(ax, tabla: pd.DataFrame, colores: list, minimo: float = 5.0, leyenda: bool = True, ncol: int = 3):
    """Barras 100% horizontales (filas = grupos, columnas = categorías en orden), con el valor dentro
    de los segmentos de al menos `minimo` puntos y 2 px de separación entre segmentos."""
    y = np.arange(len(tabla))[::-1]
    izq = np.zeros(len(tabla))
    for j, c in enumerate(tabla.columns):
        v = tabla[c].fillna(0).to_numpy()
        ax.barh(y, v, left=izq, color=colores[j], edgecolor="white", linewidth=1.5, height=0.66, label=c, zorder=2)
        for yi, vi, li in zip(y, v, izq):
            if vi >= minimo:
                ax.text(li + vi / 2, yi, num(vi, 0), ha="center", va="center", fontsize=8.5,
                        color=_texto_sobre(colores[j]))
        izq += v
    ax.set_yticks(y, tabla.index)
    ax.set_xlim(0, 100)
    ax.set_xlabel("%")
    ax.grid(False)
    if leyenda:
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=ncol, fontsize=8.5)


def puntos_ic(ax, res: pd.DataFrame, color: str = COLORES[0], ref: float | None = None, fmt=pct, etiqueta_ref=None):
    """Puntos con IC, ordenados de menor a mayor (para regiones y aglomerados)."""
    r = res.dropna(subset=["valor"]).sort_values("valor")
    y = np.arange(len(r))
    ax.hlines(y, r["ic_inf"], r["ic_sup"], color=color, lw=2, alpha=0.45, zorder=2)
    ax.scatter(r["valor"], y, s=34, color=color, edgecolor="white", linewidth=1, zorder=3)
    ax.set_yticks(y, [f"{i}{MARCA.get(c, '')}" for i, c in zip(r.index, r["calidad"])])
    if ref is not None:
        ax.axvline(ref, color=GRIS, ls="--", lw=1, zorder=1)
        if etiqueta_ref:
            ax.text(ref, len(r) - 0.3, f" {etiqueta_ref}: {fmt(ref)}", color=TEXTO2, fontsize=8.5, va="bottom")
    ax.grid(axis="y", visible=False)


def linea_ic(ax, res: pd.DataFrame, color: str, etiqueta: str, x=None, lw: float = 2, alpha: float = 1.0):
    """Serie con banda de IC 95% (índice: trimestres 'AAAATq')."""
    x = np.arange(len(res)) if x is None else x
    ax.fill_between(x, res["ic_inf"].astype(float), res["ic_sup"].astype(float), color=color, alpha=0.18, lw=0)
    ax.plot(x, res["valor"].astype(float), color=color, lw=lw, alpha=alpha, label=etiqueta)


def eje_trimestres(ax, trimestres: list[str]):
    """Marcas en el primer trimestre de cada año."""
    pos = [i for i, q in enumerate(trimestres) if q.endswith("T1")]
    ax.set_xticks(pos, [trimestres[i][:4] for i in pos])
    ax.set_xlim(-0.5, len(trimestres) - 0.5)


# --------------------------------------------------------------------------------------------
# Exportar
# --------------------------------------------------------------------------------------------
def exportar(tablas: dict, descripciones: dict, out_dir: str, resumen: str | None = None,
             nombre: str = "jubilados_EPH") -> dict:
    """Excel (hoja Índice + una hoja por tabla), un CSV por tabla (';' y coma decimal), el resumen en
    Markdown y un ZIP con todo lo que haya en `out_dir` (incluidos los gráficos)."""
    tab_dir = os.path.join(out_dir, "tablas")
    os.makedirs(tab_dir, exist_ok=True)
    xlsx = os.path.join(out_dir, f"{nombre}.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        pd.DataFrame({"Hoja": list(tablas), "Contenido": [descripciones.get(k, "") for k in tablas]}).to_excel(
            w, sheet_name="Índice", index=False)
        for k, t in tablas.items():
            t.to_excel(w, sheet_name=k[:31])
    for k, t in tablas.items():
        t.to_csv(os.path.join(tab_dir, f"{k}.csv"), sep=";", decimal=",", encoding="utf-8-sig")
    if resumen is not None:
        with open(os.path.join(out_dir, f"{nombre}_resumen.md"), "w", encoding="utf-8") as f:
            f.write(resumen)
    zpath = os.path.join(out_dir, f"{nombre}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _, archivos in os.walk(out_dir):
            for a in archivos:
                if a.endswith(".zip"):
                    continue
                p = os.path.join(raiz, a)
                z.write(p, os.path.relpath(p, out_dir))
    return {"excel": xlsx, "csv": tab_dir, "zip": zpath}
