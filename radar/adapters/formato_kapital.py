"""Cartera mensual de KPTL México Operadora (Kapital): un PDF con una página por fondo.

Cada página trae secciones por tipo de instrumento ("Reportos", "Bonos De Desarrollo Del Gobierno
Federal", "Chequera Dólares", "Títulos Referenciados a Acciones Tracs Extranjeras (Spot)"...) con
renglones "T.VALOR EMISORA SERIE CALIF/BURS VALOR TOTAL %" y cierra con TOTAL CARTERA, ACTIVO NETO y
"Cartera al: dd/mm/aaaa". La clave del fondo NO viene en el texto (está en la imagen del
encabezado): sale de los marcadores del PDF, uno por página, que el emisor exporta desde su hoja
de cálculo ("+TASA", "KPTLGLO"...).

Los reportos se reconocen por su sección: en ella el tipo de valor es el del bono subyacente (LF,
IS). No publica número de títulos: la cartera sirve como corte adelantado del mes y no mide
rotación; cuando llega el R7 de la CNBV del mismo mes (con títulos), el R7 manda.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pdfplumber
from pdfminer.pdftypes import resolve1

from radar.adapters.base import ErrorParseo, norm
from radar.core.modelo import Cartera, Categoria, Documento, Posicion, Procedencia
from radar.core.numeros import es_monto, monto
from radar.core.pdffilas import iterar_paginas
from radar.core.tipos_valor import TipoValorDesconocido, categoria_por_tv

RE_FECHA = re.compile(r"Cartera al:\s*(\d{2})/(\d{2})/(\d{4})")
RE_PCT = re.compile(r"^-?\d+(\.\d+)?%$")


def claves_por_pagina(ruta: Path) -> dict[int, str]:
    """Marcadores del PDF -> {página (1-based): clave del fondo}."""
    out: dict[int, str] = {}
    with pdfplumber.open(ruta) as pdf:
        ids = {p.page_obj.pageid: i + 1 for i, p in enumerate(pdf.pages)}
        try:
            marcadores = list(pdf.doc.get_outlines())
        except Exception:  # noqa: BLE001 - PDF sin marcadores
            return out
        for _nivel, titulo, dest, accion, _se in marcadores:
            d = resolve1(dest) if dest else None
            if d is None and accion:
                d = resolve1(resolve1(accion).get("D"))
            if isinstance(d, list) and d and getattr(d[0], "objid", None) in ids:
                out[ids[d[0].objid]] = str(titulo).strip().upper()
    return out


def fecha_cartera(ruta: Path) -> date | None:
    for pg in iterar_paginas(ruta):
        for f in pg.filas():
            m = RE_FECHA.search(f.texto)
            if m:
                return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def _posicion(tokens: list[str], seccion: str, proc: Procedencia, contexto: str) -> Posicion | None:
    if len(tokens) < 6 or not RE_PCT.match(tokens[-1]) or not es_monto(tokens[-2]):
        return None
    tv = tokens[0]
    try:
        cat = categoria_por_tv(tv, contexto)
    except TipoValorDesconocido:
        return None  # renglón de sección ("Bonos Del Gob. Fed. Tasa Fija 23,696,913 16.24%")
    if norm(seccion).startswith("reporto"):
        cat = Categoria.REPORTO
    emisora, serie = tokens[1], tokens[2]
    return Posicion(
        emisora_raw=f"{tv}_{emisora}_{serie}", tipo_valor=tv, emisora=emisora, serie=serie, titulos=None,
        valor_razonable=monto(tokens[-2]), pct_cartera=float(tokens[-1].rstrip("%")) / 100,
        tipo_instrumento_raw=seccion, calificacion=" ".join(tokens[3:-2]), divisa="", categoria=cat,
        procedencia=proc,
    )


def parsear(ruta: Path, doc: Documento, operadora: str) -> list[Cartera]:
    claves = claves_por_pagina(ruta)
    if not claves:
        raise ErrorParseo(f"Kapital {doc.archivo}: el PDF no trae marcadores con la clave de cada fondo")
    archivo = Path(doc.archivo).name
    carteras: list[Cartera] = []
    for pg in iterar_paginas(ruta):
        n = pg.numero  # 1-based
        filas = pg.filas()
        clave = claves.get(n)
        if not clave:
            continue
        contexto = f"Kapital {clave} ({archivo} p.{n})"
        tipo_fondo = "RV" if any("renta variable" in norm(f.texto) for f in filas[:4]) else "RF"
        categoria = next((f.texto.split(":", 1)[1].strip() for f in filas if f.texto.startswith("Categoría:")), "")
        fecha = next((date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                      for f in filas if (m := RE_FECHA.search(f.texto))), None)
        total = next((monto(f.texto.split()[2]) for f in filas if f.texto.startswith("TOTAL CARTERA")), None)
        activo = next((monto(f.texto.split()[2]) for f in filas if f.texto.startswith("ACTIVO NETO")), None)
        if fecha is None or total is None or activo is None:
            raise ErrorParseo(f"{contexto}: falta fecha, total de cartera o activo neto")
        proc = Procedencia(doc.doc_id, archivo, n, fecha)
        posiciones: list[Posicion] = []
        seccion = ""
        for f in filas:
            t = f.texto
            if t.startswith(("TOTAL CARTERA", "ACTIVO NETO", "T.VALOR")):
                continue
            tokens = t.split()
            p = _posicion(tokens, seccion, proc, contexto)
            if p is not None:
                posiciones.append(p)
            elif len(tokens) >= 3 and RE_PCT.match(tokens[-1]) and es_monto(tokens[-2]):
                seccion = " ".join(tokens[:-2])
        if not posiciones:
            raise ErrorParseo(f"{contexto}: sin posiciones")
        carteras.append(Cartera(
            operadora=operadora, fondo_clave=clave, nombre_legal="", categoria=categoria, fecha_corte=fecha,
            tipo_doc=doc.tipo, activo_neto=activo, activo_neto_estimado=False, total_cartera=total,
            posiciones=posiciones, procedencia=proc, tipo_fondo=tipo_fondo,
            notas=["Cartera mensual de la operadora: sin número de títulos (no mide rotación hasta el R7 del mes)."],
        ))
    return carteras
