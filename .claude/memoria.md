# Memoria del proyecto: analisis_EPH

> Documento de continuidad entre sesiones de Claude Code (y entre PCs). Leer primero el
> bloque **HANDOFF**. Detalle técnico en [`docs/TECNICO.md`](../docs/TECNICO.md);
> diccionario de variables en [`memoria_EPH.md`](memoria_EPH.md).

## ⭐ HANDOFF (última sesión: 2026-09-29)

**NUEVO (fin de sesión 2026-09-29): `06_termometro.ipynb` creado, FALTA VALIDARLO EN COLAB.**
Índice compuesto de "malestar" 0-100 (0 = mejor trimestre de la serie, 100 = peor), etapa 1
sin variables monetarias. 3 dimensiones con peso 1/3 cada una:
- A. Cantidad de empleo: desocupación, tasa de empleo (invertida), desocupación >1 año
  (`PP10A==5`, % PEA), desalentados (`ESTADO==3 & PP02E==3`, % PEA).
- B. Calidad: subocupación (`INTENSI==1`), ocupados que buscan otro empleo (`PP03J==1`, % PEA),
  asalariados sin descuento jubilatorio (`CAT_OCUP==3 & PP07H==2`).
- C. Estrés de hogares (jefe `CH03==1`, % hogares): `V13` ahorros, `V14` préstamos
  familiares, `V17` vendieron pertenencias, `V6` alimentos gobierno/instituciones, `V7`
  alimentos familiares, `V19_A|V19_B` niños <10 aportan dinero.
- Complementarios fuera del índice: `EMPLEO==2` (solo ≥2023T4), `V15` préstamos bancarios,
  `V16` cuotas/fiado (señal ambigua: crédito ≠ estrés).
- Normalización: percentil histórico orientado de cada indicador, **redondeado a 1 decimal
  antes de rankear** (evita que el ruido en indicadores ~0,1% los lleve a 0/100).
  Franjas: ≤33 Templado, ≤66 Tibio, >66 Fiebre. También media móvil 4T y var. interanual.
- Exporta `carga_EPH/resultados/termometro_EPH.csv` (`;`, decimal `,`, utf-8-sig).
- Códigos verificados contra el PDF oficial `EPH_registro_4T2025.pdf` (copia local en
  `Desktop/INECO/Emancipacion/`). Probado localmente con 8 trimestres sintéticos
  (remuestreo de T4-2025 xlsx): corre de punta a punta. Valores reales T4-2025:
  asalariados sin descuento ≈36%, desocup. >1 año ≈2,2% PEA, gastaron ahorros ≈33%,
  préstamos familiares ≈17%, vendieron pertenencias ≈11%, alimentos gobierno ≈7-9%.
- **Qué validar en Colab:** que 2020T2-T3 aparezca como pico de "fiebre" y 2023T3-T4 como
  zona baja; revisar si algún indicador se comporta raro (quiebre de esquema, `PP07H`).
- **Etapa 2 (pendiente):** ingresos reales (`P21`, `IPCF` deflactados por IPC, ver skill
  `indec-api`) y pobreza/indigencia por canastas CBA/CBT.


**Estado: proyecto completo y al día con T1-2026.** 6 notebooks validados en Colab con
**37 trimestres (T1-2017 → T1-2026)**. Árbol git limpio, todo pusheado a `main`.

Última sesión (2026-09-29):
- El usuario subió `EPH_usu_1_Trim_2026_txt.zip` a Drive `carga_EPH`. Zip con nombres
  internos regulares (`usu_hogar_T126.txt`, `usu_individual_T126.txt`).
- Notebook 00 pasado a `overwrite=False` (antes `True` → recompilaba los 36) y su
  verificación usa `available[-1]` (antes `(2025, 4)` fijo). Compiló solo T126
  (43.739 filas × 331 cols); los 36 previos salteados.
- Títulos "serie 2017-2025" de 02-05 → "serie desde 2017".
- Notebook 01: pirámide usa `plt.FuncFormatter` (eliminado `UserWarning` de `set_ticklabels`).
- Notebooks 01-05 re-corridos en Colab por el usuario con último trimestre = T126. OK.

**Pendientes / ideas (ninguno bloqueante):**
1. **Deciles "escalonados" en 03** (D5 5,5% → D6 8,5% en T126): los cortes por cuantil
   ponderado agrupan empates de IPCF en valores redondos (ej. $500.000). Mejora: asignar
   decil por ranking acumulado de `PONDIH` (orden estable) en `deciles_share` en vez de cortar por cuantiles ponderados.
   El usuario todavía no confirmó si quiere el fix.
2. **T126 individual trae 234 cols** (T4-2023…T4-2025 traían 235). No se identificó qué
   columna falta (no hay copia local de T425). Verificar en Colab comparando
   `pq.read_schema` de `eph_T425.parquet` vs `eph_T126.parquet`. Ninguna variable usada
   por los notebooks falta.
3. Anomalía menor heredada: T3-2021 tiene 266 cols en el merge (vs 264).
4. Contrastar desocupación T1-2026 (7,8%) con el informe oficial INDEC "Mercado de trabajo".
5. Extensiones posibles: notebook de cruces (ingreso × educación, informalidad × región),
   pobreza por canastas CBA/CBT (requiere valores INDEC por región + deflactar), README
   con resumen de hallazgos.
6. **Próximo trimestre: T2-2026** → subir zip a `carga_EPH` y correr el 00 (ver flujo).

## Flujo para agregar un trimestre (no requiere tocar código)

1. Descargar del INDEC `EPH_usu_<Q>_Trim_<YYYY>_txt.zip` (Bases de datos → EPH microdatos).
2. Subirlo **sin descomprimir** a Google Drive → Mi unidad → `carga_EPH`.
3. Correr `00_preparacion_bases.ipynb` en Colab (Runtime → Run all). Debe mostrar el
   trimestre nuevo como "compilado" y los demás "ya existía (salteado)".
4. Re-correr 01-05: toman el último trimestre automáticamente.
5. Si el zip trae nombres internos raros (como T4-2020), ampliar `_parse_period_from_name`
   / `_base_type_from_name` en `src/data_loader.py`.

**Importante:** 01-05 obtienen `ULTIMO` con `list_available_quarters()`, que escanea los
**zips de Drive**, no los parquets. Si se sube un zip y no se corre el 00, el notebook
pedirá un parquet inexistente → siempre correr el 00 primero.

## Valores de referencia (para detectar regresiones)

| Indicador | T4-2025 | T1-2026 |
|---|---|---|
| Actividad / empleo / desocupación (%) | 48,6 / 45,0 / 7,5 | 48,6 / 44,8 / 7,8 |
| Subocupación (% PEA) | 11,3 | 11,1 |
| Informalidad (% ocupados, desde 2023T4) | 43,0 | 44,2 (máx. serie) |
| Gini IPCF / D10/D1 / top10 % | 0,427 / 17,7 / 32,5 | 0,442 / 19,1 / 34,0 |
| Sin cloaca / sin agua cañería / hacinamiento crítico (% hogares) | 27,3 / 1,9 / 1,8 | 27,0 / 1,9 / 1,8 |
| Secundario completo+ (25+) / analfabetismo (%) | 63,7 / 0,86 | 64,3 / 0,71 |
| Edad promedio / índice masculinidad | 35,7 / 95,0 | 35,7 / 95,0 |

Otros hitos de la serie: desocupación pico 2020T2 (13,1%) y mínimo 2023T3-T4 (5,7%);
subocupación pico 2020T4 (15,1%); Gini pico 2024T1 (0,467); edad promedio cae en
2020T2 (efecto pandemia en el operativo). Tamaño medio del hogar T126: 2,95.
Total panel previo a T126: 1.825.881 filas (36 trimestres).

## Qué es / arquitectura (resumen)

- Repo público `santiagoriverti/analisis_EPH`. Notebooks pensados para **Google Colab**.
- Datos: `.zip` de microdatos INDEC en Drive `carga_EPH` → el **00** los compila a un
  parquet por trimestre en `carga_EPH/processed/eph_T<Q><YY>.parquet` (persistente en
  Drive, **no versionado** en GitHub: "Opción A").
- 01-05 copian esos parquets a `/content/processed_local` (evita desconexión FUSE) y leen
  con `load_panel(columns=[...], quarters=[...], out_dir=PROCESSED_DIR)`.
- Sin dependencia de `pyeph`. Toda la lógica de carga en `src/data_loader.py`.
- Detalle de funciones, gotchas y decisiones: [`docs/TECNICO.md`](../docs/TECNICO.md).

## Notebooks (00-05 validados en Colab; 06 pendiente)

| NB | Contenido | Base / ponderador |
|---|---|---|
| 00 | Compila zips → parquets por trimestre; verifica merge/montos y quiebre 4T2023 | — |
| 01 | Pirámide edad×sexo, parentesco y tamaño de hogar, región, edad promedio e índice de masculinidad | Personas / `PONDERA` |
| 02 | Actividad/empleo/desocupación, subocupación (`INTENSI`), `CAT_OCUP`, informalidad (`EMPLEO==2`, solo ≥2023T4) | Personas / `PONDERA` |
| 03 | IPCF: percentiles, participación por decil, D10/D1, Gini (Lorenz), top10/bottom40. Sin línea de pobreza (decisión del usuario) | Personas / `PONDIH` |
| 04 | Tipo de vivienda (`IV1`), tenencia (`II7`), agua (`IV6`), desagüe (`IV11`), hacinamiento (`IX_TOT`/`II1`, crítico >3) | Hogar (jefe `CH03==1`) / `PONDERA` |
| 05 | `NIVEL_ED` 25+, asistencia (`CH10`), público/privado (`CH11`), analfabetismo (`CH09`) | Personas / `PONDERA` |
| 06 | Termómetro 0-100 (ver HANDOFF). **Pendiente de validar en Colab** | Personas + Hogar / `PONDERA` |

Definiciones INDEC usadas en 02: PEA = `ESTADO∈{1,2}`; actividad = PEA/total;
empleo = ocupados/total; desocupación = desocupados/PEA; subocupación = `INTENSI==1`/PEA.

## Reglas del usuario

- Commits **solo** con el usuario Santiago Riverti; **nunca** `Co-Authored-By: Claude` ni
  atribución a Claude en commits/PRs.
- Repos locales en `C:\Users\sriverti\Desktop\INECO\Repositorios\` (en otra PC, clonar
  donde corresponda).
- Idioma de trabajo: español. Actualizar este archivo al cerrar cada sesión.
- Bases pesadas del INDEC no se commitean (`data/raw/*.zip` en `.gitignore`).

## Historial resumido

- **2026-06-12**: creación del repo, `data_loader` sin `pyeph`, notebook 00 (refactor
  memory-safe, fix coma decimal, naming irregular de zips, Opción A en Drive), diccionario
  `memoria_EPH.md`, notebooks 01-05 creados y validados en Colab (36 trimestres).
  Fixes: copia Drive→local (FUSE), `pd.to_numeric` en `IPCF`/`PONDIH` (03).
- **2026-06-16**: `CLAUDE.md` apuntando a la memoria.
- **2026-09-29**: incorporado T1-2026 (ver HANDOFF); documentación reorganizada
  (`docs/TECNICO.md`, README con setup para nueva PC). Creado `06_termometro.ipynb`.
