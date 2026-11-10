"""Clasificación con reglas duras. Cada posición cae en exactamente una clase.

- Un ETF se clasifica por subyacente, nunca por ser ETF. ETF sin diccionario => falla.
- Los reportos son efectivo, no deuda.
- Las acciones de otros fondos no reciben clase aquí: se transparentan en métricas.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from radar.core.modelo import (
    EFE, MERCADO_LOCAL, MERCADO_SIC, POR_CONFIRMAR, RF, RV_ETF, RV_LOCAL, RV_SIC,
    Cartera, Categoria, Posicion,
)

DIR_DATOS = Path(__file__).resolve().parent / "datos"


class EtfNoClasificado(ValueError):
    pass


class ErrorClasificacion(ValueError):
    pass


def _leer_csv(nombre: str) -> list[dict[str, str]]:
    lineas = [
        l for l in (DIR_DATOS / nombre).read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.lstrip().startswith("#")
    ]
    return list(csv.DictReader(lineas))


@lru_cache(maxsize=1)
def diccionario_etfs() -> dict[str, str]:
    d: dict[str, str] = {}
    for r in _leer_csv("etfs.csv"):
        sub = r["subyacente"].strip().upper()
        if sub not in ("RV", "DEUDA", "MATERIA_PRIMA"):
            raise ValueError(f"etfs.csv: subyacente inválido para {r['ticker']}: {sub}")
        t = r["ticker"].strip().upper()
        if t in d:
            raise ValueError(f"etfs.csv: ticker duplicado {t}")
        d[t] = sub
    return d


@lru_cache(maxsize=1)
def etfs_confianza_media() -> frozenset[str]:
    """ETFs clasificados con fuente secundaria: se listan como hueco por verificar."""
    return frozenset(r["ticker"].strip().upper() for r in _leer_csv("etfs.csv")
                     if r.get("confianza", "alta").strip().lower() != "alta")


@lru_cache(maxsize=1)
def version_diccionario_etfs() -> str:
    for l in (DIR_DATOS / "etfs.csv").read_text(encoding="utf-8").splitlines():
        if l.startswith("# version:"):
            return l.split(":", 1)[1].strip()
    return "s/v"


@lru_cache(maxsize=1)
def nombres_sic() -> dict[str, str]:
    return {r["clave"].strip().upper(): r["nombre"].strip() for r in _leer_csv("claves_sic.csv")}


def nombre_emisora_sic(clave: str) -> str:
    return nombres_sic().get(clave.upper(), POR_CONFIRMAR)


def canonica(emisora: str) -> str:
    """Clave canónica de emisora para concentración.

    Acepta la emisora ya separada ("FEMSA") o crudos como "1_FEMSA_UBD",
    "1ASP_FEMSA" o "FEMSA UBD": en todos los casos devuelve "FEMSA".
    """
    s = emisora.strip().upper()
    if "_" in s:
        partes = s.split("_")
        s = partes[1] if len(partes) >= 2 else partes[0]
    elif " " in s:
        s = s.split()[0]
    return s.strip(" *")


def subyacente_etf(ticker: str, contexto: str) -> str:
    t = canonica(ticker)
    d = diccionario_etfs()
    if t not in d:
        raise EtfNoClasificado(
            f"ETF '{t}' sin clasificar en radar/core/datos/etfs.csv ({contexto}). "
            "Agrégalo con su subyacente (RV o DEUDA); no se adivina."
        )
    return d[t]


def _clase_agregado_etf(p: Posicion, c: Cartera, referencia: Cartera | None, contexto: str) -> None:
    """Renglón agregado de ETFs sin ticker ("OTROS TIPO DE VALOR 1ISP"): no se puede
    clasificar por subyacente. Se infiere de la cartera de referencia del mismo fondo
    (CNBV R7, desglosada): los ETFs del mismo tipo de valor que ahí aparecen y aquí no.
    Solo si todos comparten subyacente; si no, falla."""
    if referencia is None:
        raise EtfNoClasificado(f"Renglón agregado de ETFs sin cartera de referencia para inferir el subyacente ({contexto})")
    aqui = {canonica(x.emisora) for x in c.posiciones if not x.es_agregado}
    d = diccionario_etfs()
    subs = {d.get(canonica(x.emisora), "?") for x in referencia.posiciones
            if x.tipo_valor == p.tipo_valor and not x.es_agregado and canonica(x.emisora) not in aqui}
    if len(subs) != 1 or "?" in subs:
        raise EtfNoClasificado(
            f"Renglón agregado de ETFs: la referencia {referencia.procedencia.cita()} no permite inferir "
            f"un subyacente único ({sorted(subs)}) ({contexto})"
        )
    sub = subs.pop()
    if p.categoria is Categoria.ETF_LOCAL:
        p.clase, p.mercado = (RF if sub == "DEUDA" else RV_LOCAL), MERCADO_LOCAL
    else:
        p.clase, p.mercado = (RF if sub == "DEUDA" else RV_ETF), MERCADO_SIC
    p.nota = f"Agregado de ETFs: subyacente {sub} inferido de {referencia.procedencia.cita()} (e)"


def clasificar_posicion(p: Posicion, contexto: str) -> None:
    p.emisora_canonica = canonica(p.emisora)
    c = p.categoria
    if c in (Categoria.ACCION_LOCAL, Categoria.FIBRA):
        p.clase, p.mercado = RV_LOCAL, MERCADO_LOCAL
    elif c is Categoria.ETF_LOCAL:
        sub = subyacente_etf(p.emisora, contexto)
        p.clase, p.mercado = (RF if sub == "DEUDA" else RV_ETF if sub == "MATERIA_PRIMA" else RV_LOCAL), MERCADO_LOCAL
        if sub == "MATERIA_PRIMA":
            p.nota = "ETF de materia prima: contado en RV_ETF (e)"
    elif c is Categoria.ACCION_SIC:
        p.clase, p.mercado = RV_SIC, MERCADO_SIC
    elif c is Categoria.ETF_EXTRANJERO:
        sub = subyacente_etf(p.emisora, contexto)
        p.clase, p.mercado = (RF if sub == "DEUDA" else RV_ETF), MERCADO_SIC
        if sub == "MATERIA_PRIMA":
            p.nota = "ETF de materia prima: contado en RV_ETF (e)"
    elif c is Categoria.DEUDA:
        p.clase, p.mercado = RF, None
    elif c in (Categoria.REPORTO, Categoria.DEPOSITO):
        p.clase, p.mercado = EFE, None
    elif c is Categoria.FONDO:
        p.clase, p.mercado = None, None  # se transparenta en métricas
    else:  # pragma: no cover - el Enum es cerrado
        raise ErrorClasificacion(f"Categoría desconocida {c} ({contexto})")


def clasificar_cartera(c: Cartera, referencia: Cartera | None = None) -> Cartera:
    for p in c.posiciones:
        contexto = f"{c.operadora}/{c.fondo_clave} {c.fecha_corte} {p.emisora_raw}"
        if p.es_agregado and p.categoria in (Categoria.ETF_EXTRANJERO, Categoria.ETF_LOCAL):
            p.emisora_canonica = canonica(p.emisora)
            _clase_agregado_etf(p, c, referencia, contexto)
            continue
        clasificar_posicion(p, contexto)
    return c
