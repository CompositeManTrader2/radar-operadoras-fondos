# Universo de operadoras de fondos de inversión en México

**Fecha de investigación:** 10 de noviembre de 2026
**Propósito:** priorizar la cobertura comercial de la Mesa de Capitales de Punto Casa de Bolsa entre las sociedades operadoras de fondos de inversión (SOFI) que operan acciones.
**Ya cubiertas:** Finaccess México y Fondos de Inversión Multiva (solo se registra si tienen casa de bolsa hermana).

## Fuentes y método

1. **Padrón de Entidades Supervisadas de la CNBV (PES).** Es la fuente del universo. El clasificador se carga en un iframe desde la página del sector, en https://www.cnbv.gob.mx/SECTORES-SUPERVISADOS/SOCIEDADES-DE-INVERSION/Paginas/Padr%C3%B3n-de-Entidades-Supervisadas.aspx. El clasificador está en http://pes.cnbv.gob.mx/Clasificador y sus listados se consultan con un parámetro:
   - `Ejemplo?Aux=457`: SOFI en instrumentos de deuda y de renta variable (29 entidades).
   - `Aux=459`: SOFI limitadas (2).
   - `Aux=18`: casas de bolsa (35).
   - `Aux=1`: controladoras de grupos financieros (22).
   - El subsector genérico `Aux=449` (SOFI) no devuelve registros.
2. **Portafolio de Información de la CNBV (sector 52, Fondos de inversión).** Índice de reportes: https://portafolioinfo.cnbv.gob.mx/Paginas/Reporte.aspx?s=52&t=2&st=0&ti=0&sti=0&n=0&tp=0. Se usaron tres archivos oficiales (.xlsm) publicados el 14-oct-2026:
   - **R1 (activos netos diarios por fondo y operadora)**, 2.º semestre de 2026: https://portafolioinfdoctos.cnbv.gob.mx/Documentacion/minfo/XLS/52/Reporte1/052_1G_R1_2026_S2.xlsm. Corte usado: **31-ago-2026**, que es el último disponible. Las cifras de activos netos de este documento suman los fondos de cada operadora en esa fecha. El total del sistema da 5,334,105 mdp, coherente con los "más de 5 billones" que la AMIB reportó en 2026.
   - **R7 (cartera de valores mensual por fondo, título por título)**, 2026: https://portafolioinfdoctos.cnbv.gob.mx/Documentacion/minfo/XLS/52/Reporte7/052_1G_R7_2026.xlsm. Corte usado: **agosto de 2026**, con 18,002 posiciones. De aquí sale si cada operadora tiene "acciones en directo", con estas claves de tipo de valor:
     - BMV: TV `1`, `41` y `0`.
     - SIC: `1A`, `1ASP`, `1ESP` y `1MSP`.
     - ETF/trackers: `1I` y `1ISP` (extranjeros) y `1B` (locales). No cuentan como acciones en directo.
   - R5 2023+ (contratos por fondo): https://portafolioinfdoctos.cnbv.gob.mx/Documentacion/minfo/XLS/52/Reporte5/052_1G_R5_2023.xlsm. Solo se consultó como apoyo.
3. **AMIB (amib.com.mx).** El sitio es una aplicación AngularJS. Su directorio público de asociados solo incluye casas de bolsa, así que no se encontró un listado de operadoras asociadas ni la estadística mensual por operadora en una URL pública. Las cifras de la AMIB solo aparecen citadas en prensa (El CEO, Rankia).
4. **Sitios de cada operadora**, para las páginas de cartera y DICI.

**Criterio de ranking:**
1. Sin casa de bolsa hermana.
2. Con acciones en directo, no solo ETFs.
3. Tamaño (activos netos).

A petición del encargo, los grupos bancarios se colocan al final.

## Tabla priorizada

Montos en millones de pesos (mdp). Fuentes de las columnas:
- **AN 31-ago-26:** activos netos según CNBV R1.
- **Acc. BMV y Acc. SIC directo (ago-26):** valor a mercado de acciones en directo según CNBV R7; entre paréntesis, el número de emisoras distintas en BMV.
- **CB hermana:** padrón CNBV de casas de bolsa (`Aux=18`).

| # | Operadora (nombre comercial) | Clave CNBV | Grupo | CB hermana | ¿Acciones en directo? | AN 31-ago-26 | Acc. BMV directo | Acc. SIC directo | ETF/trackers |
|---|---|---|---|---|---|---:|---:|---:|---:|
| **Nivel 1: sin casa de bolsa hermana** | | | | | | | | | |
| 1 | BlackRock México | IMPFOND | BlackRock Inc. (EE. UU.) | No | Sí | 987,837 | 4,378 (41) | 26,369 | 190,343 |
| 2 | SURA Investments / SURA IM México | SIM | SURA Asset Management (Colombia) | No | Sí | 125,059 | 4,442 (35) | 0 | 13,963 |
| 3 | Principal Fondos de Inversión | PRINPAL | Principal Financial Group (EE. UU.) | No | Sí | 58,094 | 364 (35) | 31 | 3,038 |
| 4 | Franklin Templeton México | OPFRANK | Franklin Resources (EE. UU.) | No | Sí, solo SIC | 41,621 | 0 | 869 | 12,320 |
| 5 | Skandia Operadora de Fondos | SKANDIA | Skandia (internacional) [POR CONFIRMAR controlador] | No | Sí | 35,319 | 1,667 (24) | 0 | 2,491 |
| 6 | Vinci Compass (Compass Investments de México) | SEICOMP | Vinci Compass (Brasil/Chile) | No | Sí (15% de su cartera en BMV) | 22,156 | 3,409 (39) | 2,294 | 2,439 |
| — | *Finaccess México (ya cubierta)* | FACCESS | Finaccess (independiente) | No | Sí | 16,012 | 769 (16) | 2,688 | 1,935 |
| 7 | Azimut México / Más Fondos | AZMT-MX | Azimut Holding (Italia) | No | Sí | 10,729 | 246 (25) | 584 | 842 |
| 8 | Operadora de Fondos Nafinsa | OPNAFIN | Nacional Financiera (banca de desarrollo) | No | Marginal (7 mdp) | 115,864 | 7 (21) | 0 | 319 |
| 9 | Operadora Mifel | OPMIFEL | Grupo Financiero Mifel | No | Marginal (31 mdp) | 6,671 | 31 (35) | 0 | 39 |
| 10 | Fondos de Inversión Afirme | OAFIRME | Afirme Grupo Financiero | No | No | 6,822 | 0 | 0 | 0 |
| 11 | CI Fondos | CIFONDO | Ex Grupo CIBanco [POR CONFIRMAR] | No en el padrón vigente | No | 141 | 0 | 0 | 18 |
| 12 | GAF Operadora (SOFI limitada) | OPLGAF | [POR CONFIRMAR] | [POR CONFIRMAR] | [POR CONFIRMAR] | sin datos en R1 | — | — | — |
| 13 | Operadora COVAF (SOFI limitada) | OPLCOVAF | [POR CONFIRMAR] | [POR CONFIRMAR] | [POR CONFIRMAR] | sin datos en R1 | — | — | — |
| **Nivel 2: con casa de bolsa hermana, grupos no bancarios** | | | | | | | | | |
| 14 | Operadora Actinver | OACTIN | GF Actinver | Sí: Actinver CB | Sí | 351,851 | 9,786 (61) | 15,976 | 32,628 |
| 15 | GBM Administradora de Activos | OPGBM | Grupo Bursátil Mexicano | Sí: GBM CB | Sí (24.6% de su cartera) | 203,876 | 50,177 (80) | 15,317 | 32,763 |
| 16 | Operadora Valmex | OVALMEX | Valmex | Sí: Valores Mexicanos CB | Sí | 88,753 | 432 (35) | 15,424 | 25,384 |
| 17 | Monex Operadora de Fondos | OPMONEX | Monex GF | Sí: Monex CB | Sí (marginal) | 39,333 | 64 (34) | 0 | 145 |
| 18 | INVEX Operadora | OPINVEX | INVEX GF | Sí: INVEX CB | Sí | 33,420 | 190 (23) | 806 | 4,172 |
| 19 | Finamex Inversiones | OPFFINX | Finamex | Sí: CB Finamex | Sí (33.6% de su cartera) | 25,701 | 8,652 (41) | 52 | 2,767 |
| — | *Fondos de Inversión Multiva (ya cubierta)* | OPMULTI | GF Multiva | **Sí: Casa de Bolsa Multiva** | Sí | 18,860 | 219 (31) | 95 | 2,136 |
| 20 | BTG Pactual Gestora de Fondos | OPBTG | BTG Pactual (Brasil) | Sí: BTG Pactual CB | Sí (85% de su cartera) | 681 | 582 (14) | 0 | 0 |
| 21 | KPTL México Operadora | OPKPTL | Kapital México GF | Sí: Kapital México CB | No | 11,475 | 0 | 3 | 398 |
| 22 | Value Operadora | OPVALUE | Value GF | Sí: Value CB | No (1 emisora, ~0) | 7,064 | 0 | 0 | 121 |
| 23 | Operadora Punto | OPUNTO | Grupo Punto (grupo propio) | Sí: Punto CB | No | 102 | 0 | 0 | 0 |
| **Nivel 3: grupos bancarios (todos con casa de bolsa hermana)** | | | | | | | | | |
| 24 | BBVA Asset Management México | OPBBVAG | GF BBVA México | Sí: CB BBVA México | Sí | 1,319,874 | 7,451 (23) | 22,244 | 280,021 |
| 25 | Operadora de Fondos Banorte | OIXE | GF Banorte | Sí: CB Banorte | Sí | 515,926 | 5,185 (41) | 7,332 | 53,345 |
| 26 | SAM Asset Management (Santander) | SANTAND | Santander | Sí: CB Santander | Sí | 507,690 | 5,249 (32) | 12,385 | 39,960 |
| 27 | HSBC Global Asset Management México | OPHSBC | GF HSBC | Sí: HSBC CB | Sí | 342,257 | 2,920 (34) | 1,342 | 21,070 |
| 28 | Scotia Fondos | OSCOTIA | GF Scotiabank Inverlat | Sí: ScotiaInverlat CB | Sí | 271,430 | 1,998 (22) | 35,778 | 25,563 |
| 29 | Operadora Inbursa | OPINBUR | GF Inbursa | Sí: Inversora Bursátil | Sí (37.8% de su cartera) | 169,488 | 64,076 (70) | 14,438 | 7,482 |

Notas a la tabla:
- **Nafinsa y Mifel** están en el nivel 1 y no tienen casa de bolsa, pero su tenencia directa es testimonial. Por eso quedan debajo de las operadoras con acciones reales.
- **Franklin Templeton** no tiene acciones de la BMV. Su tenencia directa es solo de acciones del SIC.
- Si se pondera la **intensidad en BMV** y no solo el tamaño, dentro del nivel 1 destacan Compass (3,409 mdp, 15% de su cartera), SURA (4,442) y BlackRock (4,378), seguidas de Skandia (1,667).
- **Bajas del padrón.** Intercam, Vector y CIBanco (señalados por el gobierno de EE. UU. en junio de 2025) ya no tienen operadora ni casa de bolsa en el padrón vigente. Según El CEO, los fondos de Vector pasaron a Finamex (ver Huecos).

## Notas por operadora

### Nivel 1: sin casa de bolsa hermana

**1. BlackRock México Operadora, S.A. de C.V., SOFI**
- **Web:** https://www.blackrock.com/mx. Es la antigua Impulsora de Fondos Banamex, de ahí la clave IMPFOND.
- **Grupo y CB hermana:** BlackRock Inc. No tiene casa de bolsa en México; ninguna de las 35 del padrón (`Aux=18`) pertenece a BlackRock.
- **Acciones en directo:** sí. En agosto de 2026 tenía 41 emisoras BMV por 4,378 mdp, con GMEXICO, GFNORTE, AMX, FEMSA, WALMEX y CEMEX al frente, más 26,369 mdp en acciones SIC. El grueso de su exposición sigue siendo en trackers (iShares): 190,343 mdp.
- **Tamaño:** 987,837 mdp, la segunda operadora del sistema.
- **Cartera y DICI:** las posiciones se publican en `https://www.blackrock.com/mx/intermediarios/literature/holdings/monthly-position-sp-mx-x{clave}.pdf`. Ejemplo verificado (HTTP 200): https://www.blackrock.com/mx/intermediarios/literature/holdings/monthly-position-sp-mx-xblkdip.pdf. También existe la versión `weekly-position-...`, y Citi aloja copias de los DICI (citigroup.com/rcs/citigpa/storage/public/Mexico/{CLAVE}_DocumentoClaveActualizacionAnual.pdf).
- **Descubribilidad:** alta. Las URL son estables y predecibles por clave de fondo.

**2. SURA Investment Management México, S.A. de C.V., SOFI**
- **Web:** https://www.surainvestments.com/mx.
- **Grupo y CB hermana:** SURA Asset Management (Grupo SURA). No tiene casa de bolsa en el padrón CNBV.
- **Acciones en directo:** sí. Tenía 35 emisoras BMV por 4,442 mdp (GMEXICO, GFNORTE, FEMSA, AMX, WALMEX, CEMEX).
- **Tamaño:** 125,059 mdp, en 36 fondos.
- **Cartera y DICI:** https://www.surainvestments.com/mx/investment-management/rendimiento-fondos. Las carteras mensual y semanal se piden por JavaScript a una API (`/cs-api-sites-suraim/v1/files/type-file-cartera-mensual`). Monex aloja copias de los DICI (monex.com.mx/portal/download/fondos2/DICI SUR*.pdf).
- **Descubribilidad:** baja. La página depende de JavaScript y de una API, sin URL de PDF estable.

**3. Principal Fondos de Inversión, S.A. de C.V., Operadora de Fondos de Inversión**
- **Web:** https://principal.com.mx/am.
- **Grupo y CB hermana:** Principal Financial Group. No tiene casa de bolsa en el padrón.
- **Acciones en directo:** sí. Tenía 35 emisoras BMV por 364 mdp. Su fondo PRINRVA está en la categoría "Especializado en Acciones Nacionales" según su DICI.
- **Tamaño:** 58,094 mdp.
- **Cartera y DICI:** la cartera se consulta en `https://linea.prod.principal.com.mx/carteras/cartera.aspx?fondo={CLAVE}&frec=mes` (HTML, HTTP 200 con PRINRVA). El DICI está en https://www.principal.com.mx/PRINRVA-DICI. Los estados de valuación trimestrales están en principal.com.mx/sites/default/files/AAAA-MM/...
- **Descubribilidad:** media-alta. Las URL son paramétricas y predecibles, aunque la cartera viene en HTML y no en PDF.

**4. Franklin Templeton Asset Management México, S.A. de C.V., SOFI**
- **Web:** https://www.franklintempleton.com.mx. El sitio redirige por JavaScript.
- **Grupo y CB hermana:** Franklin Resources. No tiene casa de bolsa en el padrón.
- **Acciones en directo:** solo SIC (869 mdp). No tiene acciones BMV y opera sobre todo vía fondos o trackers: TEMGBIA invierte 99.9% en el fondo luxemburgués.
- **Tamaño:** 41,621 mdp.
- **Cartera y DICI:** copias en Citi (citigroup.com/rcs/citigpa/storage/public/Mexico/{CLAVE}_carteramensual_2024.pdf; el nombre del archivo no cambia aunque el contenido sea de 2026) y en Monex (DICI mensuales `DICI {CLAVE} MMAA.pdf`).
- **Descubribilidad:** media. Depende de los distribuidores; no se ubicó la página propia [POR CONFIRMAR].

**5. Skandia Operadora de Fondos, S.A. de C.V., SOFI**
- **Web:** https://skandiamx.com/fondos-de-inversion.
- **Grupo y CB hermana:** Skandia (antes Old Mutual) [POR CONFIRMAR controlador final]. No tiene casa de bolsa en el padrón.
- **Acciones en directo:** sí. Tenía 24 emisoras BMV por 1,667 mdp, sobre todo en SK-RVMX.
- **Tamaño:** 35,319 mdp, en 5 fondos.
- **Cartera y DICI:** el patrón es `https://hubdigital.skandia.com.mx/portalpublico/Fondos%20de%20inversi%C3%B3n/FONDOS%20SK/{DEUDA|RENTA%20VARIABLE}/{FONDO}/Prospecto_OldMutual_OM{X}_Cartera_Mensual.pdf`. Ejemplo verificado (HTTP 200): https://hubdigital.skandia.com.mx/portalpublico/Fondos%20de%20inversi%C3%B3n/FONDOS%20SK/RENTA%20VARIABLE/SK-RVMX/Prospecto_OldMutual_OMRVMX_Cartera_Mensual.pdf. El DICI sigue el patrón `.../SK-RVMX/DICI_SK-RVMX.pdf`.
- **Descubribilidad:** alta. El nombre del archivo es fijo y se sobrescribe cada mes.

**6. Compass Investments de México, S.A. de C.V., SOFI (Vinci Compass)**
- **Web:** https://latam.vincicompass.com/es/mexico/fondos-asset-management/.
- **Grupo y CB hermana:** Vinci Compass. No tiene casa de bolsa en el padrón.
- **Acciones en directo:** sí, y es el candidato con mayor intensidad relativa. Tenía 39 emisoras BMV por 3,409 mdp (PINFRA, GMEXICO, GFNORTE, CEMEX, FEMSA, GCC) y 2,294 mdp en SIC.
- **Tamaño:** 22,156 mdp, en 16 fondos. También publica fondos con marca BX+ (BXCAP, BX+4, BX+USD) [POR CONFIRMAR relación con Ve por Más].
- **Cartera y DICI:** el patrón es `https://latam.vincicompass.com/wp-content/uploads/mexico/Fondos/Fondos%20Renta%20Variable/{FONDO}/CARTERA%20MENSUAL/COMPASS{FONDO}PublicacionesAAAAMMDD.pdf`. Ejemplo verificado: .../COLRVL/CARTERA%20MENSUAL/COMPASSCOLRVLPublicaciones20260930.pdf. El DICI está en `.../{FONDO}/DOCUMENTO CON INFORMACIÓN CLAVE/DICI_{FONDO}_MMAA.pdf`.
- **Descubribilidad:** alta. WordPress con rutas legibles y fecha en el nombre del archivo.

**Finaccess México (ya cubierta).** No tiene casa de bolsa hermana en el padrón CNBV. AN 16,012 mdp.

**7. Operadora de Fondos Azimut-México, S.A. de C.V., SOFI (Más Fondos)**
- **Web:** https://azimut.mx.
- **Grupo y CB hermana:** Azimut Holding (Italia). No tiene casa de bolsa en el padrón.
- **Acciones en directo:** sí. Tenía 25 emisoras BMV por 246 mdp (fondo AZMT-V1, "especializada en acciones") y 584 mdp en SIC.
- **Tamaño:** 10,729 mdp.
- **Cartera y DICI:** la oferta de fondos está en https://azimut.mx/oferta-de-fondos/ y se carga por JavaScript (`Carteras('OFERTA')`). Los documentos están en azimut.com.mx/ST_WEB/...
- **Descubribilidad:** baja-media. Depende de JavaScript [POR CONFIRMAR ruta de carteras].

**8. Operadora de Fondos Nafinsa, S.A. de C.V., SOFI**
- **Web:** https://www.nafin.com.
- **Grupo y CB hermana:** Nacional Financiera (banca de desarrollo). No tiene casa de bolsa.
- **Acciones en directo:** marginal, 7 mdp. Su fondo NAFINDX replica el IPC; 2,482 mdp de sus fondos son de renta variable.
- **Tamaño:** 115,864 mdp, casi todo en deuda.
- **Cartera y DICI:** solo se hallaron copias en distribuidores, por ejemplo https://banco.hey.inc/content/dam/heybanco/folletos/CarteraMensualNAFINDX.pdf. La página propia está [POR CONFIRMAR].

**9. Operadora Mifel, S.A. de C.V., SOFI, GF Mifel**
- **Web:** https://www.mifel.com.mx.
- **Grupo y CB hermana:** el GF Mifel no tiene casa de bolsa en el padrón.
- **Acciones en directo:** marginal, 31 mdp en 35 emisoras (patrón de fondo índice).
- **Tamaño:** 6,671 mdp.
- **Cartera y DICI:** [POR CONFIRMAR].

**10. Fondos de Inversión Afirme, S.A. de C.V., SOFI, Afirme GF**
- **Web:** https://www.afirme.com/Personas/Fondos-de-inversion.html.
- **Grupo y CB hermana:** Afirme GF no tiene casa de bolsa en el padrón.
- **Acciones en directo:** no. Su cartera de agosto de 2026 no tenía renta variable.
- **Tamaño:** 6,822 mdp.
- **Cartera y DICI:** [POR CONFIRMAR].

**11. CI Fondos, S.A. de C.V., SOFI**
- **Web:** [POR CONFIRMAR].
- **Grupo y CB hermana:** históricamente ligada a CIBanco y CI Casa de Bolsa. CI Casa de Bolsa ya no aparece en el padrón de casas de bolsa, y Banorte rescindió su distribución el 24-sep-2025 (https://www.banorte.com/dam/jcr:d6631c7c-4dd4-44aa-9db4-8c962d79dfba/Rescision-contrato-ci-fondos.pdf).
- **Tamaño:** AN de 141 mdp, sin acciones BMV. Sin interés comercial.

**12-13. GAF Operadora y Operadora COVAF (SOFI limitadas)**
- Figuran en el padrón (`Aux=459`), pero no tienen fondos en R1 ni en R7 de agosto de 2026. Todo lo demás está [POR CONFIRMAR].

### Nivel 2: con casa de bolsa hermana, grupos no bancarios

Todas las casas de bolsa hermanas están confirmadas en el padrón (`Aux=18`).

- **Operadora Actinver (OACTIN):** web https://actinver.com. Hermana de Actinver CB. Tenía 61 emisoras BMV por 9,786 mdp. AN 351,851 mdp. Cartera y DICI [POR CONFIRMAR].
- **GBM Administradora de Activos (OPGBM):** web https://www.gbmfondos.com.mx. Hermana de GBM CB. Es la operadora con más acciones BMV fuera de Inbursa: 80 emisoras por 50,177 mdp. AN 203,876 mdp. Cartera mensual en `https://www.gbmfondos.com.mx/files/pdf/soluciones/fisicas/carteramensual/cartera_mensual_{FONDO}.pdf`. Descubribilidad alta.
- **Operadora Valmex (OVALMEX):** web https://www.valmex.com.mx. Hermana de Valores Mexicanos CB, en el mismo grupo aunque no sea un GF formal. Tenía 432 mdp en BMV y 15,424 en SIC. AN 88,753 mdp. Cartera y DICI [POR CONFIRMAR].
- **Monex Operadora de Fondos (OPMONEX):** web https://www.monex.com.mx. Hermana de Monex CB. Tenía 64 mdp en BMV. AN 39,333 mdp. Publica un PDF consolidado mensual con el patrón `monex.com.mx/portal/download/info/CARTERAS MENSUALES {MES} {AA}.pdf`.
- **INVEX Operadora (OPINVEX):** web https://www.invex.com. Hermana de INVEX CB. Tenía 190 mdp en BMV y 806 en SIC. AN 33,420 mdp. Cartera [POR CONFIRMAR].
- **Finamex Inversiones (OPFFINX):** web https://www.finamex.com.mx. Hermana de CB Finamex. Tenía 41 emisoras BMV por 8,652 mdp, 33.6% de su cartera. AN 25,701 mdp. Según El CEO, absorbió el negocio de fondos de Vector. Cartera [POR CONFIRMAR].
- **Fondos de Inversión Multiva (ya cubierta):** sí tiene casa de bolsa hermana, Casa de Bolsa Multiva, S.A. de C.V., GF Multiva (padrón `Aux=18`).
- **BTG Pactual Gestora (OPBTG):** web https://www.btgpactual.com. Hermana de BTG Pactual CB. Solo reportó un fondo (BTGALFA, 681 mdp, 85% en acciones BMV).
- **KPTL México Operadora (OPKPTL)** y **Value Operadora (OPVALUE):** tienen casa de bolsa hermana (Kapital México CB y Value CB) y no tienen acciones en directo relevantes.
- **Operadora Punto (OPUNTO):** pertenece al grupo de Punto Casa de Bolsa (102 mdp, un fondo de deuda). No es un objetivo comercial.

### Nivel 3: grupos bancarios

Todos tienen casa de bolsa hermana confirmada en el padrón.
- **BBVA AM (OPBBVAG):** la mayor del sistema, con 1,319,874 mdp. Tiene 7,451 mdp en BMV, pero su renta variable va sobre todo en trackers (280,021 mdp) y en fondos propios (116,751 mdp).
- **Banorte (OIXE):** 515,926 mdp. Las carteras están en `banorte.com/cms/casadebolsabanorteixe/fondosdeinversion/...`, con rutas legibles.
- **SAM / Santander (SANTAND):** 507,690 mdp. La razón social de la operadora no incluye "Grupo Financiero"; se considera hermana de CB Santander por la matriz común [POR CONFIRMAR estructura accionaria].
- **HSBC (OPHSBC):** 342,257 mdp. Publica una cartera trimestral en hsbc.com.mx/content/dam/hsbc/mx/documents/inversiones/global-asset/...
- **Scotia Fondos (OSCOTIA):** 271,430 mdp. Las carteras están en `cdn.aglty.io/scotia-bank-mexico/spanish/pdf/personas/fondos-de-inversion/carteras/CM_{FONDO}.pdf`, un CDN con nombres fijos.
- **Inbursa (OPINBUR):** 169,488 mdp. Es la mayor tenedora de acciones BMV en directo (64,076 mdp en 70 emisoras), pero las ejecuta Inversora Bursátil.

## Huecos [POR CONFIRMAR]

1. **AMIB:** no se ubicó en amib.com.mx una lista pública de operadoras asociadas ni la estadística mensual por operadora. El sitio es una SPA y el directorio solo lista casas de bolsa. Los 29 asociados que cita la prensa coinciden con las 29 SOFI de deuda y RV del padrón CNBV.
2. **GAF Operadora y Operadora COVAF:** falta saber grupo, sitio, fondos y si tienen casa de bolsa.
3. **CI Fondos:** falta confirmar su situación corporativa tras la salida de CIBanco y CI Casa de Bolsa, así como su sitio web.
4. **Intercam, Vector y CIBanco:** sus operadoras ya no figuran en el padrón. Hay que confirmar a quién se transfirieron los fondos de Intercam. Para Vector, la prensa (El CEO, 22-may-2026) menciona el acuerdo Vector/Finamex.
5. **Skandia:** falta confirmar el controlador final. El hub de Skandia aloja documentos de fondos SURA (SURCETE), así que también hay que confirmar si existe una relación de distribución o una operación corporativa entre SURA y Skandia.
6. **Vinci Compass:** falta confirmar la relación con los fondos BX+ (antes de Ve por Más), cuya casa de bolsa sigue vigente.
7. **SAM Asset Management:** falta confirmar si pertenece al GF Santander México o a la matriz global, aunque en ambos casos comparte grupo con CB Santander.
8. **Páginas de cartera y DICI:** no se verificaron las de Nafinsa, Mifel, Afirme, Actinver, Valmex, INVEX, Finamex, Franklin (sitio propio) y Azimut (ruta exacta). La alternativa universal es el reporte **R7 de la CNBV**: un archivo por año con la cartera mensual título por título de todas las operadoras, con unos 45 días de rezago (los datos de agosto se publicaron el 14 de octubre).
9. **Cifras:** los activos netos son la suma de los fondos reportados en R1 al 31-ago-2026. Las operadoras con pocos fondos en ese corte pueden estar subestimadas (por ejemplo, BTG con 1 fondo, o Value) [POR CONFIRMAR contra la estadística de la AMIB].
