"""
Carga de bases EPH descargadas manualmente del INDEC (formato .zip o .txt) desde
una carpeta de Google Drive ("carga_EPH") y/o desde data/raw/ del repo.

El INDEC publica los microdatos de cada trimestre como un .zip (ej.
"EPH_usu_4_Trim_2025_txt.zip") que contiene dos archivos .txt separados por ";":
  - usu_individual_T<Q><YY>.txt
  - usu_hogar_T<Q><YY>.txt

Uso típico en un notebook:

    from src.data_loader import load_eph, build_panel

    df = load_eph(year=2025, period=4, base_type="individual")
    panel = build_panel(save=True)
"""

import glob
import os
import re
import zipfile

import pandas as pd

# Carpeta de Google Drive donde se suben los .zip descargados del INDEC
# (Drive > "carga_EPH"). En Colab, montar Drive primero con
# `from google.colab import drive; drive.mount('/content/drive')`.
DRIVE_DIR = "/content/drive/MyDrive/carga_EPH"

# Carpeta del repo para bases sueltas (.txt) que no vinieron en un .zip.
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# Claves de vínculo entre la base de hogares y la de individuos.
HOGAR_KEYS = ["CODUSU", "NRO_HOGAR"]

_TAG_RE = re.compile(r"T(\d)(\d{2})", re.IGNORECASE)

# Algunos zips (ej. T4-2020) no siguen el patrón usu_<base>_T<Q><YY>.txt y usan
# nombres como "EPH_usu_personas_4to.trim_2020.txt" / "EPH_usu_hogar_4to_trim2020_txt.txt".
_ORDINAL_TRIM_RE = re.compile(r"(\d)(?:ro|do|er|to|°)?[._]?trim[e]?[._]?(\d{4})", re.IGNORECASE)


def _period_tag(year: int, period: int) -> str:
    """Convierte (2025, 4) -> 'T425' (formato usado en nombres de archivo del INDEC)."""
    return f"T{period}{str(year)[-2:]}"


def _parse_period_from_name(name: str) -> tuple[int, int] | None:
    """Extrae (year, period) de un nombre de archivo.

    Soporta el patrón habitual `T<Q><YY>` (ej. 'usu_individual_T425.txt' -> (2025, 4))
    y el patrón alternativo `<Q>to_trim<YYYY>` usado en algunos zips (ej.
    'EPH_usu_personas_4to.trim_2020.txt' -> (2020, 4)).
    """
    m = _TAG_RE.search(name)
    if m:
        period = int(m.group(1))
        year = 2000 + int(m.group(2))
        return year, period

    m = _ORDINAL_TRIM_RE.search(name)
    if m:
        period = int(m.group(1))
        year = int(m.group(2))
        return year, period

    return None


def _base_type_from_name(name: str) -> str | None:
    lname = name.lower()
    if "hogar" in lname:
        return "hogar"
    if "individual" in lname or "personas" in lname:
        return "individual"
    return None


def _read_csv(fileobj) -> pd.DataFrame:
    return pd.read_csv(fileobj, sep=";", encoding="latin1", low_memory=False)


def _find_sources(search_dirs: list[str] | None = None) -> dict[tuple[int, int], dict[str, object]]:
    """Indexa los archivos disponibles (zips o sueltos) por (year, period) y base_type.

    Devuelve algo como:
        {(2025, 4): {"individual": <ref>, "hogar": <ref>}, ...}

    donde <ref> es una ruta a un .txt suelto, o una tupla (ruta_zip, nombre_interno)
    si el archivo está dentro de un .zip.
    """
    if search_dirs is None:
        search_dirs = [DRIVE_DIR, RAW_DIR]

    sources: dict[tuple[int, int], dict[str, object]] = {}

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue

        for path in glob.glob(os.path.join(directory, "*")):
            name = os.path.basename(path)

            if name.lower().endswith(".zip"):
                with zipfile.ZipFile(path) as zf:
                    for inner_name in zf.namelist():
                        _register(sources, inner_name, (path, inner_name))
            elif name.lower().endswith(".txt"):
                _register(sources, name, path)

    return sources


def _register(sources: dict, name: str, ref: object) -> None:
    tag = _parse_period_from_name(name)
    base_type = _base_type_from_name(name)
    if tag is None or base_type is None:
        return
    sources.setdefault(tag, {})[base_type] = ref


def _load_ref(ref: object) -> pd.DataFrame:
    if isinstance(ref, tuple):
        zip_path, inner_name = ref
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(inner_name) as f:
                return _read_csv(f)
    return _read_csv(ref)


def list_available_quarters(search_dirs: list[str] | None = None) -> list[tuple[int, int]]:
    """Lista los (year, period) disponibles en DRIVE_DIR / data/raw/, con ambas bases."""
    sources = _find_sources(search_dirs)
    return sorted(tag for tag, entry in sources.items() if "individual" in entry and "hogar" in entry)


def load_eph(year: int, period: int, base_type: str = "individual", search_dirs: list[str] | None = None) -> pd.DataFrame:
    """Carga la base EPH de un trimestre desde DRIVE_DIR (o RAW_DIR / search_dirs).

    Parameters
    ----------
    year : int
        Año de la encuesta (ej. 2025).
    period : int
        Trimestre (1 a 4).
    base_type : str
        "individual" o "hogar".
    search_dirs : list[str], opcional
        Carpetas donde buscar (por defecto [DRIVE_DIR, RAW_DIR]).
    """
    sources = _find_sources(search_dirs)
    entry = sources.get((year, period))
    if entry is None or base_type not in entry:
        raise FileNotFoundError(
            f"No se encontró la base EPH {base_type} {year}T{period} en "
            f"{search_dirs or [DRIVE_DIR, RAW_DIR]} "
            f"(se esperaba un .zip del INDEC con usu_{base_type}_{_period_tag(year, period)}.txt, "
            f"o ese .txt suelto)"
        )
    return _load_ref(entry[base_type])


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


def build_panel(
    quarters: list[tuple[int, int]] | None = None,
    search_dirs: list[str] | None = None,
    save: bool = True,
) -> pd.DataFrame:
    """Construye un panel combinando individuo+hogar para una lista de trimestres.

    Si `quarters` es None, usa todos los trimestres disponibles en
    DRIVE_DIR / RAW_DIR (`list_available_quarters`).

    Para cada (year, period):
      - carga la base individual y la de hogares,
      - las une por CODUSU + NRO_HOGAR,
      - agrega columnas ANIO y TRIMESTRE.

    Si `save=True`, además de devolver el panel combinado, guarda en
    `data/processed/` un parquet por trimestre (`eph_<TyyTQQ>.parquet`) y el
    panel completo (`eph_panel.parquet`).
    """
    if quarters is None:
        quarters = list_available_quarters(search_dirs)

    frames = []
    for year, period in quarters:
        df_ind = load_eph(year, period, base_type="individual", search_dirs=search_dirs)
        df_hog = load_eph(year, period, base_type="hogar", search_dirs=search_dirs)

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
