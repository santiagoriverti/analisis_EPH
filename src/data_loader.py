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
import pyarrow.parquet as pq

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
    # decimal="," porque el INDEC usa coma decimal en los montos (ej. IPCF "2933333,33").
    # Sin esto, esas columnas se leen como texto y rompen cualquier cálculo numérico.
    return pd.read_csv(fileobj, sep=";", encoding="latin1", low_memory=False, decimal=",")


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
    out_dir: str | None = None,
    overwrite: bool = False,
) -> list[dict]:
    """Compila las bases EPH a un parquet por trimestre, de forma memory-safe.

    Procesa **un trimestre por vez** (carga individual + hogar, los une por
    CODUSU + NRO_HOGAR, agrega ANIO/TRIMESTRE, guarda el parquet y libera memoria).
    NO concatena todo en RAM: con 36 trimestres × ~235 columnas eso desborda la
    memoria de Colab. Además, un único panel combinado superaría el límite de 100 MB
    de GitHub. Por eso se guarda un archivo por trimestre (`eph_<TyyTQQ>.parquet`) y
    los notebooks lo leen con `load_panel()` eligiendo solo las columnas/trimestres
    que necesiten.

    Parameters
    ----------
    quarters : list[tuple[int, int]], opcional
        Trimestres a compilar. Si None, usa todos los disponibles.
    search_dirs : list[str], opcional
        Dónde buscar los .zip/.txt (por defecto [DRIVE_DIR, RAW_DIR]).
    out_dir : str, opcional
        Carpeta donde guardar los parquets. Por defecto `data/processed/` del repo
        (efímero en Colab). Para persistir, pasar una carpeta de Drive, ej.
        `/content/drive/MyDrive/carga_EPH/processed`.
    overwrite : bool
        Si False (default), saltea los trimestres cuyo parquet ya existe en `out_dir`
        (útil para agregar solo trimestres nuevos sin recompilar todo).

    Devuelve un resumen (lista de dicts con year, period, filas, columnas, path).
    """
    if quarters is None:
        quarters = list_available_quarters(search_dirs)

    out_dir = out_dir or PROCESSED_DIR
    os.makedirs(out_dir, exist_ok=True)
    resumen = []
    for year, period in quarters:
        path = os.path.join(out_dir, f"eph_{_period_tag(year, period)}.parquet")

        if not overwrite and os.path.exists(path):
            resumen.append(
                {"year": year, "period": period, "filas": None, "columnas": None,
                 "path": path, "estado": "ya existía (salteado)"}
            )
            continue

        df_ind = load_eph(year, period, base_type="individual", search_dirs=search_dirs)
        df_hog = load_eph(year, period, base_type="hogar", search_dirs=search_dirs)

        df = merge_individual_hogar(df_ind, df_hog)
        del df_ind, df_hog

        df["ANIO"] = year
        df["TRIMESTRE"] = period
        df = _fix_mixed_type_columns(df)

        df.to_parquet(path)
        print(f"  [{_period_tag(year, period)}] {len(df)} filas x {df.shape[1]} cols -> {path}")
        resumen.append(
            {"year": year, "period": period, "filas": len(df), "columnas": df.shape[1],
             "path": path, "estado": "compilado"}
        )
        del df

    print(f"\nListo. Parquets en: {out_dir}")
    return resumen


def load_panel(
    columns: list[str] | None = None,
    quarters: list[tuple[int, int]] | None = None,
    out_dir: str | None = None,
) -> pd.DataFrame:
    """Lee los parquets por trimestre y los concatena.

    Pensada para usarse en los notebooks 01-05. Para no desbordar la memoria de
    Colab, conviene pasar `columns` con solo las variables necesarias (y opcionalmente
    `quarters` con un subconjunto de trimestres).

    Parameters
    ----------
    columns : list[str], opcional
        Subconjunto de columnas a leer. Si None, lee todas (puede ser pesado).
        ANIO y TRIMESTRE se incluyen siempre.
    quarters : list[tuple[int, int]], opcional
        Trimestres a incluir. Si None, usa todos los parquets presentes.
    out_dir : str, opcional
        Carpeta de donde leer los parquets. Por defecto `data/processed/`. Debe
        coincidir con el `out_dir` usado en `build_panel` (ej. la carpeta de Drive).
    """
    out_dir = out_dir or PROCESSED_DIR
    if quarters is None:
        files = sorted(glob.glob(os.path.join(out_dir, "eph_T*.parquet")))
    else:
        files = [os.path.join(out_dir, f"eph_{_period_tag(y, p)}.parquet") for y, p in quarters]

    cols = None
    if columns is not None:
        cols = list(dict.fromkeys([*columns, "ANIO", "TRIMESTRE"]))

    frames = []
    for f in files:
        if not os.path.exists(f):
            continue
        if cols is not None:
            # Leer solo las columnas pedidas que existan en ese trimestre (esquema 4T2023)
            disponibles = pq.read_schema(f).names
            usar = [c for c in cols if c in disponibles]
            frames.append(pd.read_parquet(f, columns=usar))
        else:
            frames.append(pd.read_parquet(f))

    if not frames:
        existentes = sorted(os.path.basename(p) for p in glob.glob(os.path.join(out_dir, "eph_T*.parquet")))
        raise FileNotFoundError(
            f"No se encontraron parquets para leer en {out_dir}. "
            f"¿Corriste primero la celda de compilación (build_panel)? "
            f"Parquets actualmente presentes en esa carpeta: {existentes or 'ninguno'}"
        )

    return pd.concat(frames, ignore_index=True)
