# memoria_EPH.md — Diccionario y estructura de las bases EPH

Documento de referencia para **procesar y entender** las bases de microdatos de la
Encuesta Permanente de Hogares (EPH, INDEC). Combina:
- El **diseño de registros oficial** (PDF `EPH_registro_4T2025.pdf`, INDEC, abril 2026).
- La **verificación de los headers reales** de los 36 `.txt` dentro de los `.zip` de
  `carga_EPH` (T1-2017 a T4-2025).

---

## 1. Estructura general y vínculo entre bases

Cada `.zip` del INDEC contiene dos archivos `.txt` (separador `;`, encoding `latin1`):

| Archivo | Base | Unidad de análisis |
|---|---|---|
| `usu_hogar_*.txt` | **Hogar** | Hogares (vivienda + condiciones + ingresos familiares) |
| `usu_individual_*.txt` | **Personas** | Personas (demografía, educación, empleo, ingresos individuales) |

**Claves de identificación / vínculo:**
- `CODUSU` — identificador de **vivienda** (C, 29). Permite seguir la vivienda a través
  de los trimestres (panel rotativo).
- `NRO_HOGAR` — identificador de **hogar** dentro de la vivienda.
- `COMPONENTE` — identificador de **persona** dentro del hogar (solo base Personas).

**Reglas de merge:**
- Hogar ↔ Personas: se unen por `CODUSU` + `NRO_HOGAR` (relación 1 hogar : N personas).
- En la base Personas, `NRO_HOGAR` y `COMPONENTE` tienen códigos especiales:
  `51 = Servicio doméstico en hogares`, `71 = Pensionistas en hogares`.
- En `merge_individual_hogar` (src/data_loader.py) la unión es `m:1` (muchas personas
  a un hogar), con sufijo `_hogar` para columnas duplicadas.

**Ponderadores (factores de expansión) — OBLIGATORIO usarlos para estimaciones:**
- `PONDERA` — ponderador general (todas las variables salvo ingresos/pobreza).
- `PONDII` — ingreso total individual (P47T y sus deciles).
- `PONDIIO` — ingreso de la ocupación principal (P21 y sus deciles).
- `PONDIH` — ingreso total familiar e ingreso per cápita familiar (ITF, IPCF, deciles).

---

## 2. ⚠️ Quiebre de esquema en 4T2023 (CRÍTICO para el panel)

Verificado en los headers reales. Hay **dos esquemas distintos** según el trimestre:

| Período | Cols. Individual | Cols. Hogar | Esquema |
|---|---|---|---|
| **T1-2017 → T3-2023** | **177** | **88** | "viejo" (agregado) |
| **T4-2023 → T4-2025** | **235** | **98** | "nuevo" (desagregado) |

El INDEC, a partir del **4° trimestre de 2023**, incorporó nuevas variables:
informalidad laboral (`EMPLEO`, `SECTOR`), estrategias del hogar e ingresos no laborales
**desagregados**, y nuevas escalas decílicas.

**Diferencias concretas (qué columnas cambian):**

- **Base Hogar — esquema viejo** usa variables agregadas: `V2`, `V21`, `V22`, `V5`, `V11`.
  **Esquema nuevo** las desagrega: `V2_01`, `V2_02`, `V2_03`, `V21_01`, `V21_02`,
  `V21_03`, `V22_01`, `V22_02`, `V22_03`, `V5_01`, `V5_02`, `V5_03`, `V11_01`, `V11_02`.

- **Base Personas — esquema viejo** usa montos de ingreso agregados: `V2_M`, `V5_M`,
  `V11_M`, `V21_M`. **Esquema nuevo** los desagrega (`V2_01_M`, `V2_02_M`, `V2_03_M`,
  `V5_01_M`, `V5_02_M`, `V5_03_M`, `V11_01_M`, `V11_02_M`, `V21_01_M`...`V22_03_M`) y
  **agrega** variables nuevas: `EMPLEO`, `SECTOR`, `PP07B1_01`, `PP02A`, `PP02B`,
  `PP02D`, `PP02F`, `PP02G`, `PP03K`, `PP04A1`, `PP05B3`, `PP05I/J/K`, `PP06E1`,
  `PP06K(_SEM/_MES)`, `PP06L`, `PP07F1_1/2/3`, `PP07I2/I3/I4`, `PP07L`, `PP07M`,
  `PP08G(_DSEM/_DMES)`, `PP08H`, `PP10B1..PP10B10`, `PP11L2`, y los deciles de IPCF
  **de las personas** `P_DECCF`, `P_RDECCF`, `P_GDECCF`, `P_PDECCF`, `P_IDECCF`,
  `P_ADECCF`.

**Implicancia para los notebooks:** al concatenar trimestres de ambos esquemas, las
columnas no comunes quedarán con `NaN` en los trimestres que no las tienen. Para análisis
de informalidad (`EMPLEO`/`SECTOR`) o ingresos desagregados, **filtrar a T4-2023 en
adelante**. Para series largas usar solo variables comunes a ambos esquemas (demografía,
educación, ESTADO/CAT_OCUP, ITF/IPCF, deciles agregados).

**Otras irregularidades de formato detectadas:**
- Algunos trimestres (ej. 2023) traen los valores **entre comillas dobles** (`"CODUSU";"ANO4"`);
  pandas las maneja automáticamente con el `quotechar` por defecto.
- Variabilidad en mayúsculas/minúsculas y doble extensión en nombres de archivo dentro
  del zip (ver `memoria.md` → naming irregular; ya resuelto en `data_loader.py`).
- `CH05` (fecha de nacimiento) viene con tipos mezclados entre trimestres → se castea a
  string antes de exportar a parquet (`_fix_mixed_type_columns`).

---

## 3. BASE HOGAR — diccionario de variables

### Identificación
| Campo | Tipo | Descripción / valores |
|---|---|---|
| CODUSU | C(29) | Identificador de vivienda |
| NRO_HOGAR | N(1) | Identificador de hogar |
| REALIZADA | N(1) | Entrevista realizada (1=Sí, 2=No/no respuesta) |
| ANO4 | N(4) | Año de relevamiento |
| TRIMESTRE | N(1) | 1/2/3/4 = trimestre |
| REGION | N(2) | 01=GBA, 40=Noroeste, 41=Noreste, 42=Cuyo, 43=Pampeana, 44=Patagonia |
| MAS_500 | C(1) | N=<500.000 hab, S=500.000+ hab |
| AGLOMERADO | N(2) | Código de aglomerado (ver §5) |
| PONDERA | N(6) | Ponderación general |

### Características de la vivienda
| Campo | Tipo | Descripción / valores |
|---|---|---|
| IV1 | N(1) | Tipo vivienda: 1=Casa, 2=Depto, 3=Pieza inquilinato, 4=Pieza hotel/pensión, 5=Local no constr., 6=Otros |
| IV1_ESP | C(45) | Especifica IV1=6 |
| IV2 | N(2) | Cantidad de ambientes/habitaciones (sin baño/cocina/pasillo/lavadero/garage) |
| IV3 | N(1) | Pisos: 1=mosaico/baldosa/madera/cerámica, 2=cemento/ladrillo fijo, 3=ladrillo suelto/tierra, 4=otros |
| IV3_ESP | C(45) | Especifica IV3=4 |
| IV4 | N(2) | Cubierta techo: 1=membrana/asfáltica, 2=baldosa/losa, 3=pizarra/teja, 4=chapa metal, 5=chapa fibrocemento/plástico, 6=chapa cartón, 7=caña/tabla/paja, 9=N/S (PH) |
| IV5 | N(1) | Techo con cielorraso: 1=Sí, 2=No |
| IV6 | N(1) | Agua: 1=cañería dentro vivienda, 2=fuera vivienda dentro terreno, 3=fuera terreno |
| IV7 | N(1) | Origen agua: 1=red pública, 2=perforación bomba motor, 3=perforación bomba manual, 4=otra |
| IV7_ESP | C(45) | Especifica IV7=4 |
| IV8 | N(1) | Tiene baño/letrina: 1=Sí, 2=No |
| IV9 | N(1) | Ubicación baño: 1=dentro vivienda, 2=fuera vivienda dentro terreno, 3=fuera terreno |
| IV10 | N(1) | Baño: 1=inodoro con arrastre agua (botón/mochila/cadena), 2=inodoro arrastre a balde, 3=letrina sin arrastre |
| IV11 | N(1) | Desagüe: 1=red pública (cloaca), 2=cámara séptica y pozo ciego, 3=solo pozo ciego, 4=hoyo/excavación |
| IV12_1 | N(1) | Cerca de basural (≤3 cuadras): 1=Sí, 2=No |
| IV12_2 | N(1) | Zona inundable (últimos 12m): 1=Sí, 2=No |
| IV12_3 | N(1) | En villa de emergencia: 1=Sí, 2=No |

### Características habitacionales del hogar
| Campo | Tipo | Descripción / valores |
|---|---|---|
| II1 | N(2) | Ambientes de uso exclusivo del hogar |
| II2 | N(2) | De esos, cuántos usan para dormir |
| II3 | N(1) | Usa alguno exclusivo como lugar de trabajo: 1=Sí, 2=No |
| II3_1 | N(1) | Cuántos (si II3=1) |
| II4_1 | N(1) | Tiene cuarto de cocina: 1=Sí, 2=No |
| II4_2 | N(1) | Tiene lavadero: 1=Sí, 2=No |
| II4_3 | N(1) | Tiene garage: 1=Sí, 2=No |
| II5 | N(1) | Usa alguno (de II4) para dormir: 1=Sí, 2=No |
| II5_1 | N(2) | Cuántos (si II5=1) |
| II6 | N(1) | Usa alguno (de II4) exclusivo como trabajo: 1=Sí, 2=No |
| II6_1 | N(1) | Cuántos (si II6=1) |
| II7 | N(2) | Tenencia: 1=propietario viv+terreno, 2=propietario solo viv, 3=inquilino, 4=ocupante pago impuestos/expensas, 5=ocupante relación dependencia, 6=ocupante gratuito c/permiso, 7=ocupante de hecho s/permiso, 8=sucesión, 9=otra |
| II7_ESP | C(45) | Especifica II7=9 |
| II8 | N(1) | Combustible cocina: 1=gas de red, 2=gas tubo/garrafa, 3=kerosene/leña/carbón, 4=otro |
| II8_ESP | C(45) | Especifica II8=4 |
| II9 | N(1) | Baño: 1=uso exclusivo del hogar, 2=compartido c/hogares misma viv, 3=compartido c/otras viv, 4=no tiene |

### Estrategias del hogar (V1–V19)
Todas son 1=Sí / 2=No salvo aclaración. **Esquema viejo** (hasta 3T2023) usa códigos
agregados (V2, V21, V22, V5, V11); **esquema nuevo** (desde 4T2023) los desagrega.

| Campo | Descripción |
|---|---|
| V1 | Vivieron de lo que ganan en el trabajo |
| V2 | Vivieron de jubilación/pensión (agregado, esquema viejo) |
| V2_01 | Jubilación/pensión por aportes del trabajo (nuevo) |
| V2_02 | Jubilación/pensión "ama de casa"/moratoria (nuevo) |
| V2_03 | Otras pensiones (discapacidad, Madre de 7 hijos, PUAM, vejez) (nuevo) |
| V21 / V21_01/02/03 | Aguinaldo de jubilación/pensión (agregado / desagregado) |
| V22 / V22_01/02/03 | Retroactivo de jubilación/pensión (agregado / desagregado) |
| V3 | Indemnización por despido |
| V4 | Seguro de desempleo |
| V5 / V5_01 | AUH y/o Asignación por Embarazo (incluye Tarjeta Alimentar) |
| V5_02 | Otro plan social/subsidio del gobierno |
| V5_03 | Ayuda en dinero de iglesias/ONG |
| V6 | Mercaderías/ropa/alimentos del gobierno/iglesias/escuelas |
| V7 | Mercaderías/ropa/alimentos de familiares/vecinos externos |
| V8 | Cobraron alquiler de propiedad |
| V9 | Ganancias de negocio en que no trabajan |
| V10 | Intereses/rentas por plazos fijos/inversiones |
| V11 / V11_01 | Beca (en dinero) del gobierno (ej. Progresar) |
| V11_02 | Otra beca de instituciones no gubernamentales |
| V12 | Cuotas de alimentos/ayuda en dinero de externos |
| V13 | Gastaron ahorros |
| V14 | Préstamos a familiares/amigos |
| V15 | Préstamos a bancos/financieras |
| V16 | Compran en cuotas/al fiado con tarjeta/libreta |
| V17 | Vendieron pertenencias |
| V18 | Otros ingresos en efectivo (limosnas, juegos de azar) |
| V19_A | Niños <10 años ayudan con dinero trabajando |
| V19_B | Niños <10 años ayudan con dinero pidiendo |

### Resumen del hogar e ingresos familiares
| Campo | Tipo | Descripción |
|---|---|---|
| IX_TOT | N(2) | Cantidad de miembros del hogar |
| IX_MEN10 | N(2) | Miembros menores de 10 años |
| IX_MAYEQ10 | N(2) | Miembros de 10 y más años |
| ITF | N(12) | Ingreso total familiar (monto) |
| DECIFR / IDECIFR / RDECIFR / GDECIFR / PDECIFR / ADECIFR | C(2) | Decil del ITF (total EPH / interior / región / aglom. 500k+ / aglom. <500k / aglomerado) |
| IPCF | N(12,2) | Ingreso per cápita familiar (= ITF / IX_TOT) |
| DECCFR / IDECCFR / RDECCFR / GDECCFR / PDECCFR / ADECCFR | C(2) | Decil del IPCF (mismas variantes) |
| PONDIH | C/N(6) | Ponderador de ITF/IPCF |

### Organización del hogar
| Campo | Tipo | Descripción |
|---|---|---|
| VII1_1, VII1_2 | N(2) | Realización de tareas de la casa — nº componente (96=servicio doméstico, 97=externo) |
| VII2_1..VII2_4 | N(2) | Otras personas que ayudan — nº componente (96=serv.dom., 97=externo, 98=ninguna) |

---

## 4. BASE PERSONAS — diccionario de variables

### Identificación
| Campo | Tipo | Descripción / valores |
|---|---|---|
| CODUSU | C(29) | Identificador de vivienda |
| NRO_HOGAR | N(2) | Identificador de hogar (51=serv.doméstico, 71=pensionistas) |
| COMPONENTE | N(2) | Nº de orden de la persona (51=serv.doméstico, 71=pensionistas) |
| H15 | N(1) | Entrevista individual realizada: 1=Sí, 2=No |
| ANO4, TRIMESTRE, REGION, MAS_500, AGLOMERADO, PONDERA | | Igual que base Hogar |

### Características de los miembros (Cuestionario Hogar: CH03–CH16, NIVEL_ED)
| Campo | Tipo | Descripción / valores |
|---|---|---|
| CH03 | N(2) | Parentesco: 1=Jefe/a, 2=Cónyuge/pareja, 3=Hijo/a/hijastro/a, 4=Yerno/nuera, 5=Nieto/a, 6=Madre/padre, 7=Suegro/a, 8=Hermano/a, 9=Otros familiares, 10=No familiares |
| CH04 | N(1) | Sexo: 1=Varón, 2=Mujer |
| CH05 | date | Fecha de nacimiento (día/mes/año) — ⚠️ tipos mezclados entre trimestres |
| CH06 | N(2) | Años cumplidos (edad) |
| CH07 | N(1) | Estado civil: 1=unido, 2=casado, 3=separado/divorciado, 4=viudo, 5=soltero |
| CH08 | N(3) | Cobertura médica: 1=obra social (incl. PAMI), 2=mutual/prepaga/emergencia, 3=planes/seguros públicos, 4=no paga ni descuentan, 9=Ns/Nr, 12/13/23/123=combinaciones |
| CH09 | N(1) | Sabe leer y escribir: 1=Sí, 2=No, 3=Menor de 2 años |
| CH10 | N(1) | Asiste/asistió a establecimiento educativo: 1=asiste, 2=asistió, 3=nunca asistió |
| CH11 | N(1) | Tipo establecimiento: 1=público, 2=privado, 9=Ns/Nr |
| CH12 | N(2) | Nivel más alto cursado: 1=jardín/preescolar, 2=primario, 3=EGB, 4=secundario, 5=polimodal, 6=terciario, 7=universitario, 8=posgrado, 9=educación especial |
| CH13 | N(1) | Finalizó ese nivel: 1=Sí, 2=No, 9=Ns/Nr |
| CH14 | N(2) | Último año aprobado: 00=ninguno...09=noveno, 98=educación especial, 99=Ns/Nr |
| CH15 | N(1) | Dónde nació: 1=esta localidad, 2=otra localidad provincia, 3=otra provincia, 4=país limítrofe, 5=otro país, 9=Ns/Nr |
| CH15_COD | C(3) | Código de provincia/país (si CH15=3/4/5) |
| CH16 | N(1) | Dónde vivía hace 5 años: 1=esta localidad, 2=otra localidad prov., 3=otra provincia, 4=país limítrofe, 5=otro país, 6=no había nacido, 9=Ns/Nr |
| CH16_COD | C(3) | Código de provincia/país (si CH16=3/4/5) |
| NIVEL_ED | N(1) | **Nivel educativo (construida):** 1=Primario incompleto, 2=Primario completo, 3=Secundario incompleto, 4=Secundario completo, 5=Superior/univ. incompleto, 6=Superior/univ. completo, 7=Sin instrucción, 9=Ns/Nr |

### Condición de actividad (Cuestionario Individual)
| Campo | Tipo | Descripción / valores |
|---|---|---|
| ESTADO | N(1) | **Condición de actividad:** 0=entrevista no realizada, 1=Ocupado, 2=Desocupado, 3=Inactivo, 4=Menor de 10 años |
| CAT_OCUP | N(1) | **Categoría ocupacional** (ocupados y desocup. c/ocup. anterior): 1=Patrón, 2=Cuenta propia, 3=Obrero/empleado, 4=Trabajador familiar sin remuneración, 9=Ns/Nr |
| CAT_INAC | N(1) | **Categoría de inactividad:** 1=Jubilado/pensionado, 2=Rentista, 3=Estudiante, 4=Ama de casa, 5=Menor de 6 años, 6=Discapacitado, 7=Otros |
| IMPUTA | N(1) | Indica casos imputados |
| EMPLEO | N(1) | **(desde 4T2023)** Formalidad del empleo: 1=Formal, 2=Informal, 9=Ns/Nr |
| SECTOR | N(1) | **(desde 4T2023)** Sector: 1=Formal, 2=Informal, 3=Hogares, 9=Ns/Nr |

### Búsqueda de empleo / desocupados (PP02*, PP10*, PP11*)
Principales (todas 1=Sí/2=No salvo aclaración):
- `PP02A` puede empezar a trabajar (1=sí, 2=sí c/condiciones, 3=no por razones personales, 4=no desea).
- `PP02B/PP02C1..C8/PP02D` modalidades de búsqueda de trabajo (últimos 30 días).
- `PP02E` por qué no buscó: 1=suspendido, 2=trabajo asegurado, 3=se cansó, 4=poco trabajo época, 5=otras.
- `PP02H` buscó trabajo últimos 12 meses; `PP02I` trabajó últimos 12 meses.
- `PP10A` cuánto hace que busca; `PP10B1..PP10B10` razones por las que no encuentra;
  `PP10C` hizo changa; `PP10D` trabajó alguna vez; `PP10E` cuánto hace que terminó último trabajo.
- `PP11*` desocupados con empleo anterior (rama, ocupación, tiempo, razón de cese,
  indemnización, telegrama, seguro de desempleo, etc.).

### Ocupación principal (PP03*, PP04*, INTENSI)
- `PP03C` uno/más empleos; `PP03D` cantidad ocupaciones.
- `PP3E_TOT` horas semanales en ocupación principal; `PP3F_TOT` horas en otras ocupaciones.
- `PP03G/H/I/J/K` quería/buscó más horas, buscó otro empleo.
- `INTENSI` **(construida):** 1=Subocupado por insuficiencia horaria, 2=Ocupado pleno,
  3=Sobreocupado, 4=Ocupado que no trabajó en la semana, 9=Ns/Nr.
- `PP04A` tipo de empleador (1=estatal, 2=privado, 3=otro); `PP04A1` nivel estatal
  (nacional/provincial/municipal).
- `PP04B_COD` rama de actividad (CAES-Mercosur); `PP04D_COD` ocupación (CNO-2001).
- `PP04C` tamaño del establecimiento (escala 1..12); `PP04C99` tamaño agrupado (1=hasta 5, 2=6-40, 3=>40).
- `PP04G` dónde realiza las tareas (local, vivienda, vehículo, calle, etc.).

### Independientes (PP05*, PP06*) y asalariados (PP07*, PP08*)
- Independientes: antigüedad, facturación (`PP05B3`, `PP05K`), tenencia de
  maquinaria/local/vehículo (`PP05C_*`), aportes monotributo/autónomo (`PP05I/J`),
  ingresos `PP06C` (sin socios) / `PP06D` (con socios).
- Asalariados: antigüedad (`PP07A`), tiempo de finalización (`PP07C/D`), beneficios
  (`PP07G1..G4` vacaciones/aguinaldo/días enfermedad/obra social), descuento jubilatorio
  (`PP07H/I`), recibo (`PP07K/L/M`), ingresos (`PP08D1` sueldo total, `PP08J1` aguinaldo, etc.).
- `PP09*` movimientos interurbanos (CABA/GBA y otros aglomerados).

### Ingresos individuales y deciles
| Campo | Tipo | Descripción |
|---|---|---|
| P21 | N(12) | **Ingreso de la ocupación principal** (monto) |
| DECOCUR / IDECOCUR / RDECOCUR / GDECOCUR / PDECOCUR / ADECOCUR | C(2) | Deciles de P21 (total/interior/región/500k+/<500k/aglomerado) |
| PONDIIO | | Ponderador de P21 |
| TOT_P12 | N(12) | Ingreso de **otras** ocupaciones |
| P47T | N(12) | **Ingreso total individual** (laborales + no laborales) |
| DECINDR / IDECINDR / RDECINDR / GDECINDR / PDECINDR / ADECINDR | C(2) | Deciles de P47T |
| PONDII | N(6) | Ponderador de P47T |
| T_VI | N(12) | Total de ingresos **no laborales** |
| V*_M | N(8) | Montos de cada ingreso no laboral (jubilaciones, pensiones, AUH, planes, becas, alquileres, intereses, cuotas alimentarias, etc.). Esquema viejo agregado (`V2_M`,`V5_M`,`V11_M`,`V21_M`); nuevo desagregado (`V2_01_M`...`V22_03_M`, `V5_01_M`...`V5_03_M`, `V11_01_M/02_M`) |
| ITF, IPCF + deciles | | Replicados desde la base Hogar (mismo significado) |
| P_DECCF / P_IDECCF / P_RDECCF / P_GDECCF / P_PDECCF / P_ADECCF | C(2) | **(desde 4T2023)** Decil de IPCF **de las personas** |

---

## 5. Códigos de AGLOMERADO (común a ambas bases)

02=Gran La Plata · 03=Bahía Blanca-Cerri · 04=Gran Rosario · 05=Gran Santa Fe ·
06=Gran Paraná · 07=Posadas · 08=Gran Resistencia · 09=Comodoro Rivadavia-Rada Tilly ·
10=Gran Mendoza · 12=Corrientes · 13=Gran Córdoba · 14=Concordia · 15=Formosa ·
17=Neuquén-Plottier · 18=Santiago del Estero-La Banda · 19=Jujuy-Palpalá ·
20=Río Gallegos · 22=Gran Catamarca · 23=Gran Salta · 25=La Rioja · 26=Gran San Luis ·
27=Gran San Juan · 29=Gran Tucumán-Tafí Viejo · 30=Santa Rosa-Toay ·
31=Ushuaia-Río Grande · 32=CABA · 33=Partidos del Gran Buenos Aires · 34=Mar del Plata ·
36=Río Cuarto · 38=San Nicolás-Villa Constitución · 91=Rawson-Trelew ·
93=Viedma-Carmen de Patagones.

---

## 6. Convenciones de códigos especiales (Anexo I del registro)

- **Deciles de ingreso:** 00=sin ingresos, 1..10=decil, 12=no respuesta de ingresos,
  13=entrevista individual no realizada.
- **No sabe/No responde:** códigos 9, 99, 999, 9999 (salvo indicación contraria).
- **Montos de ingreso:** la no respuesta se identifica con **-9** (no con 9).
  En `PP06C`/`PP06D` además: -7 = "no tenía esa ocupación en el mes de referencia",
  -8 = "no tuvo ingresos en el mes de referencia".
- **Código 0:** el caso no corresponde a la secuencia analizada (salteo).
- Para análisis de ingresos/pobreza usar los deciles ya provistos (calculados con
  ponderadores corregidos por no respuesta) o recalcular con `PONDERA` + montos.

---

## 7. Clasificadores externos referenciados

- **PP04B_COD / PP11B_COD:** rama de actividad → CAES-Mercosur (Clasificador de
  Actividades Económicas para Encuestas Sociodemográficas del Mercosur).
- **PP04D_COD / PP11D_COD:** ocupación → CNO-2001 (Clasificador Nacional de Ocupaciones).

---

## 8. Notas operativas para los notebooks

0. Los notebooks 01-05 NO leen los `.txt`/`.zip` directo: usan
   `from src.data_loader import load_panel` y piden columnas/trimestres acotados
   (`load_panel(columns=[...], quarters=[...])`). El notebook 00 ya compiló todo a
   `data/processed/eph_T<Q><YY>.parquet` (un archivo por trimestre).
1. Leer siempre con `sep=";"`, `encoding="latin1"` (ya implementado en `data_loader._read_csv`).
2. Para estimaciones poblacionales, **multiplicar por el ponderador correcto** (§1).
3. Para series temporales largas (pre y post 4T2023), usar solo el set de variables
   comunes; para informalidad/ingresos desagregados, restringir a T4-2023+.
4. Tratar los códigos de no respuesta (`-9`, `9/99/999`, `0`) antes de promediar montos.
5. Edad = `CH06`; sexo = `CH04`; nivel educativo = `NIVEL_ED`; condición de actividad =
   `ESTADO`; categoría ocupacional = `CAT_OCUP`; informalidad = `EMPLEO`/`SECTOR`;
   ingreso del hogar = `ITF`/`IPCF` (+ deciles).
