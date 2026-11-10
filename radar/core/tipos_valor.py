"""Clave de tipo de valor (catálogo Indeval/CNBV) -> categoría de instrumento.

Lo comparten las carteras que publican la clave TV (Multiva) y el reporte R7 de la
CNBV. Una clave desconocida hace FALLAR: no se adivina.
"""
from __future__ import annotations

import re

from radar.core.modelo import Categoria


class TipoValorDesconocido(ValueError):
    pass


TV: dict[str, Categoria] = {
    "0": Categoria.ACCION_LOCAL,
    "1": Categoria.ACCION_LOCAL,
    "41": Categoria.ACCION_LOCAL,     # acciones bancarias
    "CF": Categoria.FIBRA,
    "1B": Categoria.ETF_LOCAL,        # títulos referenciados a acciones listados en México
    "1A": Categoria.ACCION_SIC,
    "1ASP": Categoria.ACCION_SIC,
    "1ESP": Categoria.ACCION_SIC,
    "1MSP": Categoria.ACCION_SIC,
    "1I": Categoria.ETF_EXTRANJERO,
    "1ISP": Categoria.ETF_EXTRANJERO,
    "51": Categoria.FONDO,
    "52": Categoria.FONDO,
    "53": Categoria.FONDO,
    # CNBV R7: "Sociedades de Inversión de Deuda Extranjera (Tipo de Cambio Spot)".
    # Fondo extranjero de deuda vía SIC: renta fija, no se transparenta (no es de la casa).
    "56SP": Categoria.DEUDA,
    "CHM": Categoria.DEPOSITO,        # cuenta de cheques moneda nacional
    "CHD": Categoria.DEPOSITO,        # cuenta de cheques en dólares
    "CHE": Categoria.DEPOSITO,        # cuenta de cheques en euros
    "CHL": Categoria.DEPOSITO,        # cuenta de cheques en libras
    "CHDK": Categoria.DEPOSITO,       # cuenta de cheques en corona danesa
    "AIM": Categoria.DEPOSITO,        # aportaciones iniciales mínimas (garantía en efectivo, MexDer)
    "EAIM": Categoria.DEPOSITO,       # aportaciones extraordinarias (garantía en efectivo)
    "1S": Categoria.ACCION_LOCAL,     # SAPIB listadas en BMV
    "00": Categoria.ACCION_LOCAL,     # acciones no susceptibles de negociación (valor ~0)
    "FF": Categoria.FIBRA,            # fideicomisos de inversión en infraestructura
    "FE": Categoria.FIBRA,            # fideicomisos de inversión en energía (FIBRA-E)
    "YYSP": Categoria.ACCION_SIC,     # ADRs cotizados en el SIC
    "2": Categoria.DEUDA,             # obligaciones
    "83": Categoria.DEUDA,            # deuda estructurada de corto plazo
    "JE": Categoria.DEUDA,            # notas estructuradas sin garantía total de principal
    "MP": Categoria.DEUDA,            # cupones segregados de Bonos M / Udibonos
    "MC": Categoria.DEUDA,
    "SC": Categoria.DEUDA,
    "SP": Categoria.DEUDA,
}

# Derivados: no caben en las cinco clases; se EXCLUYEN de la mezcla y su monto se
# reporta en las notas del fondo (catálogo CNBV R7).
TV_DERIVADOS = frozenset({"SWP", "SWPS", "FCSP", "FWDS", "FWD", "FD", "FA", "FI", "PUT", "CALL", "WSSP", "WS"})


def es_derivado(tv: str) -> bool:
    return str(tv).strip().lstrip("'") in TV_DERIVADOS
# Deuda gubernamental, bancaria y corporativa. Sufijo SP = versión cotizada en el SIC.
TV_DEUDA = re.compile(
    r"^(LF|LG|LD|IM|IQ|IS|BI|M|MS|S|2U|9\d|F|I|CD|D\d|JI|J|G|PI|R1|Q|71|73|75)(SP)?$"
)


def categoria_por_tv(tv: str, contexto: str, es_reporto: bool = False) -> Categoria:
    if es_reporto:
        return Categoria.REPORTO
    tv = str(tv).strip().lstrip("'")
    if tv in TV:
        return TV[tv]
    if TV_DEUDA.match(tv):
        return Categoria.DEUDA
    raise TipoValorDesconocido(
        f"Tipo de valor desconocido {tv!r} ({contexto}). Agrégalo a radar/core/tipos_valor.py."
    )
