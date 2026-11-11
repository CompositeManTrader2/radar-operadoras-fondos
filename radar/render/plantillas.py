"""TODO el texto fijo de los entregables vive aquí, separado de los datos.

REGLA DE ACTUALIZACIÓN: al correr un corte nuevo el documento debe salir IDÉNTICO
al anterior cambiando únicamente las cifras. No renombrar columnas, no acortar
etiquetas, no reescribir frases. Si algo aquí cambia, es una decisión editorial
deliberada y se versiona (VERSION_PLANTILLAS); el test de plantillas lo detecta.
"""

VERSION_PLANTILLAS = "2026-11-11.2"

# --------------------------------------------------------------- identidad
# Identidad de Punto Casa de Bolsa (puntocasadebolsa.mx): morado #522D6D, tipografías Ubuntu
# (títulos y logotipo) y Open Sans (texto). Herramienta interna de la mesa de capitales.
MARCA = "punto"
MARCA_SUB = "casa de bolsa"
MARCA_AREA = "Mesa de Capitales · Radar de operadoras de fondos"
MARCA_NOMBRE = "Punto Casa de Bolsa"

# --------------------------------------------------------------- encabezado
TITULO_OPERADORA = "Radar de operadoras · {operadora}"
ETIQUETA_CORTE = "Corte"
ETIQUETA_PARAMETROS = "Parámetros"
PARAMETROS = (
    "Comisión local {local} pb · Comisión SIC {sic} pb · Captura objetivo {captura} · "
    "Probabilidad de alta {alta} (e)"
)
ALTA_POR_OPERADORA = "por operadora"
PAR_DE_CORTES = "{a} y {b}"
ETIQUETA_CASA_BOLSA = "Casa de bolsa hermana"
SI = "Sí"
NO = "No"

# --------------------------------------------------------------- indicadores
INDICADORES = (
    ("fondos", "Fondos administrados"),
    ("activos", "Activos netos totales"),
    ("fondos_rv", "Fondos con renta variable"),
    ("monto_rv", "Monto en renta variable"),
    ("monto_rf", "Monto en renta fija"),
    ("monto_efe", "Efectivo y reportos"),
)
SUB_FONDOS = "{n} fondo(s) de fondos excluido(s)"
SUB_MDP = "millones de pesos"
SUB_FONDOS_RV = "de {n} analizados"
SUB_PCT_ACTIVOS = "{pct} de los activos netos"

# --------------------------------------------------------------- donas
TITULO_DONA_FONDOS = "Número de fondos"
TITULO_DONA_ACTIVOS = "Activos netos por tipo de fondo"
TIPO_FONDO = {"RV": "Renta variable", "RF": "Renta fija"}
LEYENDA_FONDOS = "{n} fondos"
LEYENDA_ACTIVOS = "{mdp} mdp"

# --------------------------------------------------------------- tabla de fondos
TITULO_TABLA_FONDOS = "Fondos administrados"
COLUMNAS_FONDOS = (
    "Clave", "Nombre corto", "Tipo de fondo", "Categoría regulatoria", "Activos netos (mdp)",
    "Mezcla", "% RV", "% RF", "% Efectivo", "RV (mdp)", "RF (mdp)",
)
FILA_TOTAL = "Total"
LEYENDA_MEZCLA = (("rv", "Renta variable"), ("rf", "Renta fija"), ("efe", "Efectivo y reportos"))
MARCA_ESTIMADO = "(e)"
MARCA_DISCREPANCIA = "‡"
MARCA_HERMANOS = "†"
TIER_PROVISIONAL = "{tier} (provisional)"

# --------------------------------------------------------------- top 20
TITULO_TOP_RV = "Top 20 · renta variable"
TITULO_TOP_RF = "Top 20 · renta fija"
COLUMNAS_TOP = ("#", "Emisora", "Monto (mdp)", "Peso relativo")
SIN_POSICIONES = "Sin posiciones en esta clase."

# --------------------------------------------------------------- pie
# --------------------------------------------------------------- qué enviarle
TITULO_QUE_ENVIARLE = "Qué enviarle"
INTRO_QUE_ENVIARLE = (
    "Research, noticias e ideas sugeridos a partir de su cartera: qué emisoras pesan más, qué compró o vendió "
    "entre los dos últimos cortes (en títulos, sin efecto precio) y cómo reparte su renta variable y su renta fija."
)
ETIQUETA_POR_QUE = "Por qué"
ETIQUETA_QUE_ENVIAR = "Qué enviar"
SIN_TEMAS = "Sin temas sugeridos para este corte."
TITULO_EMISORAS_CLAVE = "Emisoras clave"
COLUMNAS_EMISORAS_CLAVE = ("Emisora", "Nombre", "Sector", "Peso en su RV", "Fondos", "Movimiento")
TITULO_SALIDAS = "Vendió por completo"
SALIDA = "{emisora} ({mdp} mdp en el corte anterior)"

TITULO_METODOLOGIA = "Metodología"
METODOLOGIA = (
    "Fuente primaria: cartera de valores mensual publicada por la operadora; régimen de inversión "
    "tomado del DICI y del prospecto específico. Régimen = lo que el fondo puede tener; composición "
    "efectiva = lo que tiene; nunca se usa uno para estimar el otro.",
    "Clasificación con reglas duras, una clase por posición: renta variable local (BMV/BIVA, FIBRAS y "
    "ETFs listados en México con subyacente accionario), renta variable SIC (acciones extranjeras en "
    "directo), ETFs de renta variable, renta fija (incluye ETFs cuyo subyacente es deuda) y efectivo "
    "(reportos y depósitos a la vista). Un ETF se clasifica por su subyacente según el diccionario "
    "versionado {version_etfs}. Los reportos se cuentan como efectivo, no como deuda.",
    "Las acciones de otros fondos se transparentan con la cartera del fondo subyacente del mismo corte.",
    "Montos en millones de pesos (mdp) a valor razonable; porcentajes sobre el total de la cartera "
    "aplicados al activo neto. Cada posición cuadra contra el total publicado con tolerancia de {tol}.",
    "Rotación observada: compara títulos por emisora entre cortes consecutivos, valora cada cambio al "
    "precio implícito del corte posterior y encadena los tramos: Σ ((compras + ventas) / 2) entre "
    "Σ (exposición a renta variable × meses / 12). Es un PISO, no la rotación real: solo ve el cambio "
    "neto entre cierres, no las vueltas dentro del periodo. Tramos de más de {max_meses} meses no "
    "cuentan. Con menos de {n_cortes} cortes se reporta banda, nunca cifra puntual.",
    "Fuentes complementarias de la CNBV (Portafolio de Información, sector 52): R7, cartera mensual de "
    "cada fondo, se usa como corte cuando no hay cartera de la operadora de ese mes; R1, activo neto "
    "diario, sustituye al activo neto estimado cuando coincide la fecha. Ambos se concilian contra los "
    "documentos de la operadora; las diferencias mayores a {umbral} se muestran con ‡.",
)
TITULO_ROTACION = "Rotación y bolsa de comisión"
ROTACION_RESUMEN = (
    "Rotación ponderada por exposición: {rot}. Importe anual operado (dos puntas): {importe} mdp. "
    "Bolsa de comisión: {bolsa} mdp. Headroom de renta variable según régimen: {headroom} mdp."
)
ROTACION_MEDIDA = "{n} de {total} fondos con renta variable tienen rotación medida con los tramos {cortes}."
ROTACION_SIN_MEDIR = "Sin dos cortes comparables: se usa la banda supuesta {banda} (e)."
TITULO_EXCLUSIONES = "Exclusiones"
EXCLUSION_FDF = (
    "Se excluyen los fondos de fondos: su cartera son acciones de otros fondos de la casa, no valores "
    "en bolsa; no generan ejecución y contarlos duplicaría el flujo de los fondos subyacentes."
)
EXCLUSION_FDF_FONDO = "{clave}: {pct_fondos} en acciones de otros fondos; activo en directo que se va con él: {directo}."
SIN_DIRECTO = "ninguno"
EXCLUSION_NO_DISPONIBLE = "Fuera de cifras (no administrados por la operadora o sin documentos):"
TITULO_SUPUESTOS = "Supuestos (e)"
TITULO_HUECOS = "Huecos [POR CONFIRMAR]"
SIN_HUECOS = "Sin huecos en este corte."
TITULO_DISCREPANCIAS = "Discrepancias entre documentos (‡)"
TITULO_FUENTES = "Fuentes"
FUENTE_FONDO = "{clave}: {cita} · sha256 {sha}"
FUENTE_DICI = "{clave} DICI: {cita}"
PIE_FINAL = (
    "Punto Casa de Bolsa · Mesa de Capitales. Documento generado por radar {version} (plantillas "
    "{version_plantillas}). Uso interno; no es material para clientes ni constituye recomendación de inversión."
)

SUPUESTO_ACTIVO_NETO = "{n} fondo(s) sin activo neto publicado: se aproxima con el total de la cartera de valores."
SUPUESTO_ROTACION = "Techo de la banda de rotación = piso observado × {mult}."
SUPUESTO_SIN_MEDICION = "Fondos sin dos cortes: banda de rotación {banda}."
SUPUESTO_ALTA = "Probabilidad de alta {alta}: {nota}"
SUPUESTO_OTROS_VALORES = (
    "Renglones 'OTROS VALORES' tratados como depósitos a la vista; el DICI los reporta como chequeras."
)
SUPUESTO_AGREGADOS = (
    "{n} renglón(es) agregados por la operadora sin emisora ({mdp} mdp): cuentan en la mezcla, no en "
    "el top 20 ni en la rotación."
)
HUECO_SIC = "Claves SIC sin emisora confirmada: {claves}."
HUECO_REGIMEN = "Límite máximo de renta variable sin localizar: {claves}."
HUECO_ACTIVO_NETO = "Activo neto oficial (CNBV) pendiente para: {claves}."
HUECO_CASA_BOLSA = "Casa de bolsa hermana sin confirmar."
HUECO_ETF_MEDIA = "ETFs clasificados con fuente secundaria (verificar): {lista}."
NOTA_HERMANOS = (
    "† Excluye {mdp} mdp en acciones de fondos de la misma operadora: ya se cuentan en el fondo "
    "subyacente y no generan ejecución en bolsa."
)
NOTA_PROVISIONAL = (
    "Calificación provisional: la rotación está medida en menos de la mitad de la exposición a renta "
    "variable; la bolsa sale del supuesto (e). Una calificación provisional no puede ser Tier 1."
)
HUECO_SIN_CARTERA = "Fondos administrados sin cartera de este corte: {lista}."
ITEM_SIN_CARTERA = "{clave} ({nota})"
SUPUESTO_CALIBRACION = (
    "Calibración: el {fecha}, último corte con activo neto oficial (CNBV R1), el total de cartera "
    "difirió del activo neto entre {minimo} y {maximo} por fondo."
)
FUENTE_CORTE_PREVIO = "{clave} corte {fecha} (rotación): {cita}"

# --------------------------------------------------------------- comparativo
TITULO_COMPARATIVO = "Radar de operadoras · comparativo"
SUBTITULO_COMPARATIVO = "Cortes solicitados: {cortes}"
TITULO_CALIFICACION = "Calificación ponderada (1 a 5)"
COLUMNAS_CALIFICACION = (
    "Operadora", "Corte", "Casa de bolsa hermana", "Bolsa de comisión (30%)", "Independencia de canal (25%)",
    "Ajuste al servicio (20%)", "Recurrencia del flujo (10%)", "Headroom y momentum (10%)",
    "Fricción de alta (5%) (e)", "Calificación", "Tier", "Bolsa (mdp)", "Ingreso esperado (mdp) (e)",
)
VETO = "veto"
TITULO_DISPERSION = "Exposición a renta variable vs % de renta variable"
EJE_X = "Exposición a renta variable (mdp, escala logarítmica)"
EJE_Y = "% de renta variable"
NOTA_BURBUJA = "Tamaño de burbuja = bolsa de comisión (punto medio de la banda). Un punto por fondo."
TITULO_NOTAS_COMPARATIVO = "Notas"
NOTAS_COMPARATIVO = (
    "Tier 1 ≥ {t1}; Tier 2 de {t2} a {t1_menos}; Tier 3 < {t2}.",
    "Regla de veto: con casa de bolsa hermana en el mismo grupo financiero, independencia de canal = 1 "
    "y la operadora no puede quedar en Tier 1.",
    "Bolsa de comisión = importe anual operado (exposición RV × rotación × 2) × comisión por mercado. "
    "Ingreso esperado = bolsa × captura objetivo × probabilidad de alta (e).",
    "Ajuste al servicio = 1 + 4 × proporción de la renta variable en acciones y FIBRAS en directo.",
    "Escalas: bolsa {esc_bolsa} mdp; rotación {esc_rot}x; headroom/exposición {esc_head}.",
)

# --------------------------------------------------------------- fragmentos con cifras
TOOLTIP_PUNTO = "{operadora} · {clave}: {rv} mdp RV, {pct}, bolsa {bolsa} mdp"
ITEM_DIRECTO = "{emisora} {monto} mdp ({clase})"
ITEM_FUERA = "{clave} — {motivo}"
NOTA_OPERADORA = "{operadora}: {texto}"
