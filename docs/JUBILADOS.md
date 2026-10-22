# Guía del notebook 08 — adultos mayores y jubilados

Rutina para correr, validar, mantener y leer el notebook `08_jubilados.ipynb`. Cómo funciona por
dentro: [`TECNICO.md`](TECNICO.md) §8. Variables de la EPH que usa:
[`.claude/memoria_EPH.md`](../.claude/memoria_EPH.md) §10. Estado y pendientes del proyecto:
[`.claude/memoria.md`](../.claude/memoria.md) (bloque HANDOFF).

## 1. Qué hace y qué necesita

Describe cómo viven los **adultos mayores (AM): varones de 65 años o más y mujeres de 60 o más** (las
edades jubilatorias), comparados con los **pre-jubilables** (varones de 60 a 64, mujeres de 55 a 59),
los adultos más jóvenes y los menores de 18: cuántos son, con quién viven (si los hijos viven en el
hogar del adulto mayor o el adulto mayor en el de un hijo, y quién sostiene a quién), si cobran
jubilación o pensión, de qué tipo y cuánto, ingresos, pobreza e indigencia, trabajo, vivienda,
estrategias del hogar, salud, educación y estado civil; por región y aglomerado.

- **Foto:** junta los **últimos 4 trimestres** disponibles (hoy T2-2025 a T1-2026; se corre sola cuando
  entra un trimestre). Decisión del usuario: el doble de muestra que un trimestre y sin la
  estacionalidad del aguinaldo.
- **Evolución:** todos los trimestres desde T1-2017, uno por uno.
- **Precisión:** todo con intervalo de confianza del 95% (bootstrap por vivienda, 200 réplicas) y
  marcas `*` (coeficiente de variación 20-33% o menos de 100 casos) y `**` (más de 33% o menos de 50
  casos), con el criterio del INDEC.

**Requisitos:** los parquets del **00** en `carga_EPH/processed/`; internet para el IPC y el haber
mínimo (API de datos.gob.ar), las canastas básicas por región y la pobreza oficial (con respaldos en
`data/`). **No depende del 06 ni del 07.** Tarda ~3 minutos en la PC y algo más en Colab.

## 2. Cómo correrlo

**En Colab** (referencia): abrir `08_jubilados.ipynb` con el badge del README → Runtime → Run all. Las
salidas quedan en Drive, `carga_EPH/resultados/jubilados/`, y al final se descarga
`jubilados_EPH.zip` con todo. Los cambios de código solo llegan a Colab si están pusheados a `main`.

**En la PC** (con los datos reales del INDEC), desde la raíz del repo:

```bash
python tools/probar_06_local.py --descargar
python tools/probar_08_local.py
```

El primero solo hace falta la primera vez o cuando sale un trimestre nuevo (baja los zips del INDEC
a `data/raw/` y compila los parquets a `data/processed/`). El segundo corre el 08 completo y deja las
salidas en `data/processed/resultados_06/jubilados/` (ignorado por git). En Windows usar
`python -X utf8` o `PYTHONUTF8=1`. El Excel necesita `openpyxl` (`pip install -r requirements.txt`).

**Salidas:** `jubilados_EPH.xlsx` (hoja "Índice" con la descripción de cada tabla + 38 tablas; las
estimaciones traen valor, IC, casos, coeficiente de variación y calidad; la composición del ingreso,
el haber mínimo real, la validación de la pobreza, las referencias y los controles son tablas sin
IC), `tablas/*.csv` (`;` y coma decimal), `graficos/` (20 PNG, `01_piramide` a
`20_evolucion_ingresos`), `jubilados_EPH_resumen.md` (la lectura automática) y `jubilados_EPH.zip`.

## 3. Qué revisar en cada corrida

1. **Sección 2:** origen de cada serie ("API datos.gob.ar", "datos.gob.ar (INDEC)" o "respaldo del
   repo") y último mes con dato. Las canastas por región llegan con atraso (al 2026-10-22 había
   hasta jun-2026; la nacional hasta ago-2026).
2. **Sección 15 (controles):** tiene que dar **todo ✓**:

   | Control | Qué significa un ⚠ |
   |---|---|
   | Muestra de AM por trimestre (≥ 5.000) | falta un trimestre o cambió la muestra |
   | No respuesta de ingresos (< 25% individual, < 35% hogar) | subió la no respuesta: mirar con cuidado los ingresos |
   | Pobreza replicada vs. oficial (error medio < 0,5 pp) | se rompió algo en ingresos, adultos equivalentes o canastas |
   | Pobreza replicada por región (< 1,5 pp) | ídem, en alguna región |
   | Cobertura comparable en 2023T4 | el monto de jubilación dejó de ser comparable entre esquemas |
   | Tipos de beneficio vs. cobertura | inconsistencia en `TIPO_JUB` |
   | Canastas regionales publicadas | algún trimestre usa canastas **estimadas** con la nacional (esperable cuando la EPH sale antes que las canastas regionales; no es un error) |
   | Masa de haberes en la mínima (> 25%) | se desalinearon los meses de referencia o cambió el haber mínimo |

3. **Sección 14 (lectura):** el resumen en texto con las cifras principales.
4. **Estimaciones marcadas:** al 2026-10-22, 78 de 1.372 (casi todas por aglomerado o categorías
   chicas). No citar sin aclarar las que tienen `**`.

**Valores de referencia** (foto T2-2025 a T1-2026; si cambian sin que cambien los datos, algo se
rompió; los montos en pesos cambian cuando se actualiza el IPC, porque están en pesos del último mes):

| Indicador | Valor |
|---|---|
| Adultos mayores / % de la población / % mujeres | 4,44 M (4,32-4,57) / 14,8% / 65,8% |
| Hogares con al menos un AM | 33,1% (3,37 M de hogares) |
| Solos / solo con pareja / con hijos sin nietos / con hijos y nietos / en el hogar de un hijo | 22,0 / 29,8 / 22,7 / 10,6 / 6,6% |
| Hijos en el hogar del AM / AM en el hogar de un hijo / no vive con hijos | 33,3 / 6,6 / 60,2% |
| AM aportan más de la mitad del ingreso (hijos en su hogar / en el hogar del hijo) | 55,3% / 28,1% |
| Cobran jubilación o pensión (total / mujeres 60-64 / 75-84) | 88,8% / 69,5% / 96,4% |
| Por aportes / moratoria / otras pensiones / más de uno / no cobra | 56,5 / 24,2 / 3,5 / 4,5 / 11,2% |
| Cobran la mínima (con o sin bono) / menos que la mínima | 38,9% / 17,1% |
| Pobreza: AM / adultos / menores de 18 / total | 11,6 / 28,3 / 43,1 / 29,7% |
| Indigencia AM / pobreza de los AM que no cobran | 1,7% / 21,5% |
| AM que trabajan (`PONDERA`) / informales entre los ocupados | 20,3% / 55,3% |
| Pobreza replicada vs. oficial: error medio / máximo | 0,11 / 0,22 pp (18 semestres) |
| Haber mediano / haber mínimo T1-2026 (+ bono), pesos de ago-2026 | $495.015 / $412.290 ($494.792) |

## 4. Cuando sale una EPH nueva

1. Bajar el zip del INDEC, subirlo sin descomprimir a `carga_EPH` y correr el **00**.
2. Correr el **08** (el orden respecto del 06 y el 07 no importa). La foto pasa sola a los últimos 4
   trimestres y la evolución suma el trimestre nuevo.
3. Si las canastas regionales de los meses del trimestre nuevo todavía no están en datos.gob.ar, el
   control de canastas da ⚠ y esos trimestres usan la canasta nacional × la relación región/nacional
   de los últimos 6 meses (error esperable chico). Volver a correr cuando se publiquen.
4. La validación de la pobreza suma el semestre nuevo cuando están sus dos trimestres.
5. Actualizar los valores de referencia de arriba, los resultados del README y la memoria.

## 5. Mantenimiento

- **Bono previsional (mensual):** el mismo `data/bono_previsional.csv` del 07 (ver
  [`NOWCAST.md`](NOWCAST.md) §6; también en `IPC_jubilados/data/reference/`). Si falta un mes, se
  repite el último valor y la banda "la mínima (con o sin bono)" puede quedar corrida.
- **Respaldos del 08 (de vez en cuando):** canastas por región y pobreza oficial:

  ```bash
  python -X utf8 tools/probar_08_local.py --respaldos
  ```

  Reescribe `data/canastas_regionales.csv` y `data/pobreza_oficial.csv` y después corre el notebook;
  si datos.gob.ar no responde, corta con un error sin tocar los archivos. Commitear los CSV.
- **IPC y haber mínimo:** usan el respaldo del 07 (`data/series_nowcast.csv`; se actualiza con
  `nc.actualizar_respaldo`, ver `NOWCAST.md` §6).

## 6. Validar en Colab

Después de cambiar código: pushear a `main`, correr el 08 en Colab y bajar `jubilados_EPH.zip`.
Correr el 08 en la PC con el mismo commit y comparar:

```bash
python tools/probar_08_local.py
python -X utf8 tools/comparar_zip_08.py "C:/Users/<usuario>/Downloads/jubilados_EPH.zip"
```

Tiene que decir **"✓ Colab idéntico a la corrida local"** (38 tablas, resumen y gráficos). Validado
el 2026-10-22 con el commit e2a23a3: diferencia relativa máxima 5e-16. Si algún día difiere, suele ser
porque una de las dos corridas tomó las series del respaldo y la otra de la API (ver la sección 2 de
las dos corridas) o porque se publicó un dato nuevo entre una corrida y la otra.

## 7. Cómo leer los resultados (cuidados)

1. **La pobreza de los AM sale baja en parte por la metodología.** La escala de adulto equivalente
   del INDEC les asigna menos necesidades (61-75 años: 0,83 varones / 0,67 mujeres; 76 o más: 0,74 /
   0,63; contra 1 de un adulto de 30) y la canasta no distingue quién paga alquiler (el 87% de los AM
   es propietario). Además hay mucha gente apenas arriba de la línea: el **23,1% de los AM** vive en
   hogares con ingresos de 1 a 1,5 líneas de pobreza (resto de la población: 21,9%). "Pocos pobres"
   no es "poco vulnerables".
2. **La cobertura (88,8%) es un piso.** La EPH subdeclara ingresos y ~11% de los AM no informa
   montos (los compensa `PONDII`, que asume que se parecen a los que sí informan). Los registros
   administrativos (ANSES) probablemente den más.
3. **"Menos de la mínima" (17%)** es plausible por descuentos y pensiones no contributivas (le pasa al
   31% de los jubilados por moratoria —descuento de las cuotas— y al 66% de las otras pensiones —la
   PUAM es el 80% de la mínima—), pero la EPH no muestra los descuentos: parte puede ser error de
   declaración.
4. **"Cobran la mínima" en la serie** salta según el mes del trimestre en que cae el aumento (se compara
   con el promedio trimestral del haber mínimo; p. ej. 2019T4 20% y 2020T1 31%): leerlo como tendencia.
5. **El haber real** está deflactado con el IPC general. Para jubilados sería más adecuado el índice de
   precios de jubilados del repo `IPC_jubilados`.
6. **"Quién sostiene a quién"** mide solo el ingreso monetario declarado (`P47T` de los AM sobre el
   `ITF`): no la vivienda propia ni la ayuda en especie. La ayuda en dinero de personas que no viven
   en el hogar (`V12_M`) es rara: la declara el 2,9% de los AM (7,0% de los que viven solos), con un
   monto mediano de 0,6 mínimas.
7. **"Trabaja"** se mide con `PONDERA` (20,3%); la combinación jubilación × trabajo usa `PONDII` (allí
   trabaja el 18,7%, porque los ocupados declaran menos sus ingresos).
8. La pandemia (2020T2-2021T1) tuvo menos muestra y entrevistas telefónicas: en la evolución está
   sombreada.

## 8. Lo que la EPH no puede responder

- **Si tienen hijos:** solo se ven los hijos que viven en el mismo hogar (`CH03 == 3`, incluye
  hijastros si el AM es cónyuge). La EPH no pregunta por hijos que viven en otro lado.
- **Población cubierta:** 31 aglomerados urbanos (~63% del país): sin población rural ni personas en
  geriátricos o residencias, lo que sesga la convivencia de los de 85 y más.
- **Salud y cuidados:** no hay preguntas de autonomía o dependencia; PAMI no se separa de las demás
  obras sociales (`CH08 == 1`).
- **Tipo de beneficio:** solo desde 2023T4; la EPH no separa jubilación propia de pensión por
  fallecimiento.

## 9. Mejoras pendientes (evaluadas el 2026-10-22; el usuario dijo "por ahora no")

En orden de prioridad (las tres primeras usan variables que ya están en la base):

1. **Vulnerabilidad:** distribución de los AM según su ingreso en líneas de pobreza (`ITF_EN_LP`, ya
   calculada en `preparar` y sin usar): 11,6% por debajo, 23,1% entre 1 y 1,5, 18,7% entre 1,5 y 2,
   46,6% por encima de 2.
2. **Ayuda de no convivientes** (`V12_M`, cuotas de alimentos o ayuda en dinero de personas que no
   viven en el hogar) según con quién viven.
3. **Mujeres de 60 a 64 por edad simple:** la moratoria de la Ley 27.705 venció en marzo de 2025
   (verificar normativa vigente). La cobertura de las mujeres de 60-64 todavía no cae (65,4-72,4% entre
   2023T1 y 2026T1; 67,8% en 2026T1); el efecto debería aparecer de a poco, a medida que cumplen 60 las
   cohortes sin moratoria. Seguir las de 60 y 61 años y la parte por moratoria (24,5% en 2026T1, contra
   28-32% en los trimestres de 2025).
4. Deflactar el haber también con el índice de precios de jubilados (`IPC_jubilados`).
5. Tipo de beneficio en la evolución (desde 2023T4).

## 10. Problemas conocidos

| Síntoma | Causa y solución |
|---|---|
| Una serie o las canastas vienen del "respaldo del repo" | datos.gob.ar falla de forma intermitente. El módulo reintenta y baja el CSV de la distribución antes de usar el respaldo. Si pasa seguido, actualizar los respaldos (§5). |
| ⚠ "Canastas regionales publicadas" | La EPH salió antes que las canastas por región de esos meses: se estimaron con la nacional. Volver a correr cuando se publiquen. |
| `ModuleNotFoundError: openpyxl` (en la PC) | `pip install -r requirements.txt`. En Colab viene instalado. |
| No se descarga el ZIP en Colab | El navegador bloqueó la descarga: el ZIP igual queda en `carga_EPH/resultados/jubilados/`. |
| Colab usa una versión vieja del módulo | El setup hace `git pull` y recarga `src.jubilados` (`importlib.reload`); si igual pasa, Runtime → Restart and run all. |
| `KeyError` con una categoría o un trimestre | Cambió algún código de la EPH en un trimestre nuevo: revisar `preparar` en `src/jubilados.py` contra el diccionario (`memoria_EPH.md`). |

## 11. Cambiar o extender el notebook

1. La lógica está en `src/jubilados.py`; el notebook se genera con `tools/gen_08_jubilados.py` (no
   editar el `.ipynb`). Después de editar: `python tools/gen_08_jubilados.py` y
   `python tools/probar_08_local.py` (sección 15 toda ✓).
2. **Indicador nuevo:** crearlo en `preparar` como columna 0/1 con `NaN` fuera de su universo (así
   `estimar` usa solo los casos con dato), estimarlo en el generador con `jb.estimar` o
   `jb.distribucion` y el ponderador que corresponda (`PONDERA`, `PONDII`, `PONDIIO` o `PONDIH`),
   registrar la tabla con `guardar_tabla` (aparece sola en el Excel y en los CSV) y, si va en la
   lectura, sumarlo al `resumen` de la sección 14. Si lo usa la evolución, agregar sus columnas a
   `COLS_SERIE` y el indicador a `indicadores_trimestre`.
3. **Cambiar la foto:** `FOTO = TRIMESTRES[-4:]` en el generador.
4. Gráficos: colores y estilo en `src/jubilados.py` (`COLORES`, `rampa`, `estilo`; la misma paleta del
   06 y el 07, los adultos mayores siempre en azul).
5. Actualizar `TECNICO.md` §8, esta guía, la memoria y el README; pushear, correr en Colab y validar
   con `tools/comparar_zip_08.py`.
