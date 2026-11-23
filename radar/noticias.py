"""Noticias recientes de una emisora (Google News RSS, en español de México y en inglés de EE. UU.).
Solo encabezados, fuente, fecha y liga a la nota original. Se consulta en vivo desde la app (con
caché corta, para que lo del día llegue rápido); no entra al pipeline ni a los entregables, que
deben ser reproducibles.

También arma el mensaje para el chat de Bloomberg: "He visto que en sus fondos traen posición en
Apple (AAPL); hoy salió una nota... Les comparto el link". El mensaje lo envía la persona: aquí
solo se redacta."""
from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

import requests

from radar.core.numeros import sin_acentos
from radar.red import USER_AGENT

RSS = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=MX&ceid=MX:es-419"
RSS_EN = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
MAX_BYTES = 2_000_000
TERMINOS = "acciones OR resultados OR bolsa OR inversionistas OR trimestre"
TERMINOS_EN = "stock OR shares OR earnings OR buyback OR investors OR guidance"
CDMX = timezone(timedelta(hours=-6))


@dataclass(frozen=True)
class Noticia:
    titulo: str
    fuente: str
    fecha: datetime | None
    liga: str
    idioma: str = "es"


def consulta(emisora: str, nombre: str, dias: int = 14) -> str:
    """Busca por nombre cuando se conoce (las claves cortas como AMX o R son ambiguas) y con
    términos bursátiles para dejar fuera notas de consumo (ofertas, lanzamientos)."""
    base = f'"{nombre}"' if nombre and not nombre.startswith("[") else f'"{emisora}"'
    return f"{base} ({TERMINOS}) when:{dias}d"


def url_busqueda(q: str) -> str:
    return "https://news.google.com/search?q=" + quote_plus(q) + "&hl=es-419&gl=MX&ceid=MX:es-419"


def parsear_rss(xml: bytes, n: int = 3) -> list[Noticia]:
    if len(xml) > MAX_BYTES:
        return []
    raiz = ET.fromstring(xml)
    out: list[Noticia] = []
    for it in raiz.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        fuente = (it.findtext("source") or "").strip()
        if fuente and titulo.endswith(" - " + fuente):
            titulo = titulo[: -len(" - " + fuente)]
        try:
            fecha = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            fecha = None
        liga = (it.findtext("link") or "").strip()
        if titulo and liga.startswith("https://"):
            out.append(Noticia(titulo, fuente, fecha, liga))
    out.sort(key=lambda x: (x.fecha is None, -(x.fecha.timestamp() if x.fecha else 0)))
    return out[:n]


RUTA_ALIAS = Path(__file__).parent / "core" / "datos" / "alias_noticias.csv"
#: Palabras del nombre legal que no identifican a la emisora por sí solas.
GENERICAS = {
    "grupo", "financiero", "corporacion", "corporativo", "inmobiliaria", "mexico", "industrias", "industrial",
    "promotora", "operadora", "infraestructura", "aeroportuario", "pacifico", "sureste", "centro", "norte",
    "comercial", "organizacion", "consorcio", "controladora", "empresas", "nacional", "provincial", "advance",
    "platforms", "technology", "semiconductor", "materials", "networks", "health", "surgical", "research",
    "pacific", "express", "american", "union", "foods", "minera", "banco", "fibra", "interamericana",
    "entretenimiento", "mexicano", "desarrollo", "cementos", "regional", "puerto", "chase", "holdings",
    # marcas de la matriz extranjera: "Walmart" a secas es la de EE. UU., no Walmex
    "walmart", "kimberly-clark", "coca-cola",
}
#: Encabezados que nombran a la emisora pero no son de la empresa (estadios, deportes, eventos).
EXCLUIR = re.compile(r"\b(estadio|stadium|nfl|liga mx|futbol|football|partido|gol|concierto|boletos|"
                     r"telenovela|serie de tv|en vivo|live score|premier league|champions|vs\.?)\b", re.I)
#: Páginas de cotización automáticas que Google indexa como nota.
RUIDO = re.compile(r"cotizaci[oó]n e historial|precio de la acci[oó]n de|gr[aá]fico y an[aá]lisis|"
                   r"stock price, news|stock forecasts?|price forecast|quote shifts|"
                   r"TSXV:|CSE:|ASX:", re.I)
#: Términos bursátiles: esas notas van primero.
BURSATIL = re.compile(
    r"\b(acci[oó]n(es)?|stock|shares?|resultados|earnings|ingresos|revenue|utilidad|ganancias?|profit|"
    r"dividendo|dividend|recompra|buyback|repurchase|guidance|perspectiva|precio objetivo|price target|"
    r"upgrade|downgrade|calificaci[oó]n|rating|trimestre|quarter|bmv|bolsa|emisi[oó]n|bono|deuda|debt|"
    r"adquisici[oó]n|acquisition|acquire|compra de|fusi[oó]n|merger|inversi[oó]n|invest|sube|baja|cae|"
    r"rises?|falls?|jumps?|drops?|surges?|plunges?|record|r[eé]cord|ipo|oferta)\b", re.I)


@lru_cache(maxsize=1)
def _alias_csv() -> dict[str, list[str]]:
    with RUTA_ALIAS.open(encoding="utf-8") as fh:
        filas = csv.DictReader(l for l in fh if not l.startswith("#"))
        return {r["ticker"].strip(): [a.strip() for a in r["alias"].split("|") if a.strip()] for r in filas}


def alias(emisora: str, nombre: str) -> list[str]:
    """Nombres con los que la emisora aparece en un encabezado (del más largo al más corto)."""
    manual = _alias_csv().get(emisora, [])
    out = set(manual)
    if nombre and not nombre.startswith("["):
        limpio = re.sub(r"\(.*?\)", "", nombre).strip()
        out.add(limpio)
        # Palabras sueltas del nombre solo si no hay alias definidos (evita "América", "Móvil")
        for t in [] if manual else re.findall(r"[\w&'.-]+", limpio):
            if len(t) >= 4 and sin_acentos(t).lower() not in GENERICAS:
                out.add(t)
    if len(emisora) >= 3 and emisora.isalpha():
        out.add(emisora)
    return sorted(out, key=lambda a: (-len(a), a))


def menciona(titulo: str, nombres: list[str]) -> bool:
    """El encabezado nombra a la emisora (palabra completa, sin acentos, respetando mayúsculas)."""
    t = sin_acentos(titulo)
    return any(re.search(r"(?<![\w])" + re.escape(sin_acentos(a)) + r"(?![\w])", t) for a in nombres)


def consulta_idioma(emisora: str, nombre: str, idioma: str, dias: int) -> str:
    nombres = alias(emisora, nombre)[:4] or [emisora]
    base = "(" + " OR ".join(f'"{a}"' for a in nombres) + ")"
    terminos = TERMINOS if idioma == "es" else TERMINOS_EN
    return f"{base} ({terminos}) when:{dias}d"


def _rss(url: str, timeout: float, n: int, idioma: str) -> list[Noticia]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return []
        return [Noticia(x.titulo, x.fuente, x.fecha, x.liga, idioma) for x in parsear_rss(r.content, n)]
    except (requests.RequestException, ET.ParseError):
        return []


def recientes(emisora: str, nombre: str, horas: int = 24, idiomas: tuple[str, ...] = ("es", "en"),
              n: int = 5, timeout: float = 8, ahora: datetime | None = None, mercado: str = "") -> list[Noticia]:
    """Notas de las últimas `horas` cuyo encabezado nombra a la emisora: primero las bursátiles,
    luego por hora; sin repetir encabezado. En inglés, una emisora mexicana no cuenta por su clave
    sola (AMX, GAP, R chocan con otras empresas)."""
    ahora = ahora or datetime.now(timezone.utc)
    dias = max(1, -(-horas // 24))
    out: list[Noticia] = []
    for idioma in idiomas:
        url = (RSS if idioma == "es" else RSS_EN).format(q=quote_plus(consulta_idioma(emisora, nombre, idioma, dias)))
        out += _rss(url, timeout, 20, idioma)
    nombres = alias(emisora, nombre)
    sin_clave = [a for a in nombres if a != emisora] or nombres
    vistos, filtradas = set(), []
    for x in sorted(out, key=lambda x: -(x.fecha.timestamp() if x.fecha else 0)):
        k = x.titulo.lower()[:80]
        validos = sin_clave if (mercado == "México" and x.idioma == "en") else nombres
        if (x.fecha and ahora - x.fecha <= timedelta(hours=horas) and k not in vistos
                and menciona(x.titulo, validos) and not EXCLUIR.search(x.titulo) and not RUIDO.search(x.titulo)):
            vistos.add(k)
            filtradas.append(x)
    filtradas.sort(key=lambda x: (not es_bursatil(x), -x.fecha.timestamp()))
    return filtradas[:n]


def es_bursatil(x: Noticia) -> bool:
    return bool(BURSATIL.search(x.titulo))


def recientes_varias(emisoras: list[tuple[str, str, str]], horas: int = 24, hilos: int = 16) -> dict[str, list[Noticia]]:
    """{emisora: notas} para [(emisora, nombre, mercado)], en paralelo."""
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        return dict(ex.map(lambda x: (x[0], recientes(x[0], x[1], horas, mercado=x[2])), emisoras))


def cuando(fecha: datetime | None, ahora: datetime | None = None) -> str:
    """'Hoy' / 'Ayer' / 'El 18/11' en hora de la Ciudad de México."""
    if fecha is None:
        return "Recientemente"
    hoy = (ahora or datetime.now(timezone.utc)).astimezone(CDMX).date()
    d = fecha.astimezone(CDMX).date()
    return "Hoy" if d == hoy else "Ayer" if (hoy - d).days == 1 else f"El {d:%d/%m}"


def hace(fecha: datetime | None, ahora: datetime | None = None) -> str:
    if fecha is None:
        return ""
    m = int(((ahora or datetime.now(timezone.utc)) - fecha).total_seconds() // 60)
    return f"hace {max(m, 1)} min" if m < 60 else f"hace {m // 60} h" if m < 48 * 60 else f"hace {m // 1440} días"


def mensaje_bloomberg(nombre: str, emisora: str, fondos: list[str] | tuple[str, ...], nota: Noticia,
                      ahora: datetime | None = None) -> str:
    """Mensaje corto para el chat de Bloomberg (lo envía la persona, no la app)."""
    quien = f"{nombre} ({emisora})" if nombre and not nombre.startswith("[") and nombre != emisora else emisora
    fondos = list(fondos)
    if len(fondos) == 1:
        donde = f"en su fondo {fondos[0]} traen"
    elif fondos:
        lista = ", ".join(fondos[:3]) + (f" y {len(fondos) - 3} más" if len(fondos) > 3 else "")
        donde = f"en sus fondos ({lista}) traen"
    else:
        donde = "en sus fondos traen"
    fuente = f" en {nota.fuente}" if nota.fuente else ""
    return (f"Buen día. He visto que {donde} posición en {quien}. {cuando(nota.fecha, ahora)} salió una nota"
            f"{fuente}: “{nota.titulo}”. Les comparto el link por si es de su interés revisarla a detalle: "
            f"{nota.liga}")


def noticias(emisora: str, nombre: str, n: int = 3, timeout: float = 8) -> list[Noticia]:
    """Lista vacía si el servicio no responde: la app muestra entonces solo la liga de búsqueda."""
    try:
        r = requests.get(RSS.format(q=quote_plus(consulta(emisora, nombre))), timeout=timeout,
                         headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return []
        return parsear_rss(r.content, n)
    except (requests.RequestException, ET.ParseError):
        return []
