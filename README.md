# Radar de operadoras de fondos

Levanta mes a mes la cartera real de los fondos de inversión de operadoras mexicanas,
guarda el histórico de cortes y produce un one-pager HTML por operadora más un
comparativo. Fin comercial: decidir a qué operadoras dedicar cobertura de la mesa de
capitales porque rotan renta variable ejecutable.

## Plataforma

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Diseño institucional de Punto Casa de Bolsa (logotipo, morado de la marca, Ubuntu y Open Sans), sin barra
lateral: navegación superior con cinco páginas.

- **Panorama:** indicadores generales, calificación por operadora (gráfica y ranking; un clic en un renglón
  abre su ficha), mapa de exposición por fondo y tabla completa con los seis criterios.
- **Operadora:** ficha con calificación, tier y casa de bolsa hermana, indicadores y pestañas *Resumen*
  (composición y cómo se forma la calificación), *Qué enviarle* (research, noticias e ideas según su cartera),
  *Fondos*, *Posiciones* y *One-pager* (vista y descarga del HTML).
- **Fondo:** posiciones con su fuente, rotación por tramo, DICI e historia.
- **Estado de los datos:** resultado de la última corrida, ETFs pendientes, documentos y conciliaciones.
- **Metodología.**

Los supuestos de comisión se ajustan con el botón *Supuestos* y solo afectan la sesión; los permanentes están
en `config/parametros.toml`.

**Despliegue (Streamlit Community Cloud):** share.streamlit.io → *New app* → este repositorio, rama
`main`, archivo `streamlit_app.py`. Al ser privado, Streamlit pide autorizar el acceso a la cuenta de
GitHub. Cada commit de la tarea programada vuelve a desplegar la app con los datos nuevos.

## Actualización automática

`.github/workflows/actualizar.yml` corre `python -m radar actualizar` **en los servidores de GitHub**
(no depende de ninguna PC) de lunes a viernes a las 07:17 y a las 15:17 (CDMX; la segunda es respaldo)
y también a mano (*Actions → actualizar-radar → Run workflow*). Descarga todo, re-parsea, valida y
genera entregables; solo hace commit si llegó un documento nuevo o cambió el estado de una operadora
(`data/estado.txt`). Una operadora que falla (sitio caído, formato nuevo, ETF sin clasificar) queda
registrada en "Estado de los datos" y no detiene a las demás. Los DICI de las híbridas se revisan cada
7 días; sus PDF y la caché de extracción viven en la caché de Actions (si se pierde, se vuelven a bajar).

- **CNBV:** su servidor no envía el certificado intermedio (GlobalSign RSA OV SSL CA 2018); va en
  `config/certs/` y se suma a los raíces de certifi (la verificación TLS sigue completa). Si la CNBV
  cambia de certificadora, agregar ahí el nuevo intermedio público.
- **Finaccess** no responde a IPs fuera de México: desde GitHub se usan sus documentos guardados y la
  cartera de la CNBV (aviso en el estado). Su cartera mensual propia requiere una IP mexicana.
- Hasta el 2026-11-11 corría en un *self-hosted runner* de la PC (`radar-pc-mx`, en
  `%USERPROFILE%\actions-runner-radar`); ya no se usa. Quitarlo: `config.cmd remove --token <token>` en esa
  carpeta (token en *Settings → Actions → Runners*).

## Uso

```
pip install -e .[dev]
python -m radar discover --operadora finaccess
python -m radar fetch    --operadora todas            # descarga fechada + parseo + validación
python -m radar render   --operadora finaccess --corte latest
python -m radar metrics  --operadora multiva --corte latest > metricas.csv
python -m radar compare  --cortes 2026-09-30,2026-10-31
python -m pytest
```

`fetch --corte AAAA-MM-DD` falla con código 2 si el sitio ya no publica ese corte: las
operadoras sobrescriben el mismo URL cada mes y no hay archivo histórico. Por eso
**hay que correr `fetch` cada mes**: el store es la única serie.

Salidas en `salidas/`, datos en `data/` (`raw/` con cada PDF fechado por sha256,
`radar.sqlite` con el histórico, `cache/` reconstruible).

## Arquitectura

```
radar/
  fuentes/    fuentes transversales: cnbv.py (R1 activo neto, R7 cartera de todos los fondos)
  adapters/   un módulo por operadora (descubre documentos y parsea): finaccess, multiva, compass
              + formatos compartidos: formato_publicaciones (cartera Multiva/Compass),
                formato_dici (DICI de plantilla Finaccess/Compass), base (tablas y validaciones)
  core/       modelo, reconstrucción de filas por coordenadas, clasificación, métricas, validación
              datos/etfs.csv (diccionario versionado de ETFs), datos/claves_sic.csv
  store/      SQLite: clave operadora + fondo + fecha_corte
  render/     plantillas.py (TODO el texto fijo), formato, SVG, HTML
  cli.py      discover | fetch | parse | metrics | render | compare
config/parametros.toml  comisiones, umbrales, pesos, supuestos por operadora (e)
```

Agregar una operadora = un módulo en `radar/adapters/` que implemente `Adaptador`
(`descubrir`, `fecha_documento`, `parsear_cartera`, `parsear_dici`, `perfil`) y una
línea en `radar/adapters/__init__.py`. Los helpers de tablas de DICI
(`serie_portada`, `comisiones_del_fondo`, `regimen_prospecto`) están en `base.py`.

## Reglas que el código hace cumplir

- Filas reconstruidas por coordenada Y con tolerancia y ordenadas por X (pdfplumber;
  nunca pypdf). Columnas del DICI asignadas por la X de su encabezado de serie, y los
  componentes de comisión deben sumar el Total publicado: si no, falla ("posible
  intercalado").
- Cuadre: suma de posiciones vs total publicado, tolerancia 0.1 %; si no cuadra, el
  pipeline falla y nombra el fondo.
- Tipo de instrumento o tipo de valor desconocido => falla. ETF fuera de
  `core/datos/etfs.csv` => falla. Reportos = efectivo.
- Fondos de fondos (≥ 50 % en acciones de otros fondos) excluidos y declarados en el pie,
  con los activos en directo que se van con ellos.
- Multiva: el prospecto genérico decide qué fondos administra; lo demás es NO DISPONIBLE.
- Mismo corte => mismo HTML byte a byte. Texto fijo solo en `render/plantillas.py`.

## Cobertura

- **Adaptador propio** (cartera y DICI de la operadora, más CNBV): Finaccess, Multiva, Vinci Compass.
- **Híbridas** (cartera y activo neto por la CNBV; DICI y prospecto del sitio de la operadora, en
  `radar/adapters/dici/`): las seis más grandes sin casa de bolsa propia. Aportan régimen, comisiones,
  liquidez y distribuidoras; si una distribuidora es casa de bolsa del mismo grupo, el perfil lo marca
  como hermana aunque el padrón diga lo contrario (DISCREPANCIA). Un DICI ilegible o no publicado es
  aviso, no error: la operadora sigue con la cartera de la CNBV.

  | Operadora | DICI (2026-11-10) | Fuente |
  |---|---|---|
  | BlackRock México | 31 de 40 | blackrock.com y, de respaldo, la copia de Citi (distribuidor) |
  | SURA IM México | 35 de 36 | API JSON de la página de rendimientos (PDF en base64) |
  | Principal | 20 de 20 | alias fijos `principal.com.mx/{CLAVE}-DICI` |
  | Franklin Templeton | 11 de 11 | JSON público de documentos (URL de Widen no predecible) |
  | Skandia | 5 de 5 | blob público con la clave en la ruta |
  | Nafinsa | 13 de 13 | fichas del sitio (`fund:detail`); un DICI por tipo de adquirente, se toma el de personas físicas |

  Ninguna lista una casa de bolsa propia: distribuyen por Citi/Banamex, Actinver, GBM, Monex, Multiva,
  Ve por Más, etc.; Nafinsa y Skandia solo se listan a sí mismas. El sitio de Nafinsa a veces deja
  colgada la primera conexión: los reintentos del cliente HTTP la resuelven (no hace falta navegador).
- **Cobertura CNBV** (R7 cartera mensual + R1 activo neto, ~45 días de rezago, sin DICI): las otras 20
  operadoras del padrón, definidas en `config/operadoras_cnbv.toml` con su casa de bolsa hermana según el
  padrón CNBV. Su régimen queda [POR CONFIRMAR] y, mientras su rotación no esté medida (necesita dos
  meses de R7), su calificación es **provisional** y no puede ser Tier 1.
- Agregar DICI a una operadora CNBV: subclase de `AdaptadorCnbvConDici` en `radar/adapters/dici/` con
  `documentos(cliente, claves)` (y `bajar()` si el PDF no se baja con un GET) y una línea en `CLASES`.
- Pasar una operadora a adaptador propio: módulo en `radar/adapters/`, línea en `__init__.py` y quitarla
  del TOML. Si la clave del fondo en la CNBV difiere de la de la operadora, va en `config/alias_fondos.toml`
  (el pipeline avisa cuando detecta un traslape de posiciones >= 90 %).

## Operadoras

| Clave | Operadora | Casa de bolsa hermana | Cartera | DICI | CNBV |
|---|---|---|---|---|---|
| finaccess | Finaccess México | No | propio (URLs fijas) | plantilla | FACCESS |
| multiva | Fondos de Inversión Multiva | Sí (veto) | Publicaciones | propio | OPMULTI |
| compass | Vinci Compass | No | Publicaciones | plantilla | SEICOMP |

## Decisiones a revisar

- **Rotación**: el denominador es la exposición promedio a renta variable (no el activo
  neto total) para que `importe = exposición RV × rotación × 2` sea consistente; en fondos
  de RV es casi idéntico. Solo se comparan posiciones de RV con títulos; los renglones
  agregados de Multiva ("OTROS TIPO DE VALOR") no se pueden seguir.
- **Finaccess "cartera diaria"** (`cartera_<clave>.pdf`) está congelada en otro corte
  (10-sep-2026 al momento de construir esto). Se guarda como corte adicional y da la
  primera medición de rotación; el one-pager usa siempre el corte mensual.
- **CNBV (`radar/fuentes/cnbv.py`)**: `fetch` descarga el R7 (cartera mensual de todos los
  fondos) y el R1 (activo neto diario) vigentes. Cada archivo publicado trae UN solo
  periodo con ~45 días de rezago y sobrescribe el URL, así que también se guardan
  fechados. R7 entra como corte cuando no hay cartera de la operadora de ese mes (si la
  hay, solo concilia); R1 sustituye el activo neto estimado cuando coincide la fecha. Las
  macros de los .xlsm nunca se ejecutan (openpyxl en modo datos). R7 no publica total: su
  cuadre es la conciliación contra R1 (‡ si difiere más de 10 %), no la regla de 0.1 %.
- **Multiva y Vinci Compass no publican activo neto**: en el corte de la operadora se usa el total de
  cartera (e), calibrado contra el último R1 disponible (−0.3 % a +1.8 % al 31-ago-2026).
- **Rotación encadenada**: el piso suma los tramos consecutivos
  (Σ operado/2 entre Σ exposición × meses/12); tramos de más de `MAX_MESES_PAR` meses no
  cuentan. Si un corte agrupa un tipo de valor en renglones sin emisora (Multiva) y el
  otro lo desglosa (R7), esas emisoras se ignoran en vez de contarse como compras/ventas.
- **Vinci Compass**: publica con un mes más de rezago (corte 30-sep cuando las otras ya
  publicaron 30-oct); `compare` usa el último corte de cada operadora <= la fecha pedida.
  Sus DICI listan a Casa de Bolsa Ve por Más, GBM y Credit Suisse como distribuidoras
  (terceros, no hermanas). Su prospecto tiene la tabla de régimen con valores apilados en
  otra columna: si el máximo leído es menor que la RV que el fondo tiene, la lectura se
  descarta ([POR CONFIRMAR]); hoy pasa en BX+4, CRECE+ y RVMAX1.
- **Texto encimado en el PDF** (I+LIQG): un renglón agregado traía la etiqueta encima de
  las cifras; se rescatan por carácter y se validan contra el % publicado.
- **DICI inconsistentes del emisor** (I+USD serie B-FC): si una serie no cuadra y las demás
  de la misma tabla sí, se conserva el Total publicado y se reporta con ‡.
- **Formatos de DICI y prospecto de las híbridas**: comisiones sin "%" y series entre comillas
  (BlackRock); distribuidoras separadas por " / " o por comas, cortadas donde empieza la columna de
  advertencias; tablas de régimen por incisos "a." con las cifras en un renglón propio; tablas con una
  columna por año (LifePath / fecha objetivo) no se leen ([POR CONFIRMAR]). Si un fondo de deuda (ID..)
  sale con RV en su régimen (TEMGBIA: acciones de un fondo de bonos), se descarta. pdfminer no
  implementa el cmap TrueType formato 12: se trata como "sin cmap" y se usa el ToUnicode del PDF.
- **ETFs de materia prima** (GLD): no son RV ni deuda; se cuentan en RV_ETF y se marcan (e).
- Supuestos comerciales (probabilidad de alta, fricción) en `config/parametros.toml`.

## Revisión del modelo (2026-11-10)

Auditoría independiente en `docs/revision_modelo.md` (21 hallazgos). Corregidos: alias de claves
CNBV ↔ operadora (AXESCSD = AXESCOB, TAURUM = BX+USD); calificación provisional sin rotación medida;
tenencias en fondos hermanos excluidas (sin doble conteo); momentum mensual con los mismos fondos;
la rotación media no salta al llegar a 6 cortes y solo cuentan cortes mensuales; ventas seguras con
renglones agregados; base mínima de 1 % del activo para medir rotación; llave de conciliaciones
separada por fuente; aviso de R7 parcial; headroom solo sobre fondos con régimen; sin redondeo antes
del umbral de tier; ETFs de materia prima en una sola clase. Pendientes conscientes: reparto local/SIC
por tenencia y no por lo operado, control de splits/eventos corporativos, y un solo tramo mensual
anualizado (Compass) que pesa mucho en la bolsa mientras no haya más cortes.

ETFs: `radar/core/datos/etfs.csv` (549 tickers) con fuente y confianza; los de confianza media se listan
como hueco en el pie de cada operadora.
