"""Noticias recientes de una emisora (Google News RSS, español de México). Solo encabezados,
fuente, fecha y liga a la nota original. Se consulta en vivo desde la app (con caché);
no entra al pipeline ni a los entregables, que deben ser reproducibles."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

from radar.red import USER_AGENT

RSS = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=MX&ceid=MX:es-419"
MAX_BYTES = 2_000_000
TERMINOS = "acciones OR resultados OR bolsa OR inversionistas OR trimestre"


@dataclass(frozen=True)
class Noticia:
    titulo: str
    fuente: str
    fecha: datetime | None
    liga: str


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
