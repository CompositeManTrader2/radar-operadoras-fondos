"""Formato de cifras: millones de pesos con separador de miles, % y pb."""
from __future__ import annotations

from html import escape


def mdp(pesos: float, dec: int = 1) -> str:
    v = pesos / 1_000_000
    s = f"{v:,.{dec}f}"
    return "0.0" if s in ("-0.0", "-0") else s


def pct(x: float | None, dec: int = 1) -> str:
    return "—" if x is None else f"{x * 100:.{dec}f}%"


def pb(x: float) -> str:
    return f"{x:g}"


def veces(x: float) -> str:
    return f"{x:.2f}x"


def banda(lo: float, hi: float, fmt=veces) -> str:
    return f"{fmt(lo)}–{fmt(hi)}"


def e(s: str) -> str:
    return escape(s, quote=True)
