"""Corre el notebook 06 en la PC con los datos reales del INDEC (sin Colab).

Uso (desde la raíz del repo):
    python tools/probar_06_local.py --descargar   # baja del INDEC los zips que falten y compila
    python tools/probar_06_local.py               # usa los parquets ya compilados

1. (--descargar) Baja los microdatos trimestrales del sitio del INDEC a data/raw/ (~3 MB por
   trimestre) hasta el último publicado.
2. Compila a data/processed/ los parquets que falten (build_panel, overwrite=False).
3. Ejecuta todas las celdas de notebooks/06_termometro.ipynb salvo el setup de Colab. Las
   salidas (CSV, resumen y graficos/*.png) van a data/processed/resultados_06/, el equivalente
   local de carga_EPH/resultados/ en Drive.

data/raw/*.zip y data/processed/* están ignorados por git. Regenerar el notebook antes de
probar un cambio: python tools/gen_06_termometro.py
"""
import glob
import json
import os
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)
os.chdir(REPO)

import src.data_loader as dl  # noqa: E402

URL = "https://www.indec.gob.ar/ftp/cuadros/menusuperior/eph/"


def descargar():
    """Baja los zips que falten en data/raw/, desde T1-2017 hasta el último publicado."""
    import requests
    os.makedirs(dl.RAW_DIR, exist_ok=True)
    anio, faltantes_seguidos = 2017, 0
    while faltantes_seguidos < 4:  # 4 trimestres seguidos sin publicar = fin de la serie
        for t in range(1, 5):
            destino = os.path.join(dl.RAW_DIR, f"EPH_usu_{t}_Trim_{anio}_txt.zip")
            if os.path.exists(destino):
                faltantes_seguidos = 0
                continue
            # el INDEC publicó T1-2017 con otro nombre
            nombre = "EPH_usu_1er_Trim_2017_txt.zip" if (anio, t) == (2017, 1) else os.path.basename(destino)
            r = requests.get(URL + nombre, timeout=120)
            if r.ok and "zip" in r.headers.get("Content-Type", ""):
                open(destino, "wb").write(r.content)
                print(f"  bajado {os.path.basename(destino)} ({len(r.content) / 1e6:.1f} MB)")
                faltantes_seguidos = 0
            else:  # el sitio responde una página HTML cuando el trimestre no existe
                faltantes_seguidos += 1
        anio += 1


def correr_notebook():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    processed = dl.PROCESSED_DIR
    resultados = os.path.join(processed, "resultados_06")

    def disponibles(search_dirs=None):  # trimestres = parquets compilados
        fs = glob.glob(os.path.join(processed, "eph_T*.parquet"))
        return sorted((2000 + int(os.path.basename(f)[6:8]), int(os.path.basename(f)[5])) for f in fs)
    dl.list_available_quarters = disponibles
    plt.show = lambda *a, **k: plt.close("all")  # el notebook ya guarda cada gráfico (guardar_figura)

    nb = json.load(open(os.path.join(REPO, "notebooks", "06_termometro.ipynb"), encoding="utf-8"))
    celdas = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    ns = {"REPO_DIR": REPO, "PROCESSED_DIR": processed, "RESULTADOS_DIR": resultados,
          "display": print, "__name__": "__main__"}
    exec("import sys, os, shutil, glob", ns)  # lo que importa la celda de setup de Colab
    t0 = time.time()
    for i, src in enumerate(celdas[1:], start=1):  # la celda 0 es el setup de Colab
        exec(src.replace("display(Markdown(resumen))", "print(resumen)"), ns)
        print(f"[celda {i} ok]", flush=True)
    print(f"\nNotebook 06 completo en {time.time() - t0:.0f} s; salidas y gráficos en {resultados}")


if __name__ == "__main__":
    if "--descargar" in sys.argv:
        descargar()
    dl.build_panel(search_dirs=[dl.RAW_DIR], out_dir=dl.PROCESSED_DIR)
    correr_notebook()
