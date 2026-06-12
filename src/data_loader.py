"""
Carga de bases EPH combinando pyeph (fuente principal) con bases manuales
en data/raw/ para los trimestres que pyeph todavía no tiene disponibles.

Uso típico en un notebook:

    from src.data_loader import load_eph

    df = load_eph(year=2024, period=4, base_type="individual")
"""

import glob
import os

import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def _period_tag(year: int, period: int) -> str:
    """Convierte (2024, 4) -> 'T424' (formato usado en nombres de archivo del INDEC)."""
    return f"T{period}{str(year)[-2:]}"


def _load_from_raw(year: int, period: int, base_type: str) -> pd.DataFrame | None:
    """Busca una base manual en data/raw/ para el trimestre pedido.

    Espera archivos nombrados como usu_<base_type>_T<Q><YY>.txt o .xls
    (ej: usu_individual_T424.txt).
    """
    tag = _period_tag(year, period)
    pattern = os.path.join(RAW_DIR, f"usu_{base_type}_{tag}.*")
    matches = glob.glob(pattern)
    if not matches:
        return None

    path = matches[0]
    if path.endswith(".txt"):
        return pd.read_csv(path, sep=";", encoding="latin1")
    if path.endswith((".xls", ".xlsx")):
        return pd.read_excel(path)
    raise ValueError(f"Formato no soportado para {path}")


def load_eph(year: int, period: int, base_type: str = "individual") -> pd.DataFrame:
    """Carga la base EPH de un trimestre, priorizando pyeph y cayendo a data/raw/.

    Parameters
    ----------
    year : int
        Año de la encuesta (ej. 2024).
    period : int
        Trimestre (1 a 4).
    base_type : str
        "individual" o "hogar".
    """
    try:
        import pyeph

        return pyeph.get(data="eph", year=year, period=period, base_type=base_type)
    except Exception:
        df = _load_from_raw(year, period, base_type)
        if df is None:
            raise FileNotFoundError(
                f"No se encontró la base EPH {base_type} {year}T{period} "
                f"ni en pyeph ni en data/raw/ "
                f"(se esperaba un archivo usu_{base_type}_{_period_tag(year, period)}.txt o .xls)"
            )
        return df


def list_available_quarters(base_type: str = "individual") -> list[str]:
    """Lista los trimestres disponibles como bases manuales en data/raw/."""
    pattern = os.path.join(RAW_DIR, f"usu_{base_type}_T*.*")
    return sorted(os.path.basename(p) for p in glob.glob(pattern))


# Claves de vínculo entre la base de hogares y la de individuos.
HOGAR_KEYS = ["CODUSU", "NRO_HOGAR"]

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def merge_individual_hogar(df_individual: pd.DataFrame, df_hogar: pd.DataFrame) -> pd.DataFrame:
    """Une la base de individuos con la de hogares por CODUSU + NRO_HOGAR.

    Las columnas que están en ambas bases (además de las claves) se mantienen
    con el sufijo "_hogar" del lado de la base de hogares.
    """
    overlap = (set(df_individual.columns) & set(df_hogar.columns)) - set(HOGAR_KEYS)
    df_hogar = df_hogar.rename(columns={c: f"{c}_hogar" for c in overlap})
    return df_individual.merge(df_hogar, on=HOGAR_KEYS, how="left", validate="m:1")


def _fix_mixed_type_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a string las columnas object con tipos mezclados (ej. int y str).

    Esto evita errores de pyarrow al exportar a parquet, que requiere que cada
    columna tenga un único tipo (algunas columnas de la EPH, como CH05, vienen
    con valores numéricos y de texto mezclados en distintos trimestres/bases).
    """
    for col in df.select_dtypes(include="object").columns:
        types = df[col].dropna().map(type).unique()
        if len(types) > 1:
            df[col] = df[col].astype(str)
    return df


def build_panel(quarters: list[tuple[int, int]], save: bool = True) -> pd.DataFrame:
    """Construye un panel combinando individuo+hogar para una lista de trimestres.

    Para cada (year, period) en `quarters`:
      - carga la base individual y la de hogares (pyeph o data/raw),
      - las une por CODUSU + NRO_HOGAR,
      - agrega columnas ANIO y TRIMESTRE.

    Si `save=True`, además de devolver el panel combinado, guarda en
    `data/processed/` un parquet por trimestre (`eph_<TyyTQQ>.parquet`) y el
    panel completo (`eph_panel.parquet`).
    """
    frames = []
    for year, period in quarters:
        df_ind = load_eph(year, period, base_type="individual")
        df_hog = load_eph(year, period, base_type="hogar")

        df = merge_individual_hogar(df_ind, df_hog)
        df["ANIO"] = year
        df["TRIMESTRE"] = period
        df = _fix_mixed_type_columns(df)

        if save:
            os.makedirs(PROCESSED_DIR, exist_ok=True)
            df.to_parquet(os.path.join(PROCESSED_DIR, f"eph_{_period_tag(year, period)}.parquet"))

        frames.append(df)

    panel = pd.concat(frames, ignore_index=True)
    panel = _fix_mixed_type_columns(panel)

    if save:
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        panel.to_parquet(os.path.join(PROCESSED_DIR, "eph_panel.parquet"))

    return panel
