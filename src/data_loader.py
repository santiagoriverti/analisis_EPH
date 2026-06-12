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
