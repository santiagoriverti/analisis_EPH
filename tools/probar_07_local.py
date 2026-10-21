"""Corre el notebook 07 (nowcast) en la PC con los datos reales del INDEC (sin Colab).

Uso (desde la raíz del repo):
    python tools/probar_07_local.py --descargar   # baja del INDEC los zips que falten y compila
    python tools/probar_07_local.py               # usa los parquets ya compilados

Igual que probar_06_local.py, pero ejecuta notebooks/07_nowcast.ipynb. Las salidas van a
data/processed/resultados_06/nowcast/ (equivalente local de carga_EPH/resultados/nowcast/), y el
control contra el 06 lee data/processed/resultados_06/termometro_EPH.csv: correr antes el 06 si
cambió algo. Regenerar el notebook antes de probar un cambio: python tools/gen_07_nowcast.py

Ojo: cada corrida agrega una versión al registro local (registro_versiones.csv), con la fecha de
hoy; las corridas del mismo día se reemplazan.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import probar_06_local as p06  # noqa: E402

if __name__ == "__main__":
    if "--descargar" in sys.argv:
        p06.descargar()
    p06.dl.build_panel(search_dirs=[p06.dl.RAW_DIR], out_dir=p06.dl.PROCESSED_DIR)
    p06.correr_notebook("07_nowcast")
