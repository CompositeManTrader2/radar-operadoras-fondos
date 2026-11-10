# Revisión del modelo del radar (auditoría de corrección)

Fecha: 2026-11-10. Alcance: `radar/core/metricas.py`, `radar/core/clasificacion.py`,
`radar/core/tipos_valor.py`, `radar/core/datos/etfs.csv`, `radar/pipeline.py`
(`construir_metricas`, integración R7/R1), `radar/fuentes/cnbv.py`, `radar/store/db.py` y,
solo en lo numérico, `radar/render/html.py`. Referencia: `docs/especificacion.md` y las
decisiones de `README.md`.

Nota de método: durante la revisión otro proceso modificaba el código (archivos con hora
12:18–12:22: `cnbv_generico.py`, `tipos_valor.py`, `cnbv.py`, `db.py`, `config.py`,
`pipeline.py`, `metricas.py`, `html.py`) y el store (12:23). Los números de línea corresponden
al código de las 12:22. Las cifras salen de copias del store en el scratchpad (nunca se
escribió en `data/`); se recalcularon sobre la copia de las 12:23 y no cambiaron. La suite
pasa completa: `65 passed` (7 min 48 s).

## Resumen

Las fórmulas centrales están bien implementadas: exposición, headroom, importe × 2, bolsa con
pb/10 000, ingreso esperado, rotación (deltas valuados al precio posterior, anualización por
días), piso encadenado, escalas, pesos, tiers y veto. También está bien la prioridad
cartera de la operadora > R7 dentro del mismo mes. Las cifras de Finaccess, Multiva y Compass
se reproducen a mano.

Los problemas de fondo están en la **identidad de los fondos y el agregado por operadora**, y
en cuánto pesan los **supuestos** en la calificación:

1. La clave de fondo de la CNBV no siempre es la de la operadora. AXESCSD es AXESCOB y TAURUM
   es BX+USD. Hoy eso crea fondos fantasma, rotación sin medir y un momentum mal calculado.
   Cuando llegue el R7 de un mes que ya tiene cartera de la operadora, el mismo fondo se
   contará dos veces.
2. En las operadoras cubiertas solo con la CNBV, la bolsa (30 % de la calificación) sale
   entera del supuesto de rotación 0.20–0.60. Inbursa tiene bolsa = 5 con 109.5 mdp sin
   ninguna rotación medida.
3. Los fondos que tienen acciones de fondos hermanos por debajo del umbral de fondo de fondos
   (50 %) se cuentan dos veces en activo neto, exposición y bolsa. Hoy no pasa en las tres
   operadoras con adaptador propio, pero sí en el universo CNBV (p. ej. OIXE/NTECT con 18 %
   en hermanos, 26.8 mil mdp).

Ningún hallazgo cambia hoy el tier de Finaccess (3.97, Tier 2), Multiva (1.65, Tier 3 con
veto) ni Compass (4.30, Tier 1). Finaccess está a 0.03 del Tier 1 y su bolsa media quedaría a
0.03 mdp del corte de 6 mdp en cuanto alcance 6 cortes (hallazgo 5).

## Hallazgos (por severidad)

### Alta

**1. La clave CNBV y la clave de la operadora del mismo fondo no se emparejan: fondos
duplicados o fantasma.**
`radar/pipeline.py:174-179` (`_ingestar_r7` da de alta "Solo en CNBV" a todo fondo R7 cuya
clave no está en el universo) y `radar/store/db.py:111-135` (la prioridad mensual > R7 se
aplica por `fondo_clave`).
- Evidencia en el store: AXESCSD (R7, 31-ago, 496.9 mdp) tiene exactamente las mismas
  posiciones que AXESCOB (cartera diaria 10-sep, 499.8 mdp): IB01 74 039 títulos, BIL 14 651,
  SHV 11 951, FLOT 15 209… TAURUM (R7, 31-ago) es BX+USD (30-sep): misma chequera en dólares
  0732245 y VUAA.
- Efectos de hoy:
  - (a) AXESCSD y TAURUM aparecen en el pie como "administrado sin cartera".
  - (b) AXESCOB y BX+USD salen con rotación "sin medición" aunque hay dos cortes.
  - (c) El momentum excluye el fondo del corte previo pero lo incluye en el actual:
    - Finaccess: +12.7 % reportado contra +8.2 % correcto (13 443 / (11 928 + 497) − 1).
    - Compass: +0.45 % reportado contra −0.96 % correcto (21 945 / (21 846 + 311) − 1). Su
      puntaje de momentum pasa de 4 a 2, "headroom y momentum" de 2.5 a 1.5 y el total de
      4.30 a 4.20.
- Efecto latente: cuando llegue el R7 de octubre, AXESCSD no tiene mensual "del mes" con su
  clave, así que se guarda como corte `cnbv_r7` y `construir_metricas` (`del_mes`, línea 306)
  lo suma junto con AXESCOB. Eso duplica unos 540 mdp de Finaccess (+4 % de activo neto). Lo
  mismo pasará con TAURUM/BX+USD en Compass con el R7 de septiembre.
- Arreglo: una tabla de alias `clave_operadora → clave_cnbv` por adaptador (o en
  `config/`), aplicada en `carteras_r7`/`activos_r1` antes de guardar. Además, una
  validación que falle (o avise en `estado`) cuando en un mismo mes haya un fondo "Solo en
  CNBV" y un fondo de la operadora sin R7. Se puede proponer el emparejamiento automático
  por traslape de posiciones ≥ 90 %. Falta una prueba para esto.

**2. En las operadoras solo CNBV, la bolsa y el tier salen enteros del supuesto de rotación.**
`radar/core/metricas.py:185` (banda sin medición 0.20–0.60), `:391-392` (`bolsa_media`) y
`:425` (`s_bolsa`).
- Con un solo R7 por fondo nunca hay un par de cortes, así que `rotacion.media` = 0.40 (e)
  para todos los fondos.
- Ejemplo (store actual): Inbursa tiene exposición RV de 81 301 mdp, bolsa media de
  109.5 mdp y bolsa = 5, con `rotacion_ponderada = (0.40, False)`. Se salva del Tier 1 solo
  por el veto.
- Una operadora sin casa de bolsa hermana y con ese tamaño tendría 0.30·5 + 0.25·5 +
  0.20·ajuste + 0.10·2 + 0.10·2 + 0.05·3 ≈ 3.3 + 0.20·ajuste. Con un ajuste ≥ 3.5 llega a
  Tier 1 sin un solo dato de rotación: la bolsa queda proporcional al AUM.
- La marca (e) sale en el pie, pero el tier no la refleja.
- Arreglo (cualquiera de estas opciones):
  - (a) Si menos del X % de la exposición RV tiene rotación medida, el criterio de bolsa se
    topa (p. ej. en 3) o el tier se publica como "provisional".
  - (b) Calcular `s_bolsa` sobre el piso medido y no sobre la media supuesta.
  - (c) Mostrar en el comparativo la fracción de la bolsa que viene de supuesto.

**3. Doble conteo por tenencias en fondos hermanos por debajo del umbral de fondo de fondos.**
`radar/core/metricas.py:58-71` (transparencia), `:232-234` (exposición), `:364-369`
(sumas por operadora) y `:255-260` (bolsa).
- El fondo A que tiene acciones del hermano B suma la RV de B a su propia exposición. El
  activo neto de B ya incluye ese dinero, así que activo neto, exposición e importe se cuentan
  dos veces.
- La bolsa es peor: a la parte transparentada se le aplica la rotación de A, que se midió solo
  sobre lo directo (los renglones FONDO no tienen clase en `_libro_rv`). Esas operaciones ya
  las ejecuta B y ya están en la bolsa de B.
- Con un 50 % en hermanos el fondo se excluye entero; con un 49 % se cuenta dos veces. Hay un
  escalón.
- Medido en el R7 de agosto (fondos no-FdF con acciones de fondos de su misma operadora):

  | Operadora | Fondos | En hermanos | % de la operadora | Ejemplos |
  |---|---|---|---|---|
  | OIXE | 2 | 27 126 mdp | 5.3 % | NTECT: 18 % en NTEGUB/NTEGUB+ |
  | IMPFOND | 9 | 19 447 mdp | 2.0 % | GOLD1+: 36.5 % en BLKDIN; BLK2040: 38 % |
  | OPGBM | 9 | 5 674 mdp | 2.8 % | GBM106: 14 % en GBMDOL (tipo 52) |

  En Finaccess, Multiva y Compass hoy es 0 % (solo los FdF tienen hermanos), por eso no se
  ve en sus cifras.
- Arreglo:
  - En los agregados por operadora, restar la parte de cada fondo invertida en hermanos que
    también están en `fondos`. Para activo neto y exposición basta con no transparentar
    hermanos analizados y quitar ese monto del activo neto del tenedor.
  - En la bolsa, aplicar la rotación del fondo solo a su exposición directa.
  - Mantener la transparencia solo para la mezcla mostrada por fondo, y para hermanos que no
    están en el universo analizado (FdF excluidos o de otra operadora).
  - Prueba: dos fondos A→B con suma de activos y bolsa invariante.

### Media

**4. El momentum no es comparable entre operadoras ni entre cortes.**
`radar/pipeline.py:338-347` y `radar/core/metricas.py:418-422, 434`.
- (a) La ventana no se normaliza. Finaccess y Multiva miden 31-ago→30-oct (2 meses), Compass
  31-ago→30-sep (1 mes), y los umbrales son los mismos (±5 %).
- (b) El conjunto de fondos no es el mismo en ambos lados. Solo se suman los fondos analizados
  hoy que tienen corte exactamente en la fecha `previo`: un fondo nuevo, o con fecha distinta
  dentro del mes, cuenta como crecimiento (ver hallazgo 1). Además, si dentro de un mismo mes
  hay dos fechas de corte (p. ej. 30 y 31), `previo` cae en el mismo mes y el momentum
  compara octubre contra octubre parcial.
- (c) Mezcla activo oficial R1 (previo) con activo estimado = total de cartera (actual, todo
  Multiva y todo Compass). El sesgo calibrado es de −0.3 % a +1.8 %, del orden del umbral de
  0 %.
- (d) Mide el cambio de AUM, que incluye el rendimiento de mercado. En operadoras de RV, un
  mes de ±5 % del índice mueve el puntaje sin que haya flujo.
- (e) Sin corte previo, el puntaje es 3, mejor que un momentum medido de −1 %.
- Arreglo:
  - Flujo neto ≈ AN_t − AN_{t−1}·(1 + r), con r el rendimiento de la cartera (o del precio
    de la serie, si se tiene).
  - Normalizarlo a tasa mensual y sobre el mismo conjunto de fondos en ambos lados (por fondo,
    con su corte previo propio).
  - Usar la misma fuente (estimado o R1) en los dos extremos.

**5. Salto de −20 % en la rotación "media" al llegar a 6 cortes.**
`radar/core/metricas.py:166-167, 188`.
- Con menos de 6 cortes, `media = (piso + 1.5·piso)/2 = 1.25·piso`; con 6 o más,
  `media = puntual = piso`. Con los mismos datos, la bolsa media de todas las operadoras cae
  20 % en cuanto se acumula el sexto corte.
- Ejemplo: Finaccess pasa de 7.54 a 6.03 mdp, a 0.03 mdp del corte de 6 mdp (bolsa = 4). Un
  movimiento menor de mercado la baja a 3 y el total queda en ~3.67.
- Arreglo: que la cifra "puntual" use el mismo estimador central (p. ej. piso × factor (e)),
  o que la banda también use el piso como valor central. Es decir, no mezclar un estimador
  de piso con uno de punto medio.

**6. Un solo tramo de un mes anualizado × 12 domina la bolsa.**
`radar/core/metricas.py:151, 180-189`.
- En Compass, la bolsa (30.8 mdp) viene en 59 % de STRAT (18.3 mdp), con una sola medición de
  31-ago a 30-sep: 1.35×.
- BX+4 sale con 2.64× y CRECE+ con 0.85×, también de un solo mes.
- La banda [piso, 1.5·piso] no representa la incertidumbre de muestreo. Un mes de
  reacomodo (STRAT compró 6 emisoras nuevas por ~377 mdp) se proyecta como ritmo anual.
- Hoy no cambia el tier (sin STRAT la bolsa seguiría ≥ 12 mdp), pero en otras operadoras sí
  puede.
- Arreglo: marcar "1 tramo" en el comparativo; para `s_rec`, exigir ≥ 3 tramos o encoger la
  rotación medida hacia el supuesto según los meses observados (p. ej. ponderando por
  meses/6).

**7. El piso con renglones agregados desperdicia ventas seguras (subestima).**
`radar/core/metricas.py:135-138`.
- Cuando el corte B agrupa un tipo de valor ("OTROS TIPO DE VALOR 1ASP"), todo instrumento de
  A que desaparece se ignora.
- El agregado de B acota cuánto de eso sigue en cartera:
  ventas seguras ≥ Σ(omitidas) − valor del agregado.
- Ejemplo STRAT: omitidas 544.0 mdp (AEM, AVGO, BAC, B, CIEN, COIN, FIX, HOOD, PDD, PLTR, UNH,
  WWD); agregado 186.2 mdp. Hay ≥ 357.8 mdp de ventas que hoy no cuentan. El piso pasaría de
  1.35× a ≈ 2.37×. Lo mismo, a menor escala, en BX+4 y MVFANG+.
- Es conservador (no infla), pero mezcla pisos más y menos ajustados entre operadoras: las
  que agrupan (Multiva, Compass) quedan castigadas.
- Arreglo: sumar `max(0, Σ omitidas − agregado_B)` a ventas (y lo simétrico para compras
  cuando A agrupa).

**8. La conciliación de activo neto operadora↔R1 se sobrescribe con la de R7↔R1.**
`radar/store/db.py:49` (PK `operadora, fondo_clave, fecha, concepto`),
`radar/pipeline.py:179` y `:231`.
- `parsear` guarda primero "activo neto" (cartera de la operadora vs R1) y luego, en
  `_ingestar_r7`, otra vez "activo neto" (suma R7 vs R1) con la misma fecha, porque la fecha
  R7 es el último día con R1 del mes, que coincide con el cierre de la operadora.
- La segunda borra la primera: para Finaccess, que sí publica activo neto, el contraste
  > 10 % que pide la especificación ("mostrar ambos y marcar") se pierde en régimen
  permanente.
- Además, `metricas_fondo` (`metricas.py:307-315`) marca como discrepancia del corte de la
  operadora una diferencia R7↔R1, aunque ese corte no use R7.
- Hoy está latente: no hay R1 de 10-sep ni de 30-oct.
- Arreglo: incluir la fuente en la clave (p. ej. conceptos "activo neto (operadora vs R1)" y
  "activo neto (R7 vs R1)") y filtrar en `metricas_fondo` por la fuente del corte que se usa.

**9. El R7 se lee de una hoja dinámica que puede venir filtrada: pérdida silenciosa.**
`radar/fuentes/cnbv.py:72-97`, `:145-150`.
- `052_1G_R7_2025.xlsm` trae en MINFO solo 543 renglones, todos de AZMT-MX: la hoja BD
  muestra el filtro `cve_administradora = (Varios elementos)`. El de 2026 trae `(Todas)`
  (18 002 renglones, 29 operadoras).
- Para cualquier otra operadora, `carteras_r7` devuelve lista vacía y no avisa.
- Para las operadoras solo CNBV eso significa perder el mes entero sin aviso.
- Arreglo: leer el filtro de BD (celda H1 = "(Todas)") y fallar o avisar si no es "(Todas)";
  avisar también cuando una `clave_cnbv` configurada no aparece en un R7 que sí trae el periodo.

**10. Un piso medido de 0 vale menos que no tener medición.**
`radar/core/metricas.py:185-189`.
- MULTIEQ (1 638 mdp, 94.9 % RV, 3 instrumentos sin cambio en 2 meses) y PAM tienen banda
  0.00–0.00 y bolsa 0.
- Un fondo sin dos cortes recibe 0.20–0.60 (e). Con el mismo desconocimiento de la rotación
  real, el medido-cero sale castigado frente al no medido: si a MULTIEQ se le diera el
  supuesto, la bolsa de Multiva pasaría de 2.0 a ~5.1 mdp y su puntaje de bolsa de 2 a 3.
- El piso de 0 en un tramo es información legítima, pero la banda debería tener un techo
  distinto de 0.
- Arreglo: techo = max(piso·1.5, piso + algo del supuesto) cuando los tramos son pocos, o
  tratar "0 en un tramo" como no concluyente.

### Baja

11. **Headroom: el denominador incluye fondos sin régimen.** `metricas.py:384-385, 431`. El
    headroom suma 0 por los fondos con `rv_max=None` (BX+4, CRECE+, RVMAX1 en Compass), pero
    su exposición sí entra al denominador. Compass: 481.9/7 791 = 6.2 %; sin esos fondos,
    481.9/5 390 = 8.9 %. Además, con fondos de RV al ~96 % la razón casi nunca llega a 0.10, así
    que el criterio vale 1 en las tres operadoras y no discrimina. Arreglo: excluir del
    denominador los fondos sin régimen y revisar `HEADROOM_CORTES`.
12. **Reparto local/SIC de la bolsa por tenencia y no por lo operado.** `metricas.py:245-260`.
    En BX+4, la tenencia local es 34.3 %, pero de lo operado entre 31-ago y 30-sep solo
    FRAGUA (9.1 de 190.7 mdp, ~5 %) fue local. Como la comisión SIC (25 pb) es mayor que la
    local (15 pb), se subestima un poco. Arreglo: `rotacion_observada` ya conoce el mercado de
    cada delta; guardar compras/ventas por mercado y usar ese reparto cuando haya medición.
13. **Materia prima, inconsistente.** `clasificacion.py:124-134`. Un ETF local de materia prima
    va a RV_LOCAL y uno extranjero a RV_ETF. En ambos casos infla %RV y headroom frente a un
    régimen de RV que no contempla oro. Es una desviación documentada; al menos conviene
    usar la misma clase y excluirlo del headroom.
14. **Subyacente sin cartera.** `metricas.py:73`. Todo fondo tipo 52 se asigna a RV_LOCAL
    aunque sea global (sube `share_local` y baja la bolsa); el 53 va a RF. Conviene marcar
    "mercado por confirmar" o usar la clasificación R1 del subyacente.
15. **El conteo de cortes incluye la cartera diaria.** `metricas.py:187`. El tramo de 10 días
    31-ago→10-sep (Finaccess) cuenta para los 6 cortes y se anualiza × 36 (AXESUSA 1.35×,
    AXESEDM 1.19× en ese tramo). Pesa poco en el piso encadenado, pero acelera el cambio a
    "cifra puntual". Arreglo: contar solo cortes mensuales para `CORTES_PARA_CIFRA`.
16. **El docstring de `piso_encadenado` es incorrecto.** `metricas.py:171-174`. El piso
    encadenado es el promedio ponderado (por base·meses) de los pisos de cada tramo: no es
    "más ajustado que cualquier par aislado". AXESEDM: tramos 1.19× y 0.62×, cadena 0.72×. Sí
    es ≥ que comparar directo el primer corte contra el último (eso es lo que prueba el test).
17. **No hay control de precio implícito ni de eventos corporativos.** `metricas.py:139-146`.
    Un split se contaría como compra. Hoy hay un solo salto anómalo: ACN en AXESUSA, de
    3 024 a 4 856 MXN por título entre 10-sep y 30-oct (delta −0.59 mdp). Arreglo: si
    |Δtítulos|/títulos ≥ 30 % y el valor casi no cambia, o si el precio salta > 50 %, marcar
    y excluir del tramo.
18. **Rotación con base mínima.** I+USD sale con 12.1× sobre una base de 0.5 mdp (vendió su
    único ETF). No entra en la ponderada (exposición 0), pero conviene una base mínima (p. ej.
    1 % del activo) antes de reportar.
19. **Render.** El texto de la burbuja (`plantillas.py:150`) dice "punto medio de la banda",
    pero con ≥ 6 cortes usa el valor puntual. `_top` (`html.py:110-127`) suma valores de
    cartera sin escalar al activo neto, mientras las tablas sí escalan (la diferencia es
    mínima).
20. **README.** Dice que solo Multiva estima el activo neto. Compass también (16 fondos (e),
    `formato_publicaciones.py:131`).
21. **Redondeo antes del umbral.** `metricas.py:441`. `round(total, 2)` antes de comparar con
    4.0: un 3.995 se vuelve 4.0 y pasa a Tier 1. Conviene comparar el valor sin redondear y
    redondear solo al mostrar.

## Desviaciones documentadas en README: evaluación

- **Denominador de la rotación = exposición RV promedio (no activo neto). Sólida.** Hace que
  importe = exposición × rotación × 2 ≈ (compras + ventas) anualizadas. Con el activo neto
  de la especificación, en fondos mixtos el importe se multiplicaría por %RV dos veces. La
  base incluye RV no seguible (agregados), lo que solo baja el piso.
- **Piso encadenado Σ operado/2 ÷ Σ base·meses/12 y exclusión de tramos > 4 meses. Sólido**,
  y mejor que comparar el primer corte contra el último. Solo el docstring está mal
  (hallazgo 16).
- **Ignorar emisoras cuando un corte agrupa y el otro desglosa. Sólido como piso**, pero se
  puede ajustar más (hallazgo 7).
- **R7 entra como corte solo si no hay cartera de la operadora del mes; R1 sustituye al
  activo estimado a ±3 días. Correcto**, salvo el emparejamiento de claves (hallazgo 1) y la
  colisión de la conciliación (hallazgo 8).
- **Activo neto estimado = total de cartera (Multiva, Compass), con calibración R7↔R1
  (−0.3 % a +1.8 %).** Razonable para exposición y bolsa. No sirve para el momentum si el
  otro extremo es oficial (hallazgo 4).
- **GLD en RV_ETF (e).** Aceptable comercialmente (se ejecuta por SIC), con los matices del
  hallazgo 13.
- **Cartera diaria de Finaccess como corte adicional.** Aceptable para la rotación; no
  debería contar para los 6 cortes (hallazgo 15).

## Verificado y correcto

- **Fórmulas de la especificación** (`metricas.py:232-263, 398-402`):
  - exposición = AN × %RV; headroom = max(0, máx − %RV) × AN; importe = exposición ×
    rotación × 2.
  - bolsa = importe·share_local·15 pb + importe·(1 − share_local)·25 pb, con pb → fracción
    /10 000 en `config.py:64-70`.
  - ingreso = bolsa × 15 % × probabilidad. Finaccess: 6.03–9.05 × 0.15 × 0.35 = 0.317–0.475 mdp ✓.
- **Rotación** (`metricas.py:125-153`): compras/ventas por títulos, valuadas al precio
  posterior (o anterior si el instrumento sale), meses = días/30.4375. Recalculado: STRAT
  ((424.3 + 41.7)/2)/2 104 × 12/0.99 = 1.34× ✓; AXESBMV tramos 0.141× y 0.225× ✓.
- **Claves de instrumento entre fuentes distintas** (R7 vs PDF de cada operadora): emisora
  canónica + serie coinciden. AXESCAP: 12 instrumentos con delta 0 entre R7 y la cartera
  diaria; AER|N, AMZN|*, TSM|N, etc. emparejan en STRAT. No hay compras/ventas espurias por
  formato.
- **Calificación** (`metricas.py:424-449`): los pesos suman 1 (validado al cargar);
  `escala` da 1 + número de cortes alcanzados; tiers ≥ 4.0 / ≥ 3.0; veto ⇒ independencia = 1
  y nunca Tier 1 (Multiva 1.65, Tier 3, veto ✓).
- **Unidades**: `rv_max` y los porcentajes son fracciones (BX+USD máximo 0.20); la bolsa se
  compara en pesos contra `BOLSA_MXN_CORTES`; `mdp()` divide entre 10⁶; `pb()` imprime los pb
  del parámetro.
- **Fondos de fondos**: el umbral se calcula sobre el total publicado; se excluyen de todos
  los agregados y el pie lista sus posiciones directas (AXESFIN 100 %, AXESPRO 79.2 %,
  MULTIBA/MULTIED/MULTIFA ≈ 99.6 %).
- **Prioridad PDF vs R7 del mismo mes** (`db.py:118-157`, `pipeline.py:180-189`,
  `construir_metricas:306-309`): R7 no entra si ya hay mensual del mes; si la mensual llega
  después, borra el R7; en métricas se prefiere la mensual. Hay prueba
  (`test_store_prioriza_cartera_de_la_operadora_en_el_mismo_mes`).
- **Selección de corte**: `latest` = última fecha mensual; los fondos se toman por mes;
  `compare` usa el último corte ≤ la fecha de cada operadora.
- **Clasificación**: reportos = EFE; acciones de fondos sin clase y transparentadas; un ETF
  fuera del diccionario hace fallar (y en R7 el pipeline lista los pendientes en vez de
  adivinar); agregados de ETFs solo con subyacente único inferido de R7; tipo de valor
  desconocido hace fallar. Los derivados se excluyen y se anotan.
- **`etfs.csv` (75 entradas), revisadas una por una: las asignaciones RV/DEUDA son correctas.**
  - Bien clasificados de casos dudosos: RING (mineras de oro = acciones, RV), NLR (acciones
    de uranio/nuclear, RV), FLOT (bonos corporativos flotantes, DEUDA), HDV (RV), y VBIL,
    SGOV, USFR, BIL, SHV, IEI, IEF, IBTA, IB01, IBGS (DEUDA).
  - Solo descripciones por confirmar, sin efecto en la clase: IB1MXX (la descripción
    "deuda gubernamental mexicana" puede ser incorrecta; es deuda en cualquier caso), VDST
    (Treasury 0–1 años UCITS), CJPU y TFRN (emisor [POR CONFIRMAR]).
  - Ninguno es apalancado o inverso. En los pendientes de otras operadoras sí aparece SPXL
    (3×): al agregarlo convendría marcarlo.
- **Tipos de valor**: 1A/1ASP/1ESP/1MSP/YYSP → acción SIC; 1I/1ISP → ETF extranjero;
  1B → TRAC local; CF/FF/FE → FIBRA; 51/52/53 → fondo; CH*/AIM/EAIM → efectivo; 56SP → deuda.
  Son consistentes.
- **HTML**:
  - La fila de totales usa el activo neto como base: %RV total = exposición/AN, igual que
    los KPIs ✓.
  - %RV + %RF + %EFE = 100 % por fondo ✓.
  - El comparativo muestra la banda de bolsa y la de ingreso, en mdp ✓.
  - La burbuja usa la bolsa con la media del fondo ✓.

## Pruebas faltantes sugeridas

- Alias de clave CNBV↔operadora (el hallazgo 1 duplicaría un fondo sin que falle nada).
- Invariancia de activo, exposición y bolsa con un fondo A invertido en un hermano B.
- Momentum con un fondo nuevo, con ventanas de 1 y 2 meses, y con estimado vs oficial.
- Conciliación de activo neto de la operadora y de R7 en la misma fecha.
- R7 con filtro de administradora distinto de "(Todas)".
