# Memoria del proyecto: analisis_EPH

> Documento de continuidad entre sesiones de Claude Code (y entre PCs). Leer primero el
> bloque **HANDOFF**. Detalle técnico en [`docs/TECNICO.md`](../docs/TECNICO.md);
> diccionario de variables en [`memoria_EPH.md`](memoria_EPH.md).

## ⭐ HANDOFF (última sesión: 2026-09-29)

**Estado: proyecto al día con T1-2026. 7 notebooks (00-06) validados en Colab con 37
trimestres (T1-2017 → T1-2026).** Árbol git limpio, todo pusheado a `main`.

El 06 reorganizado (punto 4) está **validado en Colab** (2026-09-29): números idénticos a
la v3, sección 12 con los 5 chequeos ✓ (hogares T126 15.447 vs mediana 16.815; pandemia
73,8; valle 23,4), 3 archivos exportados.

Qué se hizo en la sesión 2026-09-29:
1. **T1-2026 incorporado.** Zip con nombres internos regulares; el 00 (ahora
   `overwrite=False`, verificación con `available[-1]`) compiló solo T126 (43.739 × 331).
   01-05 re-corridos OK. Fix cosmético en 01 (`FuncFormatter` en la pirámide).
2. **Documentación reorganizada** para continuar en otra PC: `docs/TECNICO.md`, README con
   sección "Continuar en otra PC", `CLAUDE.md` con orden de lectura.
3. **Nuevo `06_termometro.ipynb`** (índice de malestar económico de los hogares), iterado
   v1 → v2 → v3 y validado. Ver sección "Termómetro" abajo. El notebook se **genera** con
   `tools/gen_06_termometro.py` (no editar el .ipynb a mano).
4. **06 reorganizado (índice sin cambios, sigue v3):** 13 secciones + 2 anexos. Nuevas:
   6 lectura automática del último trimestre (`resumen_trimestre(q)`: ranking y "desde
   cuándo", aporte de cada dimensión a la variación i.a., récords, percentil ≥ 80, mayores
   movimientos, complementarios ≥ 1 pp); 11 promedios anuales; 12 controles de calidad
   (cobertura, muestra, chequeo de sentido ✓/⚠, códigos `PP11O`); 13 exporta además
   `termometro_EPH_anual.csv` y `termometro_EPH_resumen.md`. El diagnóstico de candidatas
   pasó al Anexo A con `CANDIDATAS = {}` por defecto (ya no corre pluriempleo); Anexo B =
   historial de versiones. README y TECNICO §6 actualizados.

**Pendientes / ideas (ninguno bloqueante):**
1. **Próximo trimestre T2-2026**: subir zip a `carga_EPH`, correr 00 y luego 01-06. Revisar
   que el termómetro no cambie de forma (los percentiles se recalculan con la historia).
2. Extensiones propuestas al usuario (eligió NO sumar ingresos reales ni pobreza):
   - **Transiciones con el panel rotativo** (`CODUSU`+`NRO_HOGAR`+`COMPONENTE` entre
     trimestres): flujos empleo→desempleo, registrado→no registrado. Recomendada.
   - Termómetro **por región** (`REGION`) y **por grupos** (jóvenes, sexo, educación del jefe).
   - Calidad del empleo por **rama** (`PP04B_COD`) y tamaño (`PP04C99`).
   - Página/artifact con resultados (el resumen automático en texto ya está: sección 6 del 06).
3. Termómetro, ajustes posibles: sumar ex-cuentapropistas que cerraron por falta de
   clientes (`PP11L==1`) al indicador de despidos. Candidatas no evaluadas: jóvenes 18-24
   que no estudian ni trabajan (~19,8%), temporarios `PP07C==1` (~8,5%, sesgo composición),
   desocupación de jefes (redundante con desocupación).
4. **Deciles "escalonados" en 03** (D5 5,5% → D6 8,5% en T126) por empates de IPCF en
   valores redondos. Fix: decil por ranking acumulado de `PONDIH` en `deciles_share`. Sin
   confirmar por el usuario.
5. T126 individual trae 234 cols (vs 235 en T4-2023…T4-2025): columna faltante sin
   identificar (comparar `pq.read_schema` de `eph_T425` vs `eph_T126` en Colab). No afecta.
6. Menores: T3-2021 con 266 cols (vs 264); contrastar desocupación T1-2026 (7,8%) con el
   informe oficial INDEC.

## Termómetro de la economía de los hogares (notebook 06) — v3 vigente

**Qué es:** índice de malestar 0-100 (0 = mejor trimestre de la serie, 100 = peor), sin
variables monetarias. Franjas: ≤33 Templado, ≤66 Tibio, >66 Fiebre. Tres dimensiones con
peso 1/3; cada indicador se normaliza como **percentil histórico orientado**, redondeando a
1 decimal antes de rankear (evita que el ruido en indicadores chicos los lleve a 0/100).

| Dimensión | Indicadores (en el índice) |
|---|---|
| A. Cantidad de empleo | desocupación; tasa de empleo (invertida); desocupación >1 año (`PP10A==5`, % PEA); desocupados por despido o renuncia forzada (`PP11O∈{1,7}`, % PEA) |
| B. Calidad del empleo | subocupación (`INTENSI==1`); ocupados que buscan otro empleo (`PP03J==1`, % PEA); asalariados sin descuento jubilatorio (`CAT_OCUP==3 & PP07H==2`); tasa de empleo asalariado registrado (`CAT_OCUP==3 & PP07H==1`, % población, invertida) |
| C. Estrés de los hogares (jefe `CH03==1`, % hogares) | `V13` gastaron ahorros; `V14` préstamos familiares; `V17` vendieron pertenencias; `V6` alimentos de gobierno/instituciones; `V7` alimentos de familiares |

Complementarios (se muestran, fuera del índice): informalidad `EMPLEO==2` (solo ≥2023T4),
`V15` préstamos bancarios y `V16` cuotas/fiado (señal ambigua), desalentados
(`ESTADO==3 & PP02E==3`) y niños <10 que aportan (`V19_A|V19_B`) (niveles ~0,1% = ruido),
pluriempleo `PP03C==2` (descartado: procíclico).

**Resultados v3 (validados en Colab):** máx 2020T4 82,1; mín 2017T4 20,4; valle 2023T3
22,4; 2020T2 65,7 (Tibio, a 0,3 del umbral, aceptado); 2024T1 44,2.
**2026T1 = 60,0 (Tibio), +11,0 i.a.; media móvil 4T 57,0** (la más alta desde 2022).
Dimensiones 2026T1: A 34,7 · B 66,3 · C 78,9. Lectura: hay empleo pero más precario
(asalariados sin descuento 37,9% = máximo de la serie; asalariados registrados 20,0% de la
población, percentil 86) y los hogares usan reservas (préstamos familiares p90, gastaron
ahorros p89, vendieron pertenencias p81): estrés en el nivel más alto fuera de la pandemia.
Promedio anual (v3; sección 11 del 06): 2017 29,9 · 2018 43,8 · 2019 65,9 · 2020 72,3 · 2021 64,4 · 2022 41,6
· 2023 26,2 · 2024 49,0 · 2025 54,3 · 2026 (solo T1) 60,0. 2026T1 es el 10.º trimestre más
alto de 37 (todos los superiores son 2019T2-2021T2). Estados: 21 Tibio, 8 Templado, 8 Fiebre.
Re-corrida del 06 el 2026-09-29 (CSV 37 × 40 con `trimestre`) idéntica a la validación.
Exporta `carga_EPH/resultados/termometro_EPH.csv` (37 × 39; `;`, decimal `,`, utf-8-sig).

**Historia de versiones (por qué está armado así):**
- **v1**: falló el chequeo de sentido (2020T2 = 48). Causa: **efecto composición**: en la
  cuarentena se perdieron sobre todo empleos informales y de pocas horas, entonces los
  indicadores calculados sobre ocupados "mejoraron" (dimensión B = 0,9 en 2020T2).
  Además desalentados y niños <10 (≈0,1%) metían ruido.
- **v2**: desalentados y niños pasan a complementarios; B suma la tasa de asalariados
  registrados sobre población. 2020T2 → 64,7; máx 2020T4 83,1.
- **v3**: sección 10 (hoy Anexo A) "Diagnóstico de candidatas" (6 criterios: cobertura desde 2017,
  códigos estables entre esquemas, pandemia > valle 2023, autocorrelación ≥0,3, Spearman
  con termómetro ≥0,3, |corr| <0,85 con indicadores del índice). `PP11O==1` pasó (autocorr
  0,76, Spearman 0,60, corr máx 0,83 con desocupación) → entra a A; luego ampliado al
  código 7 "renuncia obligada/pactada" (despido encubierto) a pedido del usuario (con 1+7:
  pandemia 1,62% vs valle 0,65%, autocorr 0,74, corr 0,82). `PP03C==2` (pluriempleo) no
  pasó: procíclico (pandemia 7,8% vs valle 11,2%) y estacional (T1 8,4% vs 10,1%).
- Notas `PP11O`: solo se pregunta a ex-asalariados; código 4 (fin de temporario) excluido
  por estacional.

**Cómo testear cambios sin Colab:** no hay datos locales salvo el xlsx de T4-2025
(`Desktop/INECO/Emancipacion/EPH_usu_4_Trim_2025_xls.zip`, junto al PDF oficial
`EPH_registro_4T2025.pdf`). Se arma un parquet con `merge_individual_hogar` y trimestres
sintéticos por remuestreo de hogares para correr el código de punta a punta (ver
`docs/TECNICO.md` §6). Los números reales solo salen en Colab.

## Flujo para agregar un trimestre (no requiere tocar código)

1. Descargar del INDEC `EPH_usu_<Q>_Trim_<YYYY>_txt.zip` (Bases de datos → EPH microdatos).
2. Subirlo **sin descomprimir** a Google Drive → Mi unidad → `carga_EPH`.
3. Correr `00_preparacion_bases.ipynb` en Colab (Runtime → Run all). Debe mostrar el
   trimestre nuevo como "compilado" y los demás "ya existía (salteado)".
4. Re-correr 01-06: toman el último trimestre automáticamente.
5. Si el zip trae nombres internos raros (como T4-2020), ampliar `_parse_period_from_name`
   / `_base_type_from_name` en `src/data_loader.py`.

**Importante:** 01-06 obtienen `ULTIMO` con `list_available_quarters()`, que escanea los
**zips de Drive**, no los parquets. Si se sube un zip y no se corre el 00, el notebook
pedirá un parquet inexistente → siempre correr el 00 primero.

## Valores de referencia (para detectar regresiones)

| Indicador | T4-2025 | T1-2026 |
|---|---|---|
| Actividad / empleo / desocupación (%) | 48,6 / 45,0 / 7,5 | 48,6 / 44,8 / 7,8 |
| Subocupación (% PEA) | 11,3 | 11,1 |
| Informalidad (% ocupados, desde 2023T4) | 43,0 | 44,2 (máx. serie) |
| Termómetro v3 (0-100) / media móvil 4T | 57,1 / 54,3 | 60,0 / 57,0 |
| Desocupados por despido o renuncia forzada (% PEA) | 1,1 | 1,1 |
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
- 01-06 copian esos parquets a `/content/processed_local` (evita desconexión FUSE) y leen
  con `load_panel(columns=[...], quarters=[...], out_dir=PROCESSED_DIR)`.
- Sin dependencia de `pyeph`. Toda la lógica de carga en `src/data_loader.py`.
- Detalle de funciones, gotchas y decisiones: [`docs/TECNICO.md`](../docs/TECNICO.md).

## Notebooks (todos validados en Colab)

| NB | Contenido | Base / ponderador |
|---|---|---|
| 00 | Compila zips → parquets por trimestre; verifica merge/montos y quiebre 4T2023 | — |
| 01 | Pirámide edad×sexo, parentesco y tamaño de hogar, región, edad promedio e índice de masculinidad | Personas / `PONDERA` |
| 02 | Actividad/empleo/desocupación, subocupación (`INTENSI`), `CAT_OCUP`, informalidad (`EMPLEO==2`, solo ≥2023T4) | Personas / `PONDERA` |
| 03 | IPCF: percentiles, participación por decil, D10/D1, Gini (Lorenz), top10/bottom40. Sin línea de pobreza (decisión del usuario) | Personas / `PONDIH` |
| 04 | Tipo de vivienda (`IV1`), tenencia (`II7`), agua (`IV6`), desagüe (`IV11`), hacinamiento (`IX_TOT`/`II1`, crítico >3) | Hogar (jefe `CH03==1`) / `PONDERA` |
| 05 | `NIVEL_ED` 25+, asistencia (`CH10`), público/privado (`CH11`), analfabetismo (`CH09`) | Personas / `PONDERA` |
| 06 | Termómetro de la economía de los hogares 0-100, v3 (ver sección Termómetro). Generado por `tools/gen_06_termometro.py` | Personas + Hogar / `PONDERA` |

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
  (`docs/TECNICO.md`, README con setup para nueva PC). Creado `06_termometro.ipynb`;
  v1 falló chequeo 2020 (efecto composición) → v2 corregida → v3 suma despidos
  (`PP11O∈{1,7}`), pluriempleo descartado; v3 validada. Generador versionado en `tools/`.
  Re-corrida verificada (idéntica). 06 reorganizado: lectura automática, promedios
  anuales, controles de calidad, exportación anual/resumen, candidatas a Anexo A; validado en Colab.
