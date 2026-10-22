"""Corre el notebook 08 (adultos mayores) en la PC con los datos reales del INDEC (sin Colab).

Uso (desde la raíz del repo):
    python tools/probar_08_local.py --descargar   # baja del INDEC los zips que falten y compila
    python tools/probar_08_local.py --respaldos   # además regenera los respaldos de canastas y pobreza
    python tools/probar_08_local.py               # usa los parquets ya compilados

Igual que probar_06_local.py, pero ejecuta notebooks/08_jubilados.ipynb. Las salidas (Excel, CSV,
gráficos, resumen y ZIP) van a data/processed/resultados_06/jubilados/, el equivalente local de
carga_EPH/resultados/jubilados/ en Drive. Regenerar el notebook antes de probar un cambio:
python tools/gen_08_jubilados.py

--respaldos reescribe data/canastas_regionales.csv (CBA y CBT por región) y data/pobreza_oficial.csv
(pobreza publicada por el INDEC), que el notebook usa si datos.gob.ar no responde.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import probar_06_local as p06  # noqa: E402  (deja el directorio de trabajo en la raíz del repo)
import src.jubilados as jb  # noqa: E402

if __name__ == "__main__":
    if "--descargar" in sys.argv:
        p06.descargar()
    if "--respaldos" in sys.argv:
        t = jb.actualizar_respaldo_canastas(os.path.join("data", "canastas_regionales.csv"))
        print(f"  canastas: {t.index[0]} a {t.index[-1]}")
        t = jb.actualizar_respaldo_pobreza(os.path.join("data", "pobreza_oficial.csv"))
        print(f"  pobreza oficial: {t.index[0]} a {t.index[-1]}")
    p06.dl.build_panel(search_dirs=[p06.dl.RAW_DIR], out_dir=p06.dl.PROCESSED_DIR)
    p06.correr_notebook("08_jubilados")
