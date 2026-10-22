# Guía operativa del nowcast del termómetro (notebook 07)

Rutina para usar y mantener el notebook `07_nowcast.ipynb`. Qué es y cómo funciona por dentro:
[`TECNICO.md`](TECNICO.md) §7. Estado y pendientes: [`.claude/memoria.md`](../.claude/memoria.md)
(bloque HANDOFF).

## 1. Qué hace y qué necesita

El 07 proyecta el termómetro del 06 para los trimestres que todavía no tienen EPH (la EPH sale
~85 días después de cada trimestre): D (ingresos reales) por microsimulación sobre los microdatos
de la última EPH; A, B y C por ecuaciones puente sobre el EMAE, los asalariados registrados del
SIPA y la confianza del consumidor de la UTDT. Guarda cada corrida en un registro de versiones y,
cuando sale la EPH, completa el valor oficial y el error de cada versión.

**Requisitos:**
- Correr antes el **06**: el 07 lee de `carga_EPH/resultados/termometro_EPH.csv` los indicadores
  de A, B y C (si falta, el 07 corta con un error que lo dice).
- Los parquets compilados por el **00** en `carga_EPH/processed/` (los mismos que usa el 06).
- Internet: las series se bajan de la API de datos.gob.ar (con respaldo en el repo).
- Tiempo: ~5 minutos en la PC, algo más en Colab (los backtests de las secciones 5 y 7).

## 2. Cuándo correrlo

Cada corrida agrega una versión al registro. Conviene correrlo cuando sale alguna de sus series
(fechas aproximadas, en días desde el fin del mes de referencia):

| Serie | Se usa en | Sale |
|---|---|---|
| Confianza del consumidor UTDT (bienes durables) | A, B, C | dentro del mismo mes |
| Haber mínimo, bono previsional, AUH | D | se anuncian antes de pagarse |
| IPC (INDEC) | D | ~14 días |
| Índice de salarios registrado (INDEC) | D | ~45 días |
| EMAE desestacionalizado (INDEC) | A, B, C | ~55 días |
| SIPA asalariados registrados | A, B, C | ~100 días (**la serie clave**: sin ella el error sube ~50%) |
| Índice de salarios no registrado | D | ~7 meses (la API lo fecha en el mes de publicación; el módulo lo corre 6 meses) |
| **EPH (microdatos)** | todo | **~85 días después del trimestre** |

Una corrida del mismo día y la misma versión reemplaza a la anterior en el registro.

## 3. Cómo correrlo

**En Colab** (referencia): abrir `07_nowcast.ipynb` con el badge del README → Runtime → Run all
(después del 06). Los cambios de código solo llegan a Colab si están pusheados a `main`.

**En la PC** (con los datos reales del INDEC):

```bash
python tools/probar_06_local.py --descargar
python tools/probar_07_local.py
```

`--descargar` solo hace falta la primera vez o cuando sale un trimestre nuevo. Las salidas locales
van a `data/processed/resultados_06/nowcast/` (ignorado por git). En Windows usar `PYTHONUTF8=1` o
`python -X utf8` (la salida usa ✓/⚠/→); con `python -I` la variable `PYTHONUTF8` se ignora.

## 4. Qué revisar en cada corrida

1. **Sección 2:** origen de cada serie ("API datos.gob.ar" o "respaldo del repo") y último mes con
   dato. Si una serie viene del respaldo, está tan actualizada como el CSV del repo.
2. **Sección 3:** tiene que decir **"✓ Indicadores de D, dimensiones y termómetro idénticos a los
   del 06"**. Si aparece "⚠ Hay microdatos de … que el CSV del 06 no tiene", correr el 06 y
   después el 07.
3. **Sección 4:** cuánto se movió cada serie desde la última EPH y cuántos meses son estimados.
4. **Sección 6:** la proyección de cada trimestre con su intervalo, la comparación **contra el
   mismo trimestre del año anterior** (A, B y C tienen estacionalidad: comparar contra el trimestre
   anterior engaña) y los gráficos `nowcast_05_evolucion` (serie + proyección) y `nowcast_03_hoy`
   (por dimensión).
5. **Sección 7:** la lectura ✓/⚠ de robustez (también en `nowcast/robustez_termometro.md`). Al
   2026-10-21 los ⚠ esperables son dos: intervalos algo angostos con la EPH demorada dos trimestres
   (k=3) y la dependencia del SIPA. Un ⚠ nuevo (sesgo significativo, que no le gane a repetir el
   último en algún subperíodo, versiones que no convergen) indica que algo cambió.

## 5. Cuando sale una EPH nueva

1. Bajar el zip del INDEC, subirlo sin descomprimir a `carga_EPH`, correr el **00**, después el
   **06** (revisar su sección 13) y después el **07**.
2. En la sección 8 del 07, la tabla **"Proyecciones que ya tienen su EPH"** muestra el error
   (proyectado − oficial) de cada versión de ese trimestre. El oficial de las dimensiones y del
   termómetro es el que muestra el 06 cuando ese trimestre es el último.
3. Comparar el error con el del backtest para ese horizonte (al 2026-10-21, con la EPH del
   trimestre anterior: RMSE 4,1 pts; con la EPH demorada uno o dos trimestres: 7,0 y 8,8). Un error
   de más de 2 veces el RMSE merece mirar qué dimensión falló (la tabla del registro tiene las
   dimensiones y los 15 indicadores).
4. La proyección siguiente ya parte de la base nueva y los coeficientes se reestiman solos.

Primera prueba real: **2026T2** (versiones del 21/10/2026: termómetro 62,8, IC 54,5-71,1).

## 6. Mantenimiento

- **Bono previsional (mensual):** no hay serie pública. Agregar una fila por mes en
  `data/bono_previsional.csv` (`periodo,bono`; última fila cargada: 2026-10) y lo mismo en
  `IPC_jubilados/data/reference/bono_previsional.csv`. Si falta un mes, el módulo repite el último
  valor. El notebook 08 usa el mismo archivo (banda "la mínima con o sin bono"; ver
  [`JUBILADOS.md`](JUBILADOS.md) §5).
- **Respaldo de las series (de vez en cuando):** desde la raíz del repo,

  ```bash
  python -X utf8 -c "import src.nowcast as nc; nc.actualizar_respaldo('data/series_nowcast.csv')"
  ```

  Solo reescribe el archivo si la API devolvió todas las series. Commitear el CSV. El 08 toma de
  este respaldo el IPC y el haber mínimo cuando falla la API.
- **Respaldo del IPC del 06:** ver `TECNICO.md` §6 (comando `curl`).
- **Registro de versiones:** vive en Drive (`carga_EPH/resultados/nowcast/registro_versiones.csv`)
  y es el único estado del 07 que no se puede regenerar: no borrarlo. El registro local
  (`data/processed/resultados_06/nowcast/`) es aparte y solo sirve para pruebas.
- **Archivos viejos en Drive:** `nowcast_D.csv`, `backtest_D.csv` y `backtest_D_resumen.csv`
  quedaron de las corridas del prototipo de D (oct-2026); el 07 ya no los genera y se pueden borrar.

## 7. Problemas conocidos

| Síntoma | Causa y solución |
|---|---|
| Una serie viene del "respaldo del repo" | La API de datos.gob.ar falla de forma intermitente (a veces todo un día para una serie). El módulo reintenta, baja el CSV de la distribución y recién después usa el respaldo. Si pasa seguido, actualizar el respaldo cuando la API ande. |
| `FileNotFoundError: Falta …/termometro_EPH.csv` | No se corrió el 06 (o no guardó en Drive). Correr el 06. |
| ⚠ de la sección 3 por trimestres de más | Hay un parquet nuevo que el 06 todavía no procesó: correr el 06 y después el 07. |
| El zip de un trimestre "no existe" | El INDEC responde con una página HTML (200) cuando el archivo no está: o no se publicó todavía o cambió el nombre (T1-2017 se llama `EPH_usu_1er_Trim_2017_txt.zip`). Al 2026-10-21 el T2-2026 seguía sin aparecer. |
| Colab toma una versión vieja del módulo | El setup hace `git pull` y el notebook recarga `src.nowcast` (`importlib.reload`); si igual pasa, Runtime → Restart and run all. |
| Un trimestre proyectado da distinto al comparar dos tablas | Cada trimestre se proyecta por separado: si a la historia se le agregan también los trimestres siguientes proyectados, su percentil cambia ~1 punto. |

## 8. Cambiar o extender el modelo

1. La lógica está en `src/nowcast.py`; el notebook se genera con `tools/gen_07_nowcast.py` (no editar
   el `.ipynb`). Después de editar: `python tools/gen_07_nowcast.py` y probar con
   `python tools/probar_06_local.py` + `python tools/probar_07_local.py`.
2. Comparar `backtest_termometro_resumen.csv` y la sección 7 contra la versión anterior antes de
   adoptar un cambio: con 25 trimestres, diferencias de menos de ~0,5 pts son ruido.
3. Si cambia el método, cambiar `VERSION` en el generador (hoy `"termómetro v1"`), así el registro
   distingue las versiones.
4. **Predictor nuevo:** agregarlo a `SERIES` (id de datos.gob.ar, desfase en meses, rezago de
   publicación en días), a `NOMBRE_PREDICTOR` y a `PREDICTORES_ABC` (o a `PREDICTORES` para algunos
   indicadores); regenerar el respaldo de series.
5. **Si cambia el 06** (indicadores, dimensiones, normalización): el 07 tiene copias de
   `DIMENSIONES`, `desestacionalizar`, `percentil_orientado` y las fórmulas de D. Cambiarlas en
   `src/nowcast.py` y verificar el control de la sección 3 (tiene que dar idéntico).
6. Actualizar `TECNICO.md` §7, esta guía y la memoria; pushear y correr en Colab.
