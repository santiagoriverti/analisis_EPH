"""Compara el ZIP que descarga el notebook 08 en Colab con la corrida local (validación en Colab).

Uso (desde la raíz del repo, después de python tools/probar_08_local.py):
    python -X utf8 tools/comparar_zip_08.py "C:/Users/<usuario>/Downloads/jubilados_EPH.zip"
    python -X utf8 tools/comparar_zip_08.py <zip> <carpeta local>   # por defecto data/processed/resultados_06/jubilados

Lee los CSV de tablas/ y el resumen directo del ZIP (sin descomprimirlo) y los compara con los de la
corrida local: textos iguales y números con diferencia relativa menor a 1e-9. También chequea que
estén los mismos gráficos. Sale con código 1 si algo no coincide. Con los mismos datos y el mismo
commit, Colab y la PC dan lo mismo salvo redondeo (validado el 2026-10-22: dif. máx. 5e-16).
"""
import glob
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

TOLERANCIA = 1e-9
LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed", "resultados_06", "jubilados")


def leer(fuente) -> pd.DataFrame:
    return pd.read_csv(fuente, sep=";", encoding="utf-8-sig", header=None, dtype=str, keep_default_na=False)


def numeros(t: pd.DataFrame) -> pd.DataFrame:
    return t.apply(lambda c: pd.to_numeric(c.str.replace(",", ".", regex=False), errors="coerce"))


def comparar(zip_path: str, local: str) -> bool:
    z = zipfile.ZipFile(zip_path)
    en_zip = set(z.namelist())
    filas, ok_total = [], True
    for f in sorted(glob.glob(os.path.join(local, "tablas", "*.csv"))):
        nombre = f"tablas/{os.path.basename(f)}"
        if nombre not in en_zip:
            filas.append((nombre, "falta en el ZIP", np.nan))
            ok_total = False
            continue
        a, b = leer(f), leer(io.BytesIO(z.read(nombre)))
        if a.shape != b.shape:
            filas.append((nombre, f"forma distinta {a.shape} / {b.shape}", np.nan))
            ok_total = False
            continue
        na, nb = numeros(a), numeros(b)
        es_num = na.notna() & nb.notna()
        textos_ok = bool(((a == b) | es_num).all().all())
        rel = ((na - nb).abs() / na.abs().clip(lower=1e-12)).where(es_num)
        dif = float(np.nanmax(rel.to_numpy())) if es_num.any().any() else 0.0
        ok = textos_ok and dif < TOLERANCIA
        ok_total &= ok
        filas.append((nombre, "✓" if ok else ("⚠ textos distintos" if not textos_ok else "⚠ números distintos"), dif))
    extra = sorted(n for n in en_zip if n.startswith("tablas/") and not os.path.exists(os.path.join(local, n)))
    for n in extra:
        filas.append((n, "solo en el ZIP", np.nan))
        ok_total = False

    t = pd.DataFrame(filas, columns=["archivo", "resultado", "dif_relativa_max"])
    pd.set_option("display.width", 200)
    print(t.to_string(index=False))

    resumen = "jubilados_EPH_resumen.md"
    if resumen in en_zip and os.path.exists(os.path.join(local, resumen)):
        igual = z.read(resumen).decode("utf-8") == open(os.path.join(local, resumen), encoding="utf-8").read()
        print(f"\nResumen: {'✓ idéntico' if igual else '⚠ distinto'}")
        ok_total &= igual
    png_zip = sorted(os.path.basename(n) for n in en_zip if n.startswith("graficos/") and n.endswith(".png"))
    png_loc = sorted(os.path.basename(p) for p in glob.glob(os.path.join(local, "graficos", "*.png")))
    print(f"Gráficos: {'✓ los mismos' if png_zip == png_loc else '⚠ distintos'} ({len(png_zip)} en el ZIP, {len(png_loc)} locales)")
    ok_total &= png_zip == png_loc
    print(f"\n{'✓ Colab idéntico a la corrida local' if ok_total else '⚠ Hay diferencias: revisar arriba'} "
          f"({len(t)} tablas, dif. relativa máx. {np.nanmax(t['dif_relativa_max'].to_numpy()):.1e})")
    return ok_total


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(0 if comparar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else LOCAL) else 1)
