"""Precio actual de referencia de una emisora (Yahoo Finance, gráfica pública; puede traer ~15 min
de retraso). Se consulta en vivo desde la app con caché; no entra al pipeline ni a los
entregables, que deben ser reproducibles.

Todo en pesos: la cotización en la BMV (sufijo .MX) para emisoras locales y del SIC; si el SIC no
tiene cotización reciente, la del mercado de origen en dólares por el tipo de cambio del día.

Ojo: no es el costo de los fondos. Ninguna fuente pública (CNBV R7, carteras de las operadoras,
DICI, prospectos, estados financieros) publica el costo promedio de adquisición; lo que sí hay es
el precio de mercado al corte (R7: valor unitario de mercado), contra el que se mide la variación.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

from radar.red import USER_AGENT

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=5d&interval=1d"
VIGENCIA = timedelta(days=7)   # una cotización más vieja se descarta (listado sin operación)


@dataclass(frozen=True)
class Cotizacion:
    simbolo: str
    precio_mxn: float
    hora: datetime
    fuente: str       # "BMV" | "origen (USD × tipo de cambio)"


def simbolos(emisora: str, serie: str, mercado: str) -> list[str]:
    """Candidatos en orden: WALMEX * -> WALMEX.MX; GFNORTE O -> GFNORTEO.MX; AAPL (SIC) -> AAPL.MX, AAPL."""
    e = emisora.strip().upper()
    s = (serie or "").strip().upper()
    if mercado == "México":
        return [f"{e}{'' if s in ('', '*') else s}.MX"]
    return [f"{e}.MX", e]


def _cotizar(simbolo: str, timeout: float) -> tuple[float, str, datetime] | None:
    try:
        r = requests.get(URL.format(s=simbolo), timeout=timeout, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return None
        m = (r.json().get("chart", {}).get("result") or [{}])[0].get("meta", {})
        precio, hora = m.get("regularMarketPrice"), m.get("regularMarketTime")
        if not precio or not hora:
            return None
        hora = datetime.fromtimestamp(hora, tz=timezone.utc)
        if datetime.now(timezone.utc) - hora > VIGENCIA:
            return None
        return float(precio), str(m.get("currency") or ""), hora
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None


def cotizacion(emisora: str, serie: str, mercado: str, tipo_cambio: float | None,
               timeout: float = 8) -> Cotizacion | None:
    for s in simbolos(emisora, serie, mercado):
        q = _cotizar(s, timeout)
        if q is None:
            continue
        precio, moneda, hora = q
        if moneda == "MXN":
            return Cotizacion(s, precio, hora, "BMV" if s.endswith(".MX") else "origen")
        if moneda == "USD" and tipo_cambio:
            return Cotizacion(s, precio * tipo_cambio, hora, "origen (USD × tipo de cambio)")
    return None


def tipo_cambio(timeout: float = 8) -> float | None:
    q = _cotizar("MXN=X", timeout)
    return q[0] if q else None


def cotizaciones(emisoras: list[tuple[str, str, str]], hilos: int = 16) -> dict[str, Cotizacion]:
    """{emisora: Cotizacion} para [(emisora, serie, mercado)]; las que no cotizan no aparecen."""
    tc = tipo_cambio()
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        res = ex.map(lambda x: (x[0], cotizacion(x[0], x[1], x[2], tc)), emisoras)
        return {k: q for k, q in res if q is not None}
