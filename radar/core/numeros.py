"""Lectura de cifras y fechas en formato mexicano."""
from __future__ import annotations

import re
import unicodedata
from datetime import date

RE_MONTO = re.compile(r"^-?\$?\d{1,3}(,\d{3})*(\.\d+)?$|^-?\$?\d+(\.\d+)?$")
RE_ENTERO = re.compile(r"^\d{1,3}(,\d{3})*$|^\d+$")
RE_PCT = re.compile(r"^-?\d+(\.\d+)?\s?%$")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def es_monto(s: str) -> bool:
    return bool(RE_MONTO.match(s))


def es_entero(s: str) -> bool:
    return bool(RE_ENTERO.match(s))


def es_pct(s: str) -> bool:
    return bool(RE_PCT.match(s))


def monto(s: str) -> float:
    return float(s.replace("$", "").replace(",", ""))


def pct(s: str) -> float:
    """'4.47%' -> 0.0447"""
    return float(s.replace("%", "").strip()) / 100


def mes_a_numero(nombre: str) -> int:
    return MESES[sin_acentos(nombre).lower().strip(" ,.")]


def fecha_es(dia: str, mes: str, anio: str) -> date:
    return date(int(anio), mes_a_numero(mes), int(dia))
