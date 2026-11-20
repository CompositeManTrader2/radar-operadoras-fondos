# Validación de datos: todas las operadoras

Revisión del 2026-11-20. Se compararon los fondos más grandes de cada operadora (hasta tres) contra los
documentos públicos de la propia operadora (DICI, cartera mensual, estados financieros, fichas). Corte del
portal: 30-sep-2026 (CNBV R7) salvo Finaccess, Multiva y Compass (cartera de la operadora al 30-oct-2026).
Kapital y CI Fondos se validaron antes con más detalle: ver [validacion_kapital_ci_fondos.md](validacion_kapital_ci_fondos.md).

## Resumen

- Fondos revisados: **76** en **27** operadoras (más los 14 de Kapital y CI Fondos).
- Coincide: **20**
- Diferencia menor: **25**
- Diferencia relevante: **3**
- Sin documento comparable: **28**

Cómo leer el veredicto:

- **Coincide**: mismo corte y mismo total (o diferencia < 1 %), con las principales posiciones iguales.
- **Diferencia menor**: casi siempre el documento público es de octubre y el portal de septiembre; la
  diferencia es del mes (flujos, rotación de series), no del portal.
- **Diferencia relevante**: diferencia > 10 % o una posición grande que no aparece; se revisó a mano (abajo).
- **Sin documento comparable**: la operadora no publica un documento de la fecha, el sitio bloquea el
  acceso automatizado (no se evadió) o el documento no trae cifras.

### Errores del modelo que salieron de esta validación (ya corregidos)

1. **Fondos extranjeros vía SIC (tipo de valor 56SP)** se contaban como deuda porque así los describe la
   CNBV. Afectaba 39 posiciones en 21 fondos (~15,900 mdp); SURGLOB (85.5 % en AMEGFMU) y ALTER1+ (94 % en
   CGCG) aparecían por debajo de su mínimo de renta variable. Ahora se clasifican por subyacente
   (`radar/core/datos/fondos_extranjeros.csv`): 17 posiciones pasan a RV vía ETF/fondo extranjero; las de
   deuda o sin identificar siguen en RF y las no confirmadas aparecen en los huecos del one-pager.
2. **Actinver y BlackRock** estaban bloqueadas por ETFs nuevos en el R7 de septiembre (ROBO, RSPD, ITA,
   EWK, CITY) y un tipo de valor nuevo (CHCA); se agregaron a los catálogos y ambas quedaron al día.
3. **Compass: documentos de un fondo asignados a otro.** El sitio de Compass enlaza en la página de I+CORP la
   cartera de octubre de AMVALOR, y en la de I+USD la de BX+USD. El radar tomaba la clave del fondo de esa
   cartera y le asignó a AMVALOR el prospecto de I+CORP (deuda): AMVALOR, con 98 % en renta variable,
   aparecía con régimen RV 0 %–0 %. Ahora la clave sale del DICI de la página y la cartera ajena se
   descarta con aviso; AMVALOR queda con RV 1 %–100 % (su prospecto, sept-2026, p. 7). I+CORP e I+USD
   conservan su cartera del 30-sep hasta que Compass publique la suya de octubre.

### Pendiente de decisión

- **Santander: ¿casa de bolsa hermana?** El portal marca que sí (matriz común). El DICI de USA-EQ dice que
  SAM Asset Management "NO es integrante de Grupo Financiero Santander México" y lista a Casa de Bolsa
  Santander como una distribuidora más (con Actinver y Citibanamex). Si la mesa decide que no es hermana,
  se quita el veto en `config/operadoras_cnbv.toml`.

### Controles que confirman los datos

- **Mismo corte, cifra exacta**: Monex (MONEXCP 22,624.0; MONEXM+ 16,414.9; MONXESG 78.7 mdp), Value
  (VALUEF2 2,887.6; VALUEF4 1,394.2 mdp), Franklin (estados financieros al 30-sep: diferencia 0.00 %–0.004 %)
  y Kapital (los siete fondos al peso contra su cartera mensual). Monex, Value y MIFIPC/INVEXGU se
  revisaron de nuevo directamente sobre el PDF.
- **Casa de bolsa hermana**: en ningún caso el documento contradice el dato del portal (Monex, Inbursa,
  INVEX y Punto la confirman; Mifel, Afirme, Azimut, Principal y BlackRock confirman que no hay).

## Veredicto por operadora

| Operadora | Corte portal | Fondos (veredicto) | Fuente oficial usada |
|---|---|---|---|
| BlackRock México | 2026-09-30 | BLKGUB1: Sin documento comparable; BLKDIN: Sin documento comparable; BLKFUSA: Sin documento comparable | 3 doc(s), datos al 2025-12-31, 2026-02-28 |
| SURA Investment Management | 2026-09-30 | FONDEO: Diferencia menor; SURCETE: Coincide; SUR-RV: Diferencia menor | 3 doc(s), datos al 2026-10-30 |
| Principal Fondos | 2026-09-30 | PRINFGU: Coincide; PRINFMP: Diferencia menor; PRINR55: Sin documento comparable | 2 doc(s), datos al 2026-10-30 |
| Franklin Templeton | 2026-09-30 | FT-LIQU: Coincide; FT-MEXA: Coincide; FT-USA1: Coincide | 6 doc(s), datos al 2026-09-30, 2026-10-30 |
| Skandia Operadora | 2026-09-30 | SK-DCP: Diferencia menor; SK-DEST: Diferencia menor; SK-RVST: Coincide | 3 doc(s), datos al 2026-10-30 |
| Operadora de Fondos Nafinsa | 2026-09-30 | BONDDIA: Sin documento comparable; NAFCDVI: Sin documento comparable; NAFINDX: Sin documento comparable | sin documento |
| Finaccess México | 2026-10-30 | AXESCP: Sin documento comparable; AXESMP: Sin documento comparable; AXESCAP: Sin documento comparable | sin documento |
| Fondos de Inversión Multiva | 2026-10-30 | MULTIRE: Sin documento comparable; MVJER: Sin documento comparable; MULTIEQ: Sin documento comparable | sin documento |
| Compass Investments | 2026-10-30 | I+LIQG: Coincide; STRAT: Coincide; AMVALOR: Coincide | 5 doc(s), datos al 2026-09-01, 2026-10-30 |
| BBVA Asset Management | 2026-09-30 | BBVALIQ: Diferencia menor; BBVAGOB: Diferencia menor; BBVAUS: Diferencia menor | 3 doc(s), datos al 2026-10-30 |
| Operadora de Fondos Banorte | 2026-09-30 | NTECT: Sin documento comparable; NTEGUB: Sin documento comparable; NTEUSA+: Sin documento comparable | sin documento |
| Santander Asset Management | 2026-09-30 | STERGOB: Sin documento comparable; FONSER1: Sin documento comparable; USA-EQ: Sin documento comparable | 1 doc(s), datos al 2025-12-31 |
| Scotia Fondos | 2026-09-30 | SCOTIA1: Diferencia menor; SBANKCP: Diferencia menor; SCOTUSA: Diferencia menor | 3 doc(s), datos al 2026-10-31 |
| HSBC Global Asset Management | 2026-09-30 | HSBC-D2: Diferencia menor; HSBCDC+: Diferencia menor; HSBCMEX: Sin documento comparable | 3 doc(s), datos al 2026-03-05, 2026-10-30 |
| Operadora Inbursa | 2026-09-30 | IBUPLUS: Diferencia menor; INBUMAX: Coincide; INBURSA: Diferencia menor | 6 doc(s), datos al 2026-10-31 |
| Operadora GBM | 2026-09-30 | GBM106: Sin documento comparable; MPAGORF: Sin documento comparable; NUMC: Sin documento comparable | sin documento |
| Operadora Actinver | 2026-09-30 | ACTIGOB: Diferencia menor; ACTIMED: Coincide; ACTIOP1: Coincide | 6 doc(s), datos al 2026-08-06, 2026-10-30 |
| Operadora Valmex | 2026-09-30 | VXGUBCP: Coincide; VLMXTEC: Diferencia menor; VLMXLPE: Sin documento comparable | 2 doc(s), datos al 2026-09-30, 2026-10-31 |
| Operadora Finamex | 2026-09-30 | AM2: Sin documento comparable; FMXPRE: Sin documento comparable; FMXSIC: Sin documento comparable | sin documento |
| Operadora INVEX | 2026-09-30 | INVEXGU: Diferencia relevante; INVEXMP: Coincide; INVEXTK: Diferencia menor | 6 doc(s), datos al 2026-10-30 |
| Monex Operadora | 2026-09-30 | MONEXCP: Coincide; MONEXM+: Coincide; MONXESG: Coincide | 3 doc(s), datos al 2026-09-30 |
| Value Operadora | 2026-09-30 | VALUEF2: Coincide; VALUEF4: Coincide; VALUEV6: Coincide | 1 doc(s), datos al 2026-09-30 |
| Azimut México | 2026-09-30 | AZMT-G1: Diferencia menor; AZMT-C1: Diferencia menor; AZMTEUA: Sin documento comparable | 2 doc(s), datos al 2026-10-30 |
| Mifel Operadora | 2026-09-30 | VALOR1F: Diferencia menor; VALOR3M: Diferencia menor; MIFIPC: Diferencia relevante | 5 doc(s), datos al 2025-12-31 (plantilla sin cifras; autorizacion 19/10/2026), 2026-10-30, plantilla sin cifras; autorizacion 19/10/2026 |
| Afirme Operadora | 2026-09-30 | AFIRMES: Diferencia menor; AFIRPLU: Diferencia menor | 3 doc(s), datos al 2026-10-30 |
| BTG Pactual | 2026-09-30 | BTGALFA: Diferencia menor | 2 doc(s), datos al 2026-10-30 |
| Operadora Punto | 2026-09-30 | AZTECA+: Diferencia relevante | 2 doc(s), datos al 2026-10-30 |

## Detalle por operadora

### BlackRock México (`blackrock`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| BLKGUB1 | DICI | 2025-12-31 | — | [www.citigroup.com](https://www.citigroup.com/rcs/citigpa/storage/public/Mexico/BLKGUB1_DocumentoClaveActualizacionAnual.pdf) |
| BLKDIN | DICI | 2025-12-31 | — | [www.citigroup.com](https://www.citigroup.com/rcs/citigpa/storage/public/Mexico/BLKDIN_DocumentoClaveActualizacionAnual.pdf) |
| BLKFUSA | DICI | 2026-02-28 | — | [www.blackrock.com](https://www.blackrock.com/mx/intermediarios/literature/fact-sheet/blkfusa-dici.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| BLKGUB1 | — | — | — | — | — / — | **Sin documento comparable** |
| BLKDIN | — | — | — | — | — / — | **Sin documento comparable** |
| BLKFUSA | — | — | — | — | — / — | **Sin documento comparable** |

- **BLKGUB1**: El DICI oficial (copia Citi) es de dic-2025 (top: BONDESF 260723 6.64%, 270401 6.04%, 260521 5.45%). La URL de blackrock.com para blkgub1 y blkdin devuelve 404. Portal ago-26 456,617 mdp (+6.2% vs dic, plausible pero no comparable). BONDESF 270401/270624/271104/270805/270909 aparecen en ambos. Comisiones/régimen: Serie B0-A total comisiones 0.47% = portal 0.0047 (coincide). Doc: cartera dic-2025 429,907.9 mdp; sin mezcla.
- **BLKDIN**: DICI dic-2025; portal ago-26 79,091.3. Distinta fecha. Comisiones/régimen: Serie B0-B total 0.77% (doc) vs portal 0.0077 (coincide). Doc cartera dic-2025 77,551.8 mdp.
- **BLKFUSA**: DICI de feb-2026, no hay ago/sep. No se extrajo top10/total (texto desordenado). Comisiones/régimen: No cotejado fila a fila.
- **Casa de bolsa hermana**: Distribuidoras: Banamex, Banco Citi Mexico y Citi Mexico Casa de Bolsa (Grupo Financiero Citi Mexico); ninguna es del mismo grupo que BlackRock (coincide con portal: false)
- **Notas**: Ningun documento de ago/sep-2026 disponible; DICI vigentes son de dic-2025 y feb-2026.

### SURA Investment Management (`sura`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| FONDEO | cartera mensual | 2026-10-30 | — | [www.suraim.com.mx](https://www.suraim.com.mx/Archivos/Fondos/Carteras%20Mensuales/FONDEO.pdf) |
| SURCETE | cartera mensual | 2026-10-30 | — | [www.suraim.com.mx](https://www.suraim.com.mx/Archivos/Fondos/Carteras%20Mensuales/SURCETE.pdf) |
| SUR-RV | cartera mensual | 2026-10-30 | — | [www.suraim.com.mx](https://www.suraim.com.mx/Archivos/Fondos/Carteras%20Mensuales/SUR-RV.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| FONDEO | 18,837.0 | 17,723.1 | +6.3 % | 3 de 5 (BONDESF 300124, 310807, BONOS 300228) | Reporto 93.83%, directo CETES 4.63%, otros 1.53% / EFE 95.1 / RF 4.9 | **Diferencia menor** |
| SURCETE | 17,197.0 | 17,113.2 | +0.5 % | 5 de 5 (CETES 261126 13.07 vs 15.37 difiere 2.3 pts; resto +-1) | Directo 96.70%, otros 3.30% / RF 97.0 / EFE 3.0 | **Coincide** |
| SUR-RV | 5,223.7 | 4,941.1 | +5.7 % | 5 de 5 en top10 (SPXS1, 500U, XSPU1, CEMA, XMED); % de XSPU1, CEMA, XMED difieren >1 pt | RV 99.29% / RV 99.8 / EFE 0.2 | **Diferencia menor** |

- **FONDEO**: Doc un mes posterior al ultimo corte del portal; activo neto doc 18,816.0. Comisiones/régimen: n/a (cartera no trae regimen/comisiones).
- **SURCETE**: Activo neto doc 17,175.5. Doc un mes posterior. Comisiones/régimen: n/a.
- **SUR-RV**: Rotacion de pesos un mes despues (XMED 13.3 a 5.26). Activo neto doc 5,205.9. Comisiones/régimen: n/a.
- **Notas**: No se hallo DICI de agosto/septiembre (Monex devuelve pagina generica a descargas automaticas). Se uso la cartera mensual oficial de suraim.com.mx (30-oct-2026); el sitio solo publica la vigente.

### Principal Fondos (`principal`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| PRINFGU | DICI | 2026-10-30 | — | [principal.com.mx](https://principal.com.mx/PRINFGU-DICI) |
| PRINFMP | DICI | 2026-10-30 | — | [principal.com.mx](https://principal.com.mx/PRINFMP-DICI) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| PRINFGU | 42,402.8 | 42,053.1 | +0.8 % | 4 de 5 (CETES 270513 17.77 vs 17.78; 270318 11.78 vs 12.72; 270708 6.44 vs 4.57; 270624 5.77 vs 4.75; 270401 fuera del top10 portal) | DICI no da mezcla RV/RF/EFE / RF 96.4 / EFE 3.6 | **Coincide** |
| PRINFMP | 3,515.2 | 3,366.1 | +4.4 % | 4 de 5 (CETES 270708 14.46 vs 16.10 difiere 1.6; 271028, 280217, 280412 +-1; 271014 ausente) | n/a / RF 97.3 / EFE 2.7 | **Diferencia menor** |
| PRINR55 | — | — | — | — | — / — | **Sin documento comparable** |

- **PRINFGU**: Doc un mes posterior. Comisiones/régimen: Serie A total 0.02% = portal 0.0002 (coincide); regimen RV 0 coincide.
- **PRINFMP**: Doc un mes posterior; CEMEX, MSFIN, LALAC tambien en ambos. Comisiones/régimen: no cotejado.
- **PRINR55**: principal.com.mx/PRINR55-DICI da 404; principal.com.mx/PRINR55 es un PDF de 1 pagina sin texto extraible. Comisiones/régimen: Sin documento.
- **Casa de bolsa hermana**: DICI lista Actinver Casa de Bolsa, GBM, Casa de Bolsa Finamex, Kuspit Casa de Bolsa, Banco del Bajio, Mifel, Banregio, Azimut, Skandia, KPTL, O'Rourke, Fondika; ninguna del grupo Principal (coincide con portal)
- **Notas**: No hay DICI de ago/sep; los vigentes son de oct-2026.

### Franklin Templeton (`franklin`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| FT-LIQU | estados financieros | 2026-09-30 | — | [franklintempletonprod.widen.net](https://franklintempletonprod.widen.net/content/1ttk0kig6v/original/FT-LIQU_Estados_Financieros_30092026.pdf) |
| FT-LIQU | DICI | 2026-10-30 | 2026-10-30 | [franklintempletonprod.widen.net](https://franklintempletonprod.widen.net/content/9p20xdem52/original/20573-documento-clave-es-mx.pdf) |
| FT-MEXA | estados financieros | 2026-09-30 | — | [franklintempletonprod.widen.net](https://franklintempletonprod.widen.net/content/cimpmfximn/original/FT-MEXA_Estados_Financieros_30092026.pdf) |
| FT-MEXA | DICI | 2026-10-30 | 2026-10-30 | [franklintempletonprod.widen.net](https://franklintempletonprod.widen.net/content/6y3ekuvxnl/original/29271-documento-clave-es-mx.pdf) |
| FT-USA1 | estados financieros | 2026-09-30 | — | [franklintempletonprod.widen.net](https://franklintempletonprod.widen.net/content/cpoo6zcw38/original/FT-USA1_Estados_Financieros_30092026.pdf) |
| FT-USA1 | DICI | 2026-10-30 | 2026-10-30 | [franklintempletonprod.widen.net](https://franklintempletonprod.widen.net/content/d3jhox3o2e/original/4405-documento-clave-es-mx.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| FT-LIQU | 23,185.4 | 23,184.5 | +0.0 % | 1 de 5 vs DICI oct (alta rotacion de reportos); EF no trae top10 | EF: inversiones 17,567.6 (75.8%), reportos 5,616.9 (24.2%) / RF 75.8 / EFE 24.2 | **Coincide** |
| FT-MEXA | 7,928.7 | 7,928.7 | +0.0 % | 5 de 5 vs DICI oct (IB1MXX 28.2 vs 27.73, VMSTX 27.13 vs 26.69, TBLLMX 21.75 vs 21.41, MB3M 20.78 vs 20.58; IBTMXX 1.63 vs 3.11) | EF: inversiones 7,928.7 todo en instrumentos de capital/indices / RV 0.5 / RF 99.5 (clasificacion portal) | **Coincide** |
| FT-USA1 | 961.2 | 961.2 | -0.0 % | 5 de 5 vs DICI oct (NVDA 7.6 vs 8.49, MSFT 7.36 vs 7.24, AAPL 6.84 vs 6.62, USPX 5.75 vs 4.82, MU 3.26 vs 3.93) | EF: inversiones 959.655 + bancos 1.555 / RV 99.8 / EFE 0.2 | **Coincide** |

- **FT-LIQU**: Capital contable EF 23,162.2. Total DICI oct 24,849.5 (+7.2% vs portal sep, un mes despues). Comisiones/régimen: Comisiones DICI BE 0.0340%, BE1 0.3884% = portal (0.00034, 0.003884); regimen RV 0 coincide.
- **FT-MEXA**: Total identico al EF. Activo EF 7,977.8, capital contable 7,970.3 (portal R1 ago 7,963.1). Comisiones/régimen: Comisiones por serie no cotejadas.
- **FT-USA1**: Total doc = inversiones + bancos del EF. Activo EF 965.0. Comisiones/régimen: Comisiones DICI BE 0.4798%, BE1 1.2841% = portal (0.004798, 0.012841).
- **Casa de bolsa hermana**: DICI solo remite a pagina web de distribuidores autorizados; sin lista
- **Notas**: JSON Franklin con 3Q26 estados financieros por fondo; DICI vigente de 30-oct-2026.

### Skandia Operadora (`skandia`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| SK-DCP | DICI | 2026-10-30 | — | [hubdigital.skandia.com.mx](https://hubdigital.skandia.com.mx/portalpublico/Fondos%20de%20inversi%C3%B3n/FONDOS%20SK/DEUDA/SK-DCP/DICI_SK-DCP.pdf) |
| SK-DEST | DICI | 2026-10-30 | — | [hubdigital.skandia.com.mx](https://hubdigital.skandia.com.mx/portalpublico/Fondos%20de%20inversi%C3%B3n/FONDOS%20SK/DEUDA/SK-DEST/DICI_SK-DEST.pdf) |
| SK-RVST | DICI | 2026-10-30 | — | [hubdigital.skandia.com.mx](https://hubdigital.skandia.com.mx/portalpublico/Fondos%20de%20inversi%C3%B3n/FONDOS%20SK/RENTA%20VARIABLE/SK-RVST/DICI_SK-RVST.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| SK-DCP | 20,732.6 | 20,116.0 | +3.1 % | 4 de 5 (CETES 261224, BPAG28 261105, UDIBONO 261203, BPAG28 270805; reporto 6.1% no separado en portal) | n/a / RF 90.3 / EFE 9.7 | **Diferencia menor** |
| SK-DEST | 7,084.7 | 6,891.4 | +2.8 % | 3 de 5 (BONOS 360221 11.1 vs 9.08; CETES 270708, 280803; fuera: BPAG28 290802, BPA182 320923 reporto) | n/a / RF 93.2 / EFE 6.8 | **Diferencia menor** |
| SK-RVST | 2,638.9 | 2,612.2 | +1.0 % | 5 de 5 (OMFL 15.7, RWL 14.5, QQQM 14.2, BBIN 13.1, FDT 11.0; todos +-1 pt) | RV ~98.8% (otros 1.2%) / RV 98.9 / EFE 1.1 | **Coincide** |

- **SK-DCP**: Doc un mes posterior (+3.1%). Comisiones/régimen: Comisiones: admin 1.10%, total 1.13% = portal (0.011/0.0113); regimen RV 0 coincide.
- **SK-DEST**: Doc un mes posterior (+2.8%). Comisiones/régimen: Serie B 1.40%/1.43%, E 1.20%/1.23% = portal.
- **SK-RVST**: Doc un mes posterior (+1.0%). Comisiones/régimen: Serie B 2.40%/2.46% = portal; RV 80-100 coincide.
- **Casa de bolsa hermana**: Distribuidora: la propia Skandia Operadora de Fondos; sin casa de bolsa del grupo (coincide)
- **Notas**: DICI de oct-2026; no hay ago/sep publicados.

### Operadora de Fondos Nafinsa (`nafinsa`)

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| BONDDIA | — | — | — | — | — / — | **Sin documento comparable** |
| NAFCDVI | — | — | — | — | — / — | **Sin documento comparable** |
| NAFINDX | — | — | — | — | — / — | **Sin documento comparable** |

- **BONDDIA**: ofnafin.com.mx bloquea acceso automatizado (pagina de bloqueo; no se evade). Busquedas no hallaron DICI/cartera 2026. Comisiones/régimen: Sin documento.
- **NAFCDVI**: ofnafin.com.mx bloquea acceso automatizado (pagina de bloqueo; no se evade). Busquedas no hallaron DICI/cartera 2026. Comisiones/régimen: Sin documento.
- **NAFINDX**: ofnafin.com.mx bloquea acceso automatizado (pagina de bloqueo; no se evade). Busquedas no hallaron DICI/cartera 2026. Unico DICI externo hallado (banco.hey.inc nafindx_pf DICI.pdf) es de ene-2025, no comparable (NAFTRAC 100%, cualitativamente igual al portal 99.85-99.98%). Comisiones/régimen: Sin documento.
- **Notas**: Sin documentos oficiales de ago/sep.

### Finaccess México (`finaccess`)

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| AXESCP | — | — | — | — | — / — | **Sin documento comparable** |
| AXESMP | — | — | — | — | — / — | **Sin documento comparable** |
| AXESCAP | — | — | — | — | — / — | **Sin documento comparable** |

- **AXESCP**: No se pudo obtener cartera/DICI de ago-oct 2026. finaccess.com.mx: las paginas de detalle (fondos_detalle.jsp) redirigen (303) a la portada sin documentos; /PDF/cartera.html trae una cartera de 2015 y /PDF/informe_axescp.pdf es del 4T11 (ambos obsoletos). Sin datos oficiales para contrastar.
- **AXESMP**: No se pudo obtener cartera/DICI de ago-oct 2026. finaccess.com.mx: las paginas de detalle (fondos_detalle.jsp) redirigen (303) a la portada sin documentos; /PDF/cartera.html trae una cartera de 2015 y /PDF/informe_axescp.pdf es del 4T11 (ambos obsoletos). Sin datos oficiales para contrastar.
- **AXESCAP**: No se pudo obtener cartera/DICI de ago-oct 2026. finaccess.com.mx: las paginas de detalle (fondos_detalle.jsp) redirigen (303) a la portada sin documentos; /PDF/cartera.html trae una cartera de 2015 y /PDF/informe_axescp.pdf es del 4T11 (ambos obsoletos). Sin datos oficiales para contrastar.
- **Notas**: Sin documento. Portal dice casa_de_bolsa_hermana=false; no verificado con documento oficial. El prospecto indica que la cartera mensual se publica en finaccess.com.mx en los primeros 5 dias habiles, pero no se encontro un enlace accesible.

### Fondos de Inversión Multiva (`multiva`)

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| MULTIRE | — | — | — | — | — / — | **Sin documento comparable** |
| MVJER | — | — | — | — | — / — | **Sin documento comparable** |
| MULTIEQ | — | — | — | — | — / — | **Sin documento comparable** |

- **MULTIRE**: No se localizo cartera mensual ni DICI de ago-oct 2026 en multiva.com.mx (los URLs de /documents/32731/... llevan ids no deducibles; la busqueda solo devolvio DICI de feb-2026, p.ej. 202602_MULTIRE.pdf, fuera de los meses del portal). Sin comparacion.
- **MVJER**: No se localizo cartera mensual ni DICI de ago-oct 2026 en multiva.com.mx (los URLs de /documents/32731/... llevan ids no deducibles; la busqueda solo devolvio DICI de feb-2026, p.ej. 202602_MULTIRE.pdf, fuera de los meses del portal). Sin comparacion.
- **MULTIEQ**: No se localizo cartera mensual ni DICI de ago-oct 2026 en multiva.com.mx (los URLs de /documents/32731/... llevan ids no deducibles; la busqueda solo devolvio DICI de feb-2026, p.ej. 202602_MULTIRE.pdf, fuera de los meses del portal). Sin comparacion.
- **Notas**: Sin documento comparable; portal dice casa_de_bolsa_hermana=true (no verificado).

### Compass Investments (`compass`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| I+LIQG | cartera mensual | 2026-10-30 | — | [latam.vincicompass.com](https://latam.vincicompass.com/wp-content/uploads/mexico/Fondos/Fondos%20de%20Deuda/I+LIQG/CARTERA%20MENSUAL/COMPASSI+LIQGPublicaciones20261030.pdf) |
| I+LIQG | otro | 2026-10-30 | — | [latam.vincicompass.com](https://latam.vincicompass.com/wp-content/uploads/mexico/Fact%20Sheets/I+LIQ/FS%20I+LIQ%20COMPASS%20Octubre%202026_Mexico.pdf) |
| STRAT | cartera mensual | 2026-10-30 | — | [latam.vincicompass.com](https://latam.vincicompass.com/wp-content/uploads/mexico/Fondos/Fondos%20Renta%20Variable/STRAT/CARTERA%20MENSUAL/COMPASSSTRATPublicaciones20261030.pdf) |
| AMVALOR | cartera mensual | 2026-10-30 | — | [latam.vincicompass.com](https://latam.vincicompass.com/wp-content/uploads/mexico/Fondos/Fondos%20Renta%20Variable/AMVALOR/CARTERA%20MENSUAL/COMPASSAMVALORPublicaciones20261030.pdf) |
| AMVALOR | otro | 2026-09-01 | 2026-08-19 | [latam.vincicompass.com](https://latam.vincicompass.com/wp-content/uploads/mexico/Fondos/Fondos%20Renta%20Variable/AMVALOR/AVISOS%20RELEVANTES/Aviso%20P%C3%BAblico%20-%20Cambio%20Comisiones%20y%20M%20M%C3%ADnimos%20-%20Sep%202026.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| I+LIQG | 9,194.6 | 9,194.6 | +0.0 % | 5 de 5 (BONDESF 280224 9.60, BONDESF 270422 7.60, BPAG28 290503 7.60, BONDESF 270520 7.48, BONDESF 270114 6.54; % identicos) | Gubernamental 94.7% / Cash 5.3% (fact sheet); cartera: directo 94.11%, reporto 5.34%, otros valores 0.55% / RF 94.1 / EFE 5.9 | **Coincide** |
| STRAT | 2,340.3 | 2,340.3 | +0.0 % | 5 de 5 (SHV 14.53, NVDA 5.39, TSM 5.08, GOOG 4.79, BNY 4.40; % identicos) | Acciones SIC ~70.4% + SHV 14.53% (tracks) + otros valores 0.57%; el documento no clasifica RV/RF / RV 84.9 / RF 14.5 / EFE 0.6 | **Coincide** |
| AMVALOR | 1,798.4 | 1,798.4 | +0.0 % | 5 de 5 (PINFRA L 20.06, GMEXICO B 7.58, ORBIA 6.28, ASUR B 5.72, GFNORTE O 5.70; % identicos) | Directo 98.21% + otros valores 1.79% (todo RV) / RV 98.2 / EFE 1.8 | **Coincide** |

- **I+LIQG**: Coincidencia exacta con el corte de oct-2026 de la operadora. OJO: el portal usa esta misma fuente (cartera mensual de la operadora), por lo que no es una verificacion independiente; solo confirma que la carga es fiel. El fact sheet da AUM 9,195 MXN M. No se comparo el corte 2026-09-30 (el archivo de sept. no se localizo). Comisiones/régimen: No verificado: el DICI de oct-2026 aparece enlazado en la pagina del fondo pero el servidor lo redirige (302) al sitio corporativo..
- **STRAT**: Coincide con el corte oct-2026; misma fuente que el portal (no independiente). SHV (iShares Short Treasury) clasificado por el portal como RF. Comisiones/régimen: No verificado (DICI no accesible, 302)..
- **AMVALOR**: Cartera coincide (misma fuente). Revisar el regimen rv_max=0 del portal para AMVALOR. Comisiones/régimen: Aviso de 19-ago-2026: cambian comisiones de administracion/distribucion y minimos desde 1-sep-2026, pero las tablas son imagen (no legibles) y no se pudieron comparar con las series del portal. ALERTA: el portal muestra regimen rv_min=0 / rv_max=0 para AMVALOR, incoherente con un fondo de renta variable con 98% RV; probable error de extraccion del DICI en el portal (no confirmado con el DICI oficial, inaccesible).. **Corregido el 2026-11-20:** el régimen venía del prospecto de I+CORP; ahora RV 1 %–100 %.
- **Notas**: Cartera mensual de oct-2026 de los 3 fondos coincide con el portal (fuente identica). Los DICI de oct-2026 (DICI_<fondo>_1026.pdf) estan listados en las paginas de los fondos pero devuelven 302 a la portada, asi que regimen/comisiones/distribuidoras no se verificaron. Portal: casa_de_bolsa_hermana=false; sin evidencia documental nueva.

### BBVA Asset Management (`bbva`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| BBVALIQ | otro | 2026-10-30 | 2026-11-05 | [portal.bbva.mx](https://portal.bbva.mx/siabinternet/Repositorio/import/doctos/analisis/00016362.pdf) |
| BBVAGOB | otro | 2026-10-30 | 2026-11-05 | [portal.bbva.mx](https://portal.bbva.mx/siabinternet/Repositorio/import/doctos/analisis/00016398.pdf) |
| BBVAUS | otro | 2026-10-30 | 2026-11-05 | [portal.bbva.mx](https://portal.bbva.mx/siabinternet/Repositorio/import/doctos/analisis/00016380.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| BBVALIQ | 424,809.4 | 426,970.5 | -0.5 % | No evaluable: la ficha tecnica no trae top 10 de este fondo | Gubernamentales 50% + Bancarios 26% + Papel privado 3% = RF 79; Efectivo 14% + Reporto 6% = 20 (redondeo) / RF 76.1 / EFE 23.9 | **Diferencia menor** |
| BBVAGOB | 199,994.8 | 197,261.8 | +1.4 % | No evaluable: ficha sin top 10 | Valores gubernamentales 84% / Reporto 16% / RF 90.0 / EFE 10.0 | **Diferencia menor** |
| BBVAUS | 11,881.0 | 11,411.2 | +4.1 % | 5 de 5 (NVDA 8.4 vs 9.13; AAPL 6.5 vs 6.23; MSFT 5.4 vs 5.17; GOOGL 5.2 vs 6.16; AMZN 5.1 vs 5.11); top10 documento = 44.7% | Efectivo 0.2%; resto renta variable EE.UU. / RV 99.9 / RF 0.1 / EFE 0.0 | **Diferencia menor** |

- **BBVALIQ**: Ficha tecnica (activos netos 424,809.44 mdp, calculos al 30/10/2026) vs cartera R7 de sept: dif -0.51%, cortes distintos (oct vs sep). Mezcla coherente (RF ~79 vs 76; EFE ~20 vs 24). No se hallo DICI/cartera mensual de ago-sep 2026. Comisiones/régimen: No aplica (ficha sin regimen/comisiones; portal sin DICI).
- **BBVAGOB**: Ficha tecnica oct vs portal sep: dif +1.39% en activos. La mezcla difiere ~6 pts (reporto 16% vs EFE 10% del portal), posible efecto de cambio de mes o de clasificacion del portal (BONDESF como RF vs reporto). No se comparo con ago-31 porque no hay documento de ese mes. Comisiones/régimen: No aplica.
- **BBVAUS**: Mismas 5 emisoras; % dentro de ~1 punto salvo GOOGL (-1.0). Activos +4.1% (oct vs sep). El texto del PDF viene desordenado; el emparejamiento ticker-% sigue el orden de la lista de la ficha (NVDA, AAPL, MSFT, GOOGL, AMZN, MA, AVGO, WFC, META, NEE). Comisiones/régimen: No aplica.
- **Notas**: Las fichas de BBVA no listan distribuidoras. No se hallo DICI con 'Principales inversiones' de ago-oct 2026 (los DICI indexados son de dic-2025). Portal: casa_de_bolsa_hermana=true (Casa de Bolsa BBVA Mexico, Grupo Financiero BBVA Mexico), sin contradiccion.

### Operadora de Fondos Banorte (`banorte`)

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| NTECT | — | — | — | — | — / — | **Sin documento comparable** |
| NTEGUB | — | — | — | — | — / — | **Sin documento comparable** |
| NTEUSA+ | — | — | — | — | — / — | **Sin documento comparable** |

- **NTECT**: banorte.com no respondio desde este entorno (timeouts por curl y WebFetch). Existen PDFs mensuales publicos (p.ej. NTEGUB: https://www.banorte.com/dam/jcr:f1b607cf-7f30-46d3-8827-92f9da81ff07/NTEGUB_MENSUAL.pdf, fecha no verificada) pero no se pudieron leer. No hay comparacion.
- **NTEGUB**: banorte.com no respondio desde este entorno (timeouts por curl y WebFetch). Existen PDFs mensuales publicos (p.ej. NTEGUB: https://www.banorte.com/dam/jcr:f1b607cf-7f30-46d3-8827-92f9da81ff07/NTEGUB_MENSUAL.pdf, fecha no verificada) pero no se pudieron leer. No hay comparacion.
- **NTEUSA+**: banorte.com no respondio desde este entorno (timeouts por curl y WebFetch). Existen PDFs mensuales publicos (p.ej. NTEGUB: https://www.banorte.com/dam/jcr:f1b607cf-7f30-46d3-8827-92f9da81ff07/NTEGUB_MENSUAL.pdf, fecha no verificada) pero no se pudieron leer. No hay comparacion.
- **Notas**: Sin documento leido. Dato indirecto sin verificar (snippet de busqueda): el NTE1 al 30-sep-2026 tiene NTEUSA+ a 1.58%. Portal: casa_de_bolsa_hermana=true (Casa de Bolsa Banorte, GF Banorte), sin contradiccion documental.

### Santander Asset Management (`santander`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| USA-EQ | DICI | 2025-12-31 | 2026-01-06 | [www.citigroup.com](https://www.citigroup.com/rcs/citigpa/storage/public/Mexico/USA-EQ_DocumentoClaveActualizacionAnual.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| STERGOB | — | — | — | — | — / — | **Sin documento comparable** |
| FONSER1 | — | — | — | — | — / — | **Sin documento comparable** |
| USA-EQ | — | — | — | — | — / — | **Sin documento comparable** |

- **STERGOB**: santander.com.mx (/PDF/Fondos/Carteras/CM_STERGOB.pdf y DICI D_STERGOB.pdf) devuelve 403 (bloqueo anti-bot); no se evadio. Sin documento.
- **FONSER1**: santander.com.mx devuelve 403 para CM_FONSER1.pdf y D_FONSER1.pdf. Sin documento.
- **USA-EQ**: El unico DICI accesible (alojado en citigroup.com) trae 'Principales inversiones al 31-dic-2025': NVDA 10.78, TSLA 8.16, META 7.17, AMZN 5.69, NFLX 5.29; cartera 6,975,879 (miles de pesos presumibles). Esta a 8 meses del portal, no comparable. Regimen del DICI: RV EE.UU. 1%-100%, RV fuera de EE.UU. 0-25%, deuda 0-99%, VaR max 6.5%; comision administracion serie B1 2.66% anual. El de ago-2026 existe (segun busqueda) pero esta en santander.com.mx (403).
- **Casa de bolsa hermana**: El DICI de USA-EQ (dic-2025) lista como distribuidoras a Casa de Bolsa Santander, Banco Santander Mexico, Banco Actinver, Actinver Casa de Bolsa, CitiBanamex Casa de Bolsa, Intercam Fondos, Kuspit, Mas Fondos y Monex Casa de Bolsa. IMPORTANTE: el mismo DICI declara que SAM Asset Management NO es integrante de Grupo Financiero Santander Mexico (subsidiaria de Santander Asset Management UK Holdings, usa la marca bajo licencia).
- **Notas**: Hallazgo relevante: el portal marca casa_de_bolsa_hermana=true ('Casa de Bolsa Santander pertenece a Santander'), pero el DICI aclara que la operadora no es parte del Grupo Financiero; Casa de Bolsa Santander es distribuidora afiliada al banco, no hermana de grupo formal. Revisar el criterio.

### Scotia Fondos (`scotia`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| SCOTIA1 | DICI | 2026-10-31 | — | [cdn.aglty.io](https://cdn.aglty.io/scotia-bank-mexico/spanish/pdf/personas/fondos-de-inversion/dici/DICI_SCOTIA1.pdf) |
| SBANKCP | DICI | 2026-10-31 | — | [cdn.aglty.io](https://cdn.aglty.io/scotia-bank-mexico/spanish/pdf/personas/fondos-de-inversion/dici/DICI_SBANKCP.pdf) |
| SCOTUSA | DICI | 2026-10-31 | — | [cdn.aglty.io](https://cdn.aglty.io/scotia-bank-mexico/spanish/pdf/personas/fondos-de-inversion/dici/DICI_SCOTUSA.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| SCOTIA1 | 48,296.1 | 46,896.1 | +3.0 % | 3 de 5 (CHEQUERA 40-044 4747974 8.25 vs 8.46; CETES 271028 4.35 vs 4.44; CETES 270318 3.13 vs 3.82; BONDESF 290719 reporto 9.61 solo en top10 de ago: 10.61) | No desglosado en el DICI; top10: reporto 9.61, chequera 8.25, resto deuda / RF 61.6 / EFE 38.4 | **Diferencia menor** |
| SBANKCP | 45,199.0 | 45,616.9 | -0.9 % | 3 de 5 (CHEQUERA 40-044 4747857 10.30 vs 10.15; BPA182 310327 4.75 vs 7.41; CETES 271028 4.03 vs 3.95) | No desglosado; top10 incluye chequera 10.30 y reporto 3.80 / RF 58.5 / EFE 41.5 | **Diferencia menor** |
| SCOTUSA | 22,205.1 | 22,397.5 | -0.9 % | 5 de 5 (NVDA 10.83 vs 11.57; GOOG 9.57 vs 11.67; AAPL 8.92 vs 8.60; MSFT 8.51 vs 8.01; KLAC 5.18 vs 6.12) | Renta variable (top10 todo RV); sin desglose / RV 99.8 / RF 0.2 / EFE 0.0 | **Diferencia menor** |

- **SCOTIA1**: DICI con principales inversiones a octubre-2026 comparado con el corte mas cercano (30-sep). Total +2.99%; las posiciones grandes persisten (chequera 40-044), la rotacion de CETES/BONDESF es normal mes a mes. Comisiones/régimen: Regimen DICI: pesos 80-100%, reporto 0-100%, ETFs 0-20%; comision administracion serie C1E 2.10% (total 2.12%). El portal no trae DICI para este fondo..
- **SBANKCP**: Corte octubre vs septiembre: total -0.92%. BPA182 310327 baja de 7.41% a 4.75%. Comisiones/régimen: Comision administracion serie C1E 2.20% (total 2.22%); portal sin DICI..
- **SCOTUSA**: Mismas 5 emisoras; GOOG difiere 2.1 pts (oct vs sep). Total -0.86%. Comisiones/régimen: Comision administracion serie C1E 2.50% (total 2.52%); VaR 4.60%; asesor 1832 Asset Management L.P..
- **Casa de bolsa hermana**: Los tres DICI (oct-2026) listan como distribuidoras a Scotiabank Inverlat (Banco) y Scotia Inverlat Casa de Bolsa, S.A. de C.V., Grupo Financiero Scotiabank Inverlat (mismo grupo que la operadora: confirma casa_de_bolsa_hermana=true). Tambien listan Actinver CB, Citi Mexico CB, Ve por Mas CB, Base CB, Kuspit, Finamex, Mifel, Punto Casa de Bolsa y Operadora Actinver, entre otras.
- **Notas**: Los DICI de Scotia (cdn.aglty.io) se descargaron y traen 'Principales inversiones al mes de octubre 2026'; el portal solo tiene ago y sep para Scotia, asi que se uso el corte 30-sep como mas cercano. No hay documentos de ago/sep.

### HSBC Global Asset Management (`hsbc`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| HSBC-D2 | cartera mensual | 2026-10-30 | — | [www.assetmanagement.hsbc.com.mx](https://www.assetmanagement.hsbc.com.mx/-/media/Files/attachments/mexico/fund-center/portfolios/hsbc-d2-cartera.pdf) |
| HSBCDC+ | cartera mensual | 2026-10-30 | — | [www.assetmanagement.hsbc.com.mx](https://www.assetmanagement.hsbc.com.mx/-/media/Files/attachments/mexico/fund-center/portfolios/hsbcdcplus-cartera.pdf) |
| HSBCMEX | cartera mensual | 2026-03-05 | — | [www.assetmanagement.hsbc.com.mx](https://www.assetmanagement.hsbc.com.mx/-/media/Files/attachments/mexico/fund-center/portfolios/hsbcmex-cartera.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| HSBC-D2 | 175,440.0 | 177,158.5 | -1.0 % | 3 de 5 | RV 0; directo (BONDESF, CETES, CB, CD) 80.86%; reporto 6.01%; otros valores 13.13% / RF 84.4 / EFE 15.6 (30-sep) | **Diferencia menor** |
| HSBCDC+ | 49,447.0 | 50,660.5 | -2.4 % | 4 de 5 | RV 0; directo 79.48%; reporto 10.85%; otros valores 9.67% / RF 91.3 / EFE 8.7 (30-sep) | **Diferencia menor** |
| HSBCMEX | 2,643.0 | 2,934.1 | — | 5 de 5 (indicativo) | RV 94.77% directo; otros valores 5.23% / RV 98.9 / EFE 1.1 (31-ago) | **Sin documento comparable** |

- **HSBC-D2**: Total derivado de 141,859.64 mdp / 80.86% (el PDF no imprime el total). Series coincidentes con % dentro de 1 pt: CETES 270121 (3.23 vs 3.18), CETES 270218 (3.22 vs 3.17), BONDESF 270520 (3.15 vs 3.12). Las 2 que no estan (CETES 271028, BONDESF 271014 reporto) son series nuevas de octubre. Documento de otro mes que el portal. Comisiones/régimen: No aplica (cartera, no DICI).
- **HSBCDC+**: Total derivado de 39,300.10 mdp / 79.48%. Las 4 posiciones presentes son CETES 270204 (8.61 vs 8.35), 270318 (8.26 vs 9.06), 270304 (4.55 vs 8.63), 270915 (3.52 vs 2.3); solo 2 dentro de 1 pt por rotacion de un mes. BPA182 280412 (reporto) no esta en el top10 del portal. Contra el corte del 31-ago del portal (49,351) la diferencia es +0.2%. Comisiones/régimen: No aplica (cartera).
- **HSBCMEX**: El PDF vigente del sitio es del 5-mar-2026 (su encabezado dice HSBC-V2). Seis meses de diferencia; solo es referencia: GMEXICO 15.56, GFNORTE 9.39, AMX 7.70, FEMSA 7.38, CEMEX 7.02 vs portal 15.1-15.3, 10.6-11.8, 6.9-7.4, 7.2-7.5, 6.3-6.9. No se calculo diferencia de total. Comisiones/régimen: No aplica.
- **Notas**: Los PDF de cartera de HSBC no listan distribuidoras. Tambien se descargo hsbcpra (HSBC-E2, 30-oct), fuera de la muestra: tiene HSBCMEX, HSBCDC+ y HSBC-D2 como fondos de fondos (6.40/11.89/10.24%). No se hallo DICI de agosto/septiembre.

### Operadora Inbursa (`inbursa`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| IBUPLUS | DICI | 2026-10-31 | — | [www.inbursa.com](https://www.inbursa.com/sites/gfi/document/ibuplus-infoclave.pdf) |
| IBUPLUS | cartera mensual | — | — | [www.inbursa.com](https://www.inbursa.com/sites/gfi/document/ibuplus-cartera.pdf) |
| INBUMAX | DICI | 2026-10-31 | — | [www.inbursa.com](https://www.inbursa.com/sites/gfi/document/inbumax-infoclave.pdf) |
| INBUMAX | cartera mensual | — | — | [www.inbursa.com](https://www.inbursa.com/sites/gfi/document/inbumax-cartera.pdf) |
| INBURSA | DICI | 2026-10-31 | — | [www.inbursa.com](https://www.inbursa.com/sites/gfi/document/inbursa-infoclave.pdf) |
| INBURSA | cartera mensual | — | — | [www.inbursa.com](https://www.inbursa.com/sites/gfi/document/inbursa-cartera.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| IBUPLUS | 76,568.9 | 74,139.4 | +3.3 % | 5 de 5 | Acciones industriales 66.2% + SHV (ETF) 4.6% + otras RV; reportos 0.10% (cartera 76,355 mdp, AN 76,167) / RV 74.5 / RF 25.1 / EFE 0.4 (30-sep) | **Diferencia menor** |
| INBUMAX | 31,399.3 | 31,117.5 | +0.9 % | 4 de 5 con serie (CETES 270204, 280803, 270218, 270819); BONDESF y BANOBRA aparecen agregados | Reportos 10.49%; CETES 37.7%; pagares con rendimiento liquidable 32.3%; certificados bursatiles ~10% / RF 87.6 / EFE 12.4 (30-sep) | **Coincide** |
| INBURSA | 20,744.8 | 20,200.4 | +2.7 % | 5 de 5 | Acciones industriales 68.6%; reportos 0.34% (cartera 20,702 mdp) / RV 83.2 / RF 14.2 / EFE 2.6 (30-sep) | **Diferencia menor** |

- **IBUPLUS**: DICI Principales inversiones al mes de octubre 2026: AMX 11.92 (portal sep 10.26), GFINBUR 9.90 (9.19), GCARSO 8.40 (7.32), MFRISCO 6.90 (7.46), LASITE 5.38 (6.32); 3 de 5 dentro de 1 pt. Contra 31-ago del portal (76,055.5) el total difiere +0.7%. El PDF de cartera no trae fecha explicita; su total (76,355) esta entre agosto y octubre. Comisiones/régimen: Serie BF-1: admin. activos 0.825%+IVA, distribucion 0.675%+IVA, total 1.5%+IVA; sin comision por compra/venta de la operadora.
- **INBUMAX**: CETES 270204 10.16 vs 10.19, 280803 4.73 vs 4.58, 270218 4.06 vs 4.07, 270819 3.92 vs 3.92: todos dentro de 1 pt. Reportos del documento (10.5%) ~ EFE del portal (12.4%). Comisiones/régimen: Serie BF-1: total 1% + IVA (DICI).
- **INBURSA**: DICI octubre: AMX 10.22 (portal sep 8.74), GFINBUR 9.78 (9.25), GCARSO 8.81 (7.63), FCC 6.79 (7.12), MFRISCO 6.73 (7.23); 3 de 5 dentro de 1 pt. Contra 31-ago (21,214.8) la diferencia es -2.2%. Comisiones/régimen: Ver DICI (serie B-1); tabla no extraida.
- **Casa de bolsa hermana**: Los DICI listan como distribuidora a Inversora Bursatil, S.A. de C.V., Casa de Bolsa, Grupo Financiero Inbursa (mismo grupo que la operadora): confirma casa_de_bolsa_hermana.
- **Notas**: Los PDF salen de www.inbursa.com/sites/gfi/document/ (autoexpressinbursa.com redirige). Los PDF de cartera no traen fecha; los DICI son de octubre 2026. No se hallaron DICI ni cartera de agosto o septiembre.

### Operadora GBM (`gbm`)

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| GBM106 | — | — | — | — | — / — | **Sin documento comparable** |
| MPAGORF | — | — | — | — | — / — | **Sin documento comparable** |
| NUMC | — | — | — | — | — / — | **Sin documento comparable** |

- **GBM106**: Sin documento: gbm.com devuelve 403 al fetch y las paginas de detalle para esta clave dan 404; Monex solo publica carteras de sus propios fondos y de algunos que distribuye (no GBM106/NUMC/MPAGORF). No se localizo DICI ni cartera.
- **MPAGORF**: Sin documento: gbm.com devuelve 403 al fetch y las paginas de detalle para esta clave dan 404; Monex solo publica carteras de sus propios fondos y de algunos que distribuye (no GBM106/NUMC/MPAGORF). No se localizo DICI ni cartera.
- **NUMC**: Sin documento: gbm.com devuelve 403 al fetch y las paginas de detalle para esta clave dan 404; Monex solo publica carteras de sus propios fondos y de algunos que distribuye (no GBM106/NUMC/MPAGORF). No se localizo DICI ni cartera.
- **Notas**: Sin documento oficial localizado para los tres fondos. Se revisaron carteras mensuales de Monex de sep-2026 pero no incluyen fondos GBM de la muestra.

### Operadora Actinver (`actinver`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| ACTIGOB | cartera mensual | 2026-08-06 | — | [actinver.com](https://actinver.com/documents/d/actinver/cartera-semanal-actigob) |
| ACTIGOB | cartera mensual | 2026-10-30 | — | [actinver.com](https://actinver.com/documents/d/actinver/cartera-mensual-actigob) |
| ACTIMED | cartera mensual | 2026-08-06 | — | [actinver.com](https://actinver.com/documents/d/actinver/cartera-semanal-actimed) |
| ACTIMED | cartera mensual | 2026-10-30 | — | [actinver.com](https://actinver.com/documents/d/actinver/cartera-mensual-actimed) |
| ACTIOP1 | cartera mensual | 2026-08-06 | — | [actinver.com](https://actinver.com/documents/d/actinver/cartera-semanal-actiop1) |
| ACTIOP1 | cartera mensual | 2026-10-30 | — | [actinver.com](https://actinver.com/documents/d/actinver/cartera-mensual-actiop1) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| ACTIGOB | 97,982.0 | 98,131.6 | -0.1 % | 3 de 5 (6-ago vs 31-ago); 3 de 5 (30-oct vs 30-sep) | 6-ago: reportos 43.25%; 30-oct: reportos 40.05%, CETES 35.75%, udibonos 8.57% / 31-ago EFE 37.8; 30-sep EFE 40.5 / RF 59.5 | **Diferencia menor** |
| ACTIMED | 80,858.9 | 80,822.1 | +0.1 % | 5 de 5 en ambas comparaciones, todas dentro de 1 pt | 6-ago: reportos 4.94%; 30-oct: reportos 3.74% / 31-ago RF 97.1 / EFE 2.9; 30-sep RF 97.0 / EFE 3.0 | **Coincide** |
| ACTIOP1 | 11,760.0 | 11,995.2 | -2.0 % | 5 de 5 (ambos); 3 de 5 dentro de 1 pt (6-ago), 4 de 5 (30-oct) | 6-ago: RV 93.2% (GMEXICO 41.1, SIC 43.5, FIBRA 8.6), reportos 6.66%; 30-oct: RV 93.2%, reportos 6.65% / 31-ago RV 93.1 / EFE 6.9; 30-sep RV 93.4 / EFE 6.6 | **Coincide** |

- **ACTIGOB**: Doc 6-ago: AN 98,175.1 vs portal AN 31-ago 98,051.3 (+0.13%). Doc 30-oct: total 98,106.5 vs portal 30-sep 100,754.8 (-2.6%). CETES 280217 6.32 vs 6.35 y CETES 270401 4.40 vs 4.41; UDIBONO 261203 7.00 (6-ago) vs 8.35 (31-ago). Fechas distintas. Comisiones/régimen: No aplica.
- **ACTIMED**: Doc 6-ago AN 81,289.9 vs portal AN 80,677.7 (+0.76%). Doc 30-oct total 81,224.7 vs portal 30-sep 80,652.5 (+0.71%). BONDESF 280518 6.19 vs 6.19, BONDESG 290726 4.93 vs 4.93. Comisiones/régimen: No aplica.
- **ACTIOP1**: Mezcla coincide. Doc 30-oct total 12,368.0 vs portal 30-sep 12,668.7 (-2.4%). GMEXICO 40.11 vs 39.51, META 18.70 vs 20.70, MSFT 11.11 vs 10.25. Comisiones/régimen: No aplica.
- **Notas**: Los PDF de cartera semanal (6-ago) y mensual (30-oct) estan en actinver.com/documents/d/actinver/cartera-semanal o cartera-mensual seguido de la clave. No traen distribuidoras. No se obtuvo DICI.

### Operadora Valmex (`valmex`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| VXGUBCP | otro | 2026-09-30 | — | [operadoravalmex.mx](https://operadoravalmex.mx/wp-content/uploads/2021/05/VXGUBCP-5.pdf) |
| VLMXTEC | otro | 2026-10-31 | — | [operadoravalmex.mx](https://operadoravalmex.mx/wp-content/uploads/2021/10/VLMXTEC-A-OCT-1.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| VXGUBCP | 13,542.0 | 13,169.1 | +2.8 % | n/d (la ficha no lista posiciones) | CETES, BPAs y BONDES 85.7% / reporto 14.3% (posicion al 30/09/2026) / RF 85.7 / EFE 14.3 | **Coincide** |
| VLMXTEC | 6,738.0 | 6,925.9 | -2.7 % | 5 de 5 (nombres; la ficha no da porcentajes en texto) | No detalla; 71 emisoras, EUA 86.8% / RV 97.9 / EFE 2.1 | **Diferencia menor** |
| VLMXLPE | — | — | — | — | — / — | **Sin documento comparable** |

- **VXGUBCP**: La mezcla es identica a la del portal en la misma fecha. Los activos netos (13,542 mdp) son de la ficha con datos al 31-oct, no comparables en fecha con el corte del 30-sep (+2.8%). Comisiones/régimen: No aplica (ficha).
- **VLMXTEC**: Top 10 de la ficha (oct): NVIDIA, CROWDSTRIKE, META, PALO ALTO, BROADCOM, TESLA, SALESFORCE, SHOPIFY, MICROSOFT, SNOWFLAKE; el portal (sep) tiene NVDA, META, CRWD, PANW, AVGO en sus primeras 5. Activos netos 6,738 mdp (oct) vs total portal 6,925.9 (sep). Comisiones/régimen: No aplica (ficha).
- **VLMXLPE**: No se encontro DICI ni cartera al alcance; la pagina operadoravalmex.mx/fondos-de-inversion/<clave>/cartera-mensual se carga por JS.
- **Casa de bolsa hermana**: La ficha de VLMXTEC lista como custodio a Valores Mexicanos Casa de Bolsa, S.A. de C.V. (mismo grupo Valmex); es custodio, no se confirmo como distribuidora.
- **Notas**: Fuente: operadoravalmex.mx. Las fichas son material informativo de Valmex/Morningstar, no DICI ni cartera CNBV.

### Operadora Finamex (`finamex`)

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| AM2 | — | — | — | — | — / — | **Sin documento comparable** |
| FMXPRE | — | — | — | — | — / — | **Sin documento comparable** |
| FMXSIC | — | — | — | — | — / — | **Sin documento comparable** |

- **AM2**: Sin documento: finamex.com.mx/general/fondos solo describe la distribucion de fondos de terceros y /fondos-de-inversion devuelve 500. Busquedas no devolvieron DICI ni cartera para esta clave.
- **FMXPRE**: Sin documento: finamex.com.mx/general/fondos solo describe la distribucion de fondos de terceros y /fondos-de-inversion devuelve 500. Busquedas no devolvieron DICI ni cartera para esta clave.
- **FMXSIC**: Sin documento: finamex.com.mx/general/fondos solo describe la distribucion de fondos de terceros y /fondos-de-inversion devuelve 500. Busquedas no devolvieron DICI ni cartera para esta clave.
- **Notas**: Sin documento oficial localizado. El sitio indica que Finamex Casa de Bolsa ofrece mas de 50 fondos de distintas instituciones.

### Operadora INVEX (`invex`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| INVEXGU | DICI | 2026-10-30 | — | [invex.com](https://invex.com/documentos/invexgu-dici) |
| INVEXGU | cartera mensual | 2026-10-30 | 2026-11-03 | [invex.com](https://invex.com/documentos/invexgu-informe-mensual) |
| INVEXMP | DICI | 2026-10-30 | — | [invex.com](https://invex.com/documentos/invexmp-dici) |
| INVEXMP | cartera mensual | 2026-10-30 | 2026-11-03 | [invex.com](https://invex.com/documentos/invexmp-informe-mensual) |
| INVEXTK | DICI | 2026-10-30 | — | [invex.com](https://invex.com/documentos/invextk-dici) |
| INVEXTK | cartera mensual | 2026-10-30 | 2026-11-03 | [invex.com](https://invex.com/documentos/invextk-informe-mensual) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| INVEXGU | 22,410.8 | 19,673.4 | +13.9 % | 5 de 5; 2 de 5 dentro de 1 pt | Reportos 8.27% + chequera 12.58% = ~20.9%; BONDESF directo ~70% / RF 78.0 / EFE 22.0 (30-sep) | **Diferencia relevante** |
| INVEXMP | 5,366.6 | 5,387.7 | -0.4 % | 5 de 5; 4 de 5 dentro de 1 pt | Chequera 4.76% mas reportos; resto deuda / RF 93.7 / EFE 6.3 (30-sep) | **Coincide** |
| INVEXTK | 724.9 | 753.1 | -3.7 % | 5 de 5; 4 de 5 dentro de 1 pt | Chequera 5.67%; resto acciones SIC / 30-sep RV 92.7 / EFE 7.3 | **Diferencia menor** |

- **INVEXGU**: Total 30-oct 22,410.8 vs portal 30-sep 19,673.4 (+13.9%) y vs 31-ago 18,024.9 (+24%); puede ser flujo de octubre, no error. Series: CHM 12.58 vs 12.28, BONDESF 270225 7.83 vs 8.92, 261231 7.67 vs 8.73, 261203 7.15 vs 7.13, 270819 6.71 vs 5.09. Comisiones/régimen: DICI: total 0.78% (BE1) / 1.53%.
- **INVEXMP**: CETES 280608 8.74 vs 8.16, BINVEX 25-2 4.67 vs 4.65, F BINVEX 26025 3.73 vs 3.72, BINVEX 26 3.34 vs 3.33; solo la chequera difiere (4.76 vs 6.28). Comisiones/régimen: DICI: total 1.01% / 1.21%.
- **INVEXTK**: Total 30-oct 724.93 vs portal 31-ago 724.79 (+0.02%) y 30-sep 753.07 (-3.7%). NVDA 7.73 vs 8.12, MSFT 7.11 vs 6.53, AMZN 5.17 vs 4.90, CHM 5.67 vs 7.26. Comisiones/régimen: DICI: total 1.57% / 2.07%.
- **Casa de bolsa hermana**: Los DICI listan a INVEX Casa de Bolsa, S.A. de C.V., INVEX Grupo Financiero como distribuidora (mismo grupo que la operadora); INVEXMP lista ademas a Sociedad Distribuidora Integral de Acciones.
- **Notas**: Los PDF salen de invex.com/documentos/<clave>-dici o -informe-mensual (redirige al CDN invex.cdn.modyo.com). Informe mensual con composicion al 30/10/2026.

### Monex Operadora (`monex`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| MONEXCP | DICI | 2026-09-30 | 2026-10-02 | [www.monex.com.mx](https://www.monex.com.mx/portal/download/fondos2/DICI%20MONEXCP%200926.pdf) |
| MONEXM+ | DICI | 2026-09-30 | 2026-10-02 | [www.monex.com.mx](https://www.monex.com.mx/portal/download/fondos2/DICI%20MONEXMmas%200926.pdf) |
| MONXESG | DICI | 2026-09-30 | 2026-10-02 | [www.monex.com.mx](https://www.monex.com.mx/portal/download/fondos2/DICI%20MONXESG%200926.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| MONEXCP | 22,624.0 | 22,624.0 | +0.0 % | 4 de 4 renglones del DICI consistentes (el DICI agrupa por emisora/tipo y solo trae 4 renglones); BPAG91 reporto 15.3% en doc vs 11.24%+3.35%+resto en series BPAG91 del portal | Gobierno 100% (deuda); reportos BPAG91 15.3% / RF 84.7 / EFE 15.3 (EFE=reportos) - coincide | **Coincide** |
| MONEXM+ | 16,414.9 | 16,414.9 | +0.0 % | 5 de 5 por emisora/tipo (BONDESF, BPAG28, BPAG91 reporto, BPAG91 gob, BONDESF reporto); BPAG91 reporto 9.1% doc vs 9.14% portal (BPAG91 280106) | Gobierno 76.1%, Bancos 12.3%, Serv. financieros 8.4%; reportos 14.3% (9.1+5.2) / RF 85.7 / EFE 14.3 - EFE coincide con reportos del DICI (14.3%) | **Coincide** |
| MONXESG | 78.7 | 78.7 | +0.0 % | 5 de 5 (ESGU 51.0, ESGD 19.0, ESGE 11.5, EFIV 6.7, SHV 4.7 vs portal 51.02/19.04/11.49/6.73/4.67) | ETFs 'Renta Variable' ~100% por tipo en DICI; ETFs de tesoreria SHV 4.7% + BB3M 3.7% = 8.4% / RV 91.3 / RF 8.4 / EFE 0.3 - el 8.4% RF corresponde a SHV+BB3M | **Coincide** |

- **MONEXCP**: Total de cartera 22,624,003 miles identico al portal. El DICI agrupa por emisora (BONDESF 52.6%, BPAG28 18.9%, BPAG91 reporto 15.3%, BPAG91 gobierno 13.2%); el portal lista por serie, por eso los % individuales no son comparables 1 a 1, pero las sumas son consistentes con el 15.3% de reportos/EFE. Comisiones/régimen: Serie BFC-1: admin activos 0.54% + distribucion 1.27% = 1.84% anual pagado por el fondo; cliente 0%.
- **MONEXM+**: Total identico. DICI agrupa por emisora (BONDESF 38.1%, BPAG28 15.2%) vs portal por serie. Distribuidoras: Monex Casa de Bolsa (mismo grupo Monex), O'Rourke & Asociados, Kuspit Casa de Bolsa. Hay otras series (BFC-2 etc.) en el mismo PDF (22 pags). Comisiones/régimen: Serie BFC-1: admin 0.23% + distribucion 0.55% = 0.81% anual pagado por el fondo; cliente N/A.
- **MONXESG**: Total y top 5 coinciden (miles de pesos 78,747). El DICI clasifica SHV/BB3M como renta variable por ser ETFs; el portal los pone en RF (criterio razonable por subyacente). Comisiones/régimen: Serie BFC-1: cliente 1.00% (compra 0.50% + otros); fondo: admin 0.41% + distribucion 0.94% = 1.62%.
- **Casa de bolsa hermana**: Si: los tres DICI listan a Monex Casa de Bolsa (Monex Grupo Financiero, mismo grupo de la operadora) como distribuidora, ademas de O'Rourke & Asociados y Kuspit Casa de Bolsa. Coincide con casa_de_bolsa_hermana=true.
- **Notas**: monex.com.mx devuelve 403 a curl; los PDF se obtuvieron via WebFetch y se parsearon con pdfplumber (copias en g4/monex, nombres A_0926=MONEXCP, B_0926=MONXESG, DICI_MONEXMmas_0926). Los DICI de sep-2026 fueron publicados ~2 oct 2026. La URL de MONEXM+ usa 'MONEXMmas'. Las URLs de agosto (0826) de MONEXCP/MONEXMmas redirigen a la home (no existen).

### Value Operadora (`value`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| VALUEF2 | cartera mensual | 2026-09-30 | 2026-10-05 | [www.value.com.mx](https://www.value.com.mx/documentos/300926.pdf) |
| VALUEF4 | cartera mensual | 2026-09-30 | 2026-10-05 | [www.value.com.mx](https://www.value.com.mx/documentos/300926.pdf) |
| VALUEV6 | cartera mensual | 2026-09-30 | 2026-10-05 | [www.value.com.mx](https://www.value.com.mx/documentos/300926.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| VALUEF2 | 2,887.6 | 2,887.6 | +0.0 % | 5 de 5 (BONOS 320415 reporto 25.98, CFE 22UV 15.33, CPEXACB 16U 9.03, UDIBONO 340824 5.32, BPAG91 310116 reporto 4.55) - % identicos | Reportos 30.5% (25.98+4.55); resto deuda/UDIBONOS/CFE/CB / RF 69.5 / EFE 30.5 - coincide | **Coincide** |
| VALUEF4 | 1,394.2 | 1,394.2 | +0.0 % | 5 de 5 (BONOS 320415 reporto 46.63, BPAG91 310116 reporto 12.20, CETES 270708 3.06, BPA182 300328 2.96, BPAG91 270909 2.39) | Reportos 58.83% (46.63+12.20) / RF 41.2 / EFE 58.8 - coincide | **Coincide** |
| VALUEV6 | 179.4 | 179.4 | +0.0 % | 5 de 5 (GICSA 16U 24.85, TMMCB 10-3 16.72, TMMCB 10-2 15.24, ACWI 11.75, VT 8.89) - % identicos | ETFs de acciones ~34.9% (incluye IB1MXX 2.16%); CB 56.8%; reporto 8.23% / RV 32.7 / RF 59.1 / EFE 8.2 - coincide (portal excluye IB1MXX 2.16% de RV; reporto 8.23% = EFE) | **Coincide** |

- **VALUEF2**: Documento oficial 'Integracion de carteras 30 de septiembre de 2026 (miles de pesos)'. Valores identicos al portal. Comisiones/régimen: No disponible en este documento (es cartera, no DICI).
- **VALUEF4**: Identico al portal. Comisiones/régimen: No disponible.
- **VALUEV6**: El documento tambien muestra VALUEV5 y otros fondos (4 paginas). Existe aviso de rompimiento VALUE V6 (05-oct-2026) en value.com.mx/documentos/05102026 VALUE V6.pdf, no revisado. Comisiones/régimen: No disponible.
- **Notas**: Solo se obtuvo la cartera mensual (value.com.mx/documentos/300926.pdf); no se localizaron los DICI, por lo que no hay distribuidoras ni comisiones. El archivo de agosto (310826.pdf) da 404. La cartera de octubre esta en documentos/301026.pdf. Portal dice casa_de_bolsa_hermana=true (Value Casa de Bolsa, Value Grupo Financiero): no verificado en documento.

### Azimut México (`azimut`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| AZMT-G1 | DICI | 2026-10-30 | 2026-11-05 | [oafondos.com.mx](https://oafondos.com.mx/wp-content/uploads/DICI-AZMT-G1.pdf) |
| AZMT-C1 | DICI | 2026-10-30 | 2026-11-05 | [oafondos.com.mx](https://oafondos.com.mx/wp-content/uploads/DICI-AZMT-C1.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| AZMT-G1 | 4,777.6 | 4,877.7 | -2.0 % | 5 de 5 por serie (CETES 261112, CETES 270513, BPAG28 290201, CETES 271028, CETES 261126 estan en el top10 de sep); % doc 5/4/3/3/3 (enteros) | Gobierno 100% (deuda y reporto BPA182 310918 ~5%) / RF 95.8 / EFE 4.2 | **Diferencia menor** |
| AZMT-C1 | 3,284.9 | 3,232.8 | +1.6 % | 4 de 5 (CETES 280608 7%, CETES 271028 6%, BONDESF 280420 4%, CETES 280412 4% estan en el top5 de sep; CETES 270708 3% fuera del top5 de sep) | Gobierno ~100% (reporto BPA182 310918 ~3%) / RF 94.0 / EFE 6.0 | **Diferencia menor** |
| AZMTEUA | — | — | — | — | — / — | **Sin documento comparable** |

- **AZMT-G1**: El DICI vigente es de octubre (principales inversiones al 30/oct/2026, 56 pags, varias series); no se encontro el de septiembre. Total oct -2.1% vs sep del portal; composicion estable. No es prueba de coincidencia a misma fecha. Comisiones/régimen: Serie A: sin comisiones al cliente ni al fondo (0.06% total); serie F1: admin 1.54% = 1.60% anual.
- **AZMT-C1**: Documento de octubre; total +1.6% vs sep del portal. CETES 280608 7% vs 7.03% del portal en sep. Comisiones/régimen: Serie A: 0.06%; serie F1: admin 1.66% = 1.71% anual (fondo).
- **AZMTEUA**: No se localizo DICI ni cartera (oafondos devolvio 404 para DICI-AZMTEUA.pdf; COVAF sin resultado; busquedas sin resultados).
- **Casa de bolsa hermana**: Distribuidoras en DICI: Kuspit Casa de Bolsa, O'Rourke & Asociados, Grupo Bursatil Mexicano Casa de Bolsa. Ninguna es del grupo Azimut. Coincide con casa_de_bolsa_hermana=false.
- **Notas**: DICI de G1 y C1 bajados de oafondos.com.mx (O'Rourke). Ambos son de octubre 2026; no se hallo el corte de septiembre en linea. Valuadora: COVAF.

### Mifel Operadora (`mifel`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| VALOR1F | cartera mensual | 2026-10-30 | 2026-11-09 | [divulgacion.covaf.com](https://divulgacion.covaf.com/?mod=getCarteras&fondo=VALOR1F&periodo=M) |
| VALOR1F | DICI | 2025-12-31 (plantilla sin cifras; autorizacion 19/10/2026) | — | [docs.mifel.com.mx](https://docs.mifel.com.mx/d/VALOR1FDICI.pdf) |
| VALOR3M | cartera mensual | 2026-10-30 | 2026-11-09 | [divulgacion.covaf.com](https://divulgacion.covaf.com/?mod=getCarteras&fondo=VALOR3M&periodo=M) |
| VALOR3M | DICI | plantilla sin cifras; autorizacion 19/10/2026 | — | [docs.mifel.com.mx](https://docs.mifel.com.mx/d/VALOR3MDICI.pdf) |
| MIFIPC | cartera mensual | 2026-10-30 | 2026-11-09 | [divulgacion.covaf.com](https://divulgacion.covaf.com/?mod=getCarteras&fondo=MIFIPC&periodo=M) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| VALOR1F | 4,596.3 | 4,399.3 | +4.5 % | 3 de 5 (BPAG28 290201 4.13 vs 4.31; BPAG28 290503 2.97 vs 4.31; BONDESG 280316 2.83 vs 2.96); BONDESF 281005 3.92 y CETES 280928 3.97 no estan en el top10 de sep | Directo 92.86%, otros valores/efectivo 7.14%; sin reporto; CB corto plazo 11.1%, pagares 8.05% / RF 98.1 / EFE 1.9 | **Diferencia menor** |
| VALOR3M | 2,427.7 | 2,379.9 | +2.0 % | 3 de 5 (BONDESF 270826 6.19 vs 6.31; BONDESF 280831 4.52 vs 4.63; BONDESG 280316 2.88 vs 2.95); CETES 280608 4.69% de sep ya no esta en top oct | Directo 92.65%, reporto 5.15% (BPA182 310327), otros 2.2% / RF 94.4 / EFE 5.6 - reporto oct 5.15% consistente | **Diferencia menor** |
| MIFIPC | 25.5 | 37.1 | -31.4 % | 4 de 5 nombres (GMEXICO B 13.00 vs 12.24, GFNORTE O 9.44 vs 8.01, AMX B 7.70 vs 5.99, FEMSA UBD 7.40 vs 6.27); CEMEX 7.24 fuera del top5 de sep; portal sep tenia BONDESF 270930 14.76% | Acciones 96.96%, otros 3.04% / RV 85.2 / EFE 14.8 (portal sep, con posicion BONDESF 270930 14.76%) | **Diferencia relevante** |

- **VALOR1F**: Oct vs sep (+4.5%). El DICI publicado esta vacio: 'Principales activos al 31 dic 2025', sin rendimientos, autorizacion 19/10/2026, categoria IDCP corto plazo. mifel.com.mx da 403; cartera obtenida via COVAF (valuadora). Comisiones/régimen: Serie B (DICI): administracion 1.00% anual; distribucion 0.00%; cliente N/A.
- **VALOR3M**: Cartera oct +2.0% vs sep del portal; porcentajes por serie casi identicos. DICI sin cifras. Comisiones/régimen: Serie B (DICI): administracion 0.80% anual; distribucion 0.00%.
- **MIFIPC**: Total oct 25.45 mdp vs 37.12 en sep del portal (-31%); ago fue 33.12. Es de otro mes, asi que no prueba error del portal, pero la caida y la salida de la posicion BONDESF (14.8% en sep) conviene validar con la cartera de septiembre (no hallada). Comisiones/régimen: No disponible (MIFIPCDICI.pdf devolvio 403).
- **Casa de bolsa hermana**: DICI de VALOR1F y VALOR3M: distribuidora = Banca Mifel S.A. IBM, Grupo Financiero Mifel (banco, no casa de bolsa). Consistente con casa_de_bolsa_hermana=false.
- **Notas**: mifel.com.mx y parte de docs.mifel.com.mx responden 403; se usaron copias via WebFetch y COVAF. Los DICI de Mifel son plantillas vacias (cifras al 31-dic-2025), con fecha de autorizacion 19/10/2026.

### Afirme Operadora (`afirme`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| AFIRMES | cartera mensual | 2026-10-30 | 2026-11-03 | [www.afirme.com](https://www.afirme.com/dam/jcr:f69b8fd2-4d89-420a-b2b5-0982d8789bd3/AFIRMES_MEN.pdf) |
| AFIRMES | DICI | 2026-10-30 | — | [www.afirme.com](https://www.afirme.com/dam/jcr:a53bca5f-62e4-4877-9fc4-9c03fa2109fb/AFIRMES%20PERSONAS%20FISICAS.pdf) |
| AFIRPLU | cartera mensual | 2026-10-30 | 2026-11-03 | [www.afirme.com](https://www.afirme.com/dam/jcr:b7f15f71-1593-4aa7-b222-ad702704b2f1/AFIRPLUS_MEN.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| AFIRMES | 6,090.6 | 5,973.8 | +1.9 % | 3 de 5 (CETES 270107 8.99% vs 13.71% sep; BONDESF 271202 6.59 vs 6.71; BONDESF 261203 5.61 vs 5.71); CETES 280928 (reporto 5.53%) y BPAG28 270204 4.93% no estan en top10 sep | Gubernamentales 92.83%, reportos 7.17% / RF 98.3 / EFE 1.7 (sep): reportos subieron a 7.17% en oct | **Diferencia menor** |
| AFIRPLU | 703.7 | 703.3 | +0.1 % | 4 de 5 (BONDESF 310417 14.29 vs 14.28; BPAG91 280511 7.20 vs 7.15; BONDESF 270617 7.14 vs 7.13; FNCOT 24 7.75 vs 7.80); FNCOT 25 9.07% nuevo | Gubernamentales 63.25%, semigub 25.26%, bancarios 7.11%, reporto 4.38% / RF 99.5 / EFE 0.5 (sep) | **Diferencia menor** |

- **AFIRMES**: Documentos de octubre (no se encontro septiembre); total +1.9%, series de BONDESF casi identicas, cambios en CETES/reportos coherentes con movimiento mensual. Distribuidora en DICI: Banca Afirme (banco). Comisiones/régimen: Serie B1: admin 1.32% + distribucion 3.08% + otros = 4.44% anual (fondo); cliente 0%.
- **AFIRPLU**: Total oct 703.72 vs sep 703.31 (+0.06%); porcentajes casi identicos (+-0.1 pt). La clave en la web de Afirme es AFIRPLUS. Comisiones/régimen: DICI no obtenido (la web publica AFIRPLUS PERSONAS FISICAS.pdf, sin revisar).
- **Casa de bolsa hermana**: DICI AFIRMES: distribuidora Banca Afirme S.A. (banco). Sin casa de bolsa del grupo, consistente con false.
- **Notas**: Las carteras mensuales publicadas en afirme.com son de octubre 2026; no hay archivo de septiembre en linea. Comparativo de mes adyacente.

### BTG Pactual (`btg`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| BTGALFA | DICI | 2026-10-30 | 2026-11-05 | [static.btgpactual.com.mx](https://static.btgpactual.com.mx/content/files/investment-funds/portfolio/DICI_BTGALFA.pdf) |
| BTGALFA | cartera mensual | 2026-10-30 | 2026-11-03 | [static.btgpactual.com.mx](https://static.btgpactual.com.mx/content/files/investment-funds/portfolio/Cartera-Mensual-BTG-Alfa.pdf) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| BTGALFA | 716.0 | 670.0 | +6.9 % | 5 de 5 nombres (GENTERA 20.15 vs 19.80; FUNO 15.58 vs 14.74; FEMSA 14.16 vs 19.34; OMA 11.43 vs 15.44; SIGMAF 8.97 vs 8.84); FEMSA y OMA difieren >1 pt | Directo 99.66% (acciones+FUNO), otros valores 0.34% / RV 99.7 / EFE 0.3 - consistente | **Diferencia menor** |

- **BTGALFA**: Documentos de octubre (DICI y cartera mensual). Total oct +6.9% vs sep del portal (ago 681.6); mezcla 99.7% RV consistente. El DICI no trae texto de distribuidoras; O'Rourke distribuye BTG segun oafondos.com.mx/btg. Comisiones/régimen: Serie A: 0.20% anual fondo; serie B1: admin 0.71% + distribucion 1.66% = 2.57% (fondo); cliente 0%.
- **Casa de bolsa hermana**: El DICI no lista distribuidoras en texto extraible; no se pudo verificar.
- **Notas**: Fuente: static.btgpactual.com.mx. No se hallo el corte de septiembre.

### Operadora Punto (`punto`)

| Fondo | Documento | Fecha del dato | Publicado | Liga |
|---|---|---|---|---|
| AZTECA+ | DICI | 2026-10-30 | 2026-11-05 | [divulgacion.covaf.com](https://divulgacion.covaf.com/?mod=getFile&fondo=AZTECA%2B) |
| AZTECA+ | cartera mensual | 2026-10-30 | 2026-11-03 | [divulgacion.covaf.com](https://divulgacion.covaf.com/?mod=getCarteras&fondo=AZTECA%2B&periodo=M) |

| Fondo | Total doc. (mdp) | Total portal (mdp) | Dif. | Principales | Mezcla doc. / portal | Veredicto |
|---|---|---|---|---|---|---|
| AZTECA+ | 169.5 | 153.3 | +10.6 % | 4 de 5 (TPLAY 25 17.89 vs 19.76; TPLAY 00226 11.83 vs 13.07; ELEKTRA 00126 11.81 vs 13.13; CETES 280608 10.51 vs 11.47); BPA182 310918 reporto 11.99% (portal sep tenia BPA182 320923) | Directo 88.01%, reporto 11.99% (BPA182 310918) / RF 87.1 / EFE 12.9 - consistente (EFE oct 11.99%) | **Diferencia relevante** |

- **AZTECA+**: Documentos de octubre; total +10.6% vs sep del portal (ago 102.5, sep 153.3, oct 169.5: fondo creciendo), mezcla y posiciones muy parecidas; la diferencia es mensual, no necesariamente error. Distribuidoras en DICI: Punto Casa de Bolsa y Banco Azteca. Estados financieros 3T-2026 de operadorapunto.mx son PDF escaneado (imagen), no leidos. Comisiones/régimen: Serie A: cliente 0%; fondo: admin 0.30% + distribucion 0.70% = 1.00% anual.
- **Casa de bolsa hermana**: Si: DICI lista Punto Casa de Bolsa (mismo grupo de Operadora Punto) y Banco Azteca como distribuidoras. Coincide con casa_de_bolsa_hermana=true.
- **Notas**: Calificacion HR AA/3LP, categoria IDMP (cambio de prospecto abr-2026); el portal lo trata como RF.

## Limitaciones

- La CNBV aún no publica el R1 (activo neto) de septiembre: el activo neto de ese corte es la suma de la
  cartera del R7, marcado (e) en el portal, hasta que llegue el R1.
- Sitios que bloquean el acceso automatizado o no publican documentos: GBM, Finamex, Nafinsa (ofnafin),
  CIBanco (Cloudflare) y, en parte, Monex y Mifel (403; se usaron copias de la valuadora COVAF o
  WebFetch). No se evadió ningún bloqueo.
- Los documentos se bajaron a una carpeta temporal y se leyeron como texto; no se ejecutó nada de ellos.
