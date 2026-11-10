# Especificación original del radar (brief de la mesa de capitales)

Proyecto: radar de operadoras de fondos para la mesa de capitales de Punto Casa de Bolsa.
Fin comercial: decidir a qué operadoras dedicar cobertura porque rotan renta variable
que la mesa puede ejecutar.

## Glosario
- BMV / BIVA: bolsas mexicanas ("mercado local").
- SIC: Sistema Internacional de Cotizaciones; mercado distinto al local (otra comisión).
- DICI: ficha regulatoria (objetivo, régimen con límites mín./máx., comisiones, liquidez, plazo de liquidación).
- Cartera de valores: PDF mensual con posiciones a fin de mes. Fuente primaria.
- Régimen = lo que el fondo PUEDE tener. Composición efectiva = lo que TIENE. Nunca mezclarlos ni usar uno para estimar el otro.
- pb: 0.01 %. Fondo de fondos: su cartera son acciones de otros fondos (normalmente de la misma operadora).

## Universo y prioridad
1. Operadoras SIN casa de bolsa hermana. 2. Con renta variable en directo, no solo ETFs. 3. Tamaño.
Agregar una operadora = escribir un adaptador nuevo, no tocar el núcleo.

## Parseo
pdfplumber / pdftotext -layout, nunca pypdf. Reconstruir filas por coordenada Y y ordenar por X
(los DICI tienen una columna por serie; extraer en orden plano intercala series: bug silencioso).

## Clasificación (reglas duras)
Clases: RV_LOCAL (BMV/BIVA, FIBRAS, ETFs listados en México), RV_SIC (acciones extranjeras en
directo), RV_ETF (ETFs con subyacente RV), RF (deuda y ETFs con subyacente deuda), EFE (reportos y
depósitos a la vista). Un ETF se clasifica por subyacente (diccionario versionado; el parser FALLA
ante un ETF sin clasificar). Reportos = efectivo. Emisora canónica (FEMSA UBD = 1_FEMSA_UBD =
1ASP_FEMSA) guardando emisora_raw. Clave SIC dudosa => [POR CONFIRMAR].

## Métricas
- exposicion_rv = activo_neto × %RV; reparto local/SIC (transparencia en fondos de fondos)
- headroom = (límite máximo RV del régimen − %RV actual) × activo_neto
- importe_anual = exposicion_rv × rotación × 2 (compra y venta)
- bolsa_comision = importe_local × COMISION_LOCAL + importe_sic × COMISION_SIC
- ingreso_esperado = bolsa × CAPTURA_OBJETIVO × probabilidad_de_alta
- Parámetros: COMISION_LOCAL 15 pb, COMISION_SIC 25 pb, CAPTURA_OBJETIVO 15 %.

Rotación observada (piso, no rotación real): comparar TÍTULOS por emisora entre dos cortes, valorar
cada delta al precio implícito del corte posterior (valor/títulos), compras = Σ deltas > 0,
ventas = Σ |deltas < 0|, rotación anual ≈ ((compras + ventas)/2) / activo_neto × 12/meses.
Con menos de 6 cortes reportar banda, nunca cifra puntual.

Calificación por operadora (1 a 5): bolsa de comisión 30 % | independencia de canal 25 % | ajuste al
servicio 20 % | recurrencia del flujo 10 % | headroom y momentum 10 % | fricción de alta 5 %.
Tier 1 ≥ 4.0, Tier 2 de 3.0 a 3.9, Tier 3 < 3.0. Veto: casa de bolsa hermana => independencia = 1 y
no puede ser Tier 1.

## Entregables
One-pager HTML autocontenido por operadora (encabezado; 6 indicadores; 2 donas; tabla de fondos con
barra de mezcla; top 20 RV y top 20 RF; pie con metodología, supuestos (e), huecos [POR CONFIRMAR] y
fuente) y comparativo (tabla de calificación con 6 criterios; dispersión exposición RV log vs %RV,
burbuja = bolsa, color = operadora). Excluir fondos de fondos y decirlo, mencionando activos en
directo que se van. Paleta #512D6D, #00857D, #919AA2, #3C444D, #F1F2F4. Archivo + IBM Plex Mono,
tabular-nums. Tema claro/oscuro (encabezado se oscurece). Español con acentos, millones de pesos con
separador de miles, comisiones en pb. Regla de actualización: un corte nuevo sale idéntico salvo
cifras; texto fijo en un módulo de plantillas.

## Criterios de aceptación
- Suma de posiciones = total de cartera publicado (±0.1 %) o el pipeline falla y dice qué fondo.
- Ningún ETF sin clasificar.
- Toda cifra rastreable a (documento, página, fecha).
- Dos documentos del mismo fondo que discrepen > 10 %: mostrar ambos y marcar; no promediar.
- Tests con PDFs reales como fixtures, uno por operadora.
- Mismo corte dos veces => mismo HTML.

## Ampliación (2026-11-10)
Plataforma Streamlit con actualización automática periódica; muchas operadoras adicionales;
revisión de que todo el modelo sea correcto; repositorio en GitHub (CompositeManTrader2, privado).
