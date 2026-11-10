"""DICI con la plantilla regulatoria de dos páginas por serie (Finaccess, Vinci Compass).

Página impar (portada): Tipo, Categoría, Clave de pizarra | Clase y Serie, Posibles
adquirientes, Montos mínimos | composición de cartera (Total) | índice de referencia.
Página par: comisiones (una columna por serie), políticas de compra-venta y
prestadores de servicios (Operadora, Distribuidora(s), Valuadora, Calificadora).

Las columnas se ubican por la X de sus encabezados/valores, no con posiciones fijas.
"""
from __future__ import annotations

import calendar
import re
from collections import Counter
from datetime import date
from pathlib import Path

from radar.adapters.base import (
    ErrorParseo, cerca, comisiones_del_fondo, entes_por_forma_juridica, entes_prestadores, norm,
    regimen_prospecto, serie_portada,
)
from radar.core.modelo import Dici, Documento, Procedencia, SerieDici
from radar.core.numeros import es_monto, es_pct, mes_a_numero, monto
from radar.core.pdffilas import Fila, iterar_paginas, leer_pdf

RE_FECHA = re.compile(r"Principales inversiones (?:en el|al) mes de:? (\w+) del (\d{4})")


def fecha_dici(ruta: Path) -> date | None:
    for f in next(iterar_paginas(ruta)).filas():
        m = RE_FECHA.search(f.texto)
        if m:
            mes, anio = mes_a_numero(m.group(1)), int(m.group(2))
            return date(anio, mes, calendar.monthrange(anio, mes)[1])
    return None


def parsear(ruta: Path, doc: Documento, prospecto: tuple[Path, Documento] | None,
            operadora: str, etiqueta: str) -> Dici:
    paginas = leer_pdf(ruta)
    fecha = fecha_dici(ruta)
    archivo = Path(doc.archivo).name
    clave = categoria = indice = liquidez = liquidacion = recompra = ""
    composicion_total = None
    distribuidoras: list[str] = []
    series: list[SerieDici] = []
    notas: list[str] = []
    for i, pg in enumerate(paginas):
        filas = pg.filas()
        if not any("Clave de pizarra" in f.texto for f in filas):
            continue
        for f in filas:
            if f.texto.startswith("Clave de pizarra"):
                clave = clave or f.texto_entre(120, 320).strip()
            if not categoria and f.texto.startswith("Categor"):
                categoria = f.texto_entre(120, 320).strip()
            if composicion_total is None and f.palabras and f.palabras[0].texto == "Total" and f.palabras[0].x0 > 300:
                montos = [p.texto for p in f.palabras if es_monto(p.texto) and "," in p.texto]
                if montos:
                    composicion_total = monto(montos[0])
        if not indice:
            indice = _indice(filas)
        serie, adq, minimo = serie_portada(filas)
        sig = paginas[i + 1] if i + 1 < len(paginas) else None
        adm = total = None
        if sig is not None:
            sf = sig.filas()
            adm, total, inconsistencia = comisiones_del_fondo(
                sf, serie, "pagadas por el fondo", f"{etiqueta} DICI {archivo} p.{sig.numero}")
            if inconsistencia:
                notas.append(str(inconsistencia))
            if not liquidez:
                liquidez, liquidacion, recompra = _politicas(sf)
            if not distribuidoras:
                distribuidoras = _distribuidoras(sf, f"{etiqueta} DICI {archivo}")
        series.append(SerieDici(serie, adq, minimo, adm, total, Procedencia(doc.doc_id, archivo, pg.numero + 1, fecha)))
    if not series:
        raise ErrorParseo(f"{etiqueta}: no se encontraron series en {archivo}")

    rv_min = rv_max = None
    fuente_regimen = None
    if prospecto is not None:
        p_ruta, p_doc = prospecto
        rv_min, rv_max, pagina, _ = regimen_prospecto(p_ruta)
        if pagina is not None:
            fuente_regimen = Procedencia(p_doc.doc_id, Path(p_doc.archivo).name, pagina, None)
        else:
            notas.append("Régimen: no se encontró la tabla de parámetros en el prospecto [POR CONFIRMAR]")
    else:
        notas.append("Régimen: prospecto no disponible [POR CONFIRMAR]")
    return Dici(
        operadora=operadora, fondo_clave=clave or (doc.fondo_clave or ""), fecha_doc=fecha,
        categoria_regulatoria=categoria, rv_min=rv_min, rv_max=rv_max, fuente_regimen=fuente_regimen,
        liquidez=liquidez, plazo_liquidacion=liquidacion, limite_recompra=recompra,
        indice_referencia=indice, distribuidoras=distribuidoras, series=series,
        composicion_total=composicion_total, procedencia=Procedencia(doc.doc_id, archivo, 1, fecha), notas=notas,
    )


def _indice(filas: list[Fila]) -> str:
    """'Índice de Referencia %' seguido de renglones 'S&P/BMV IPC 100%', o en línea:
    'Índice(s) de Referencia: S&P/ BMV IPC (100%)'."""
    for j, f in enumerate(filas):
        n = norm(f.texto)
        if not n.startswith("indice") or "referencia" not in n:
            continue
        en_linea = re.split(r"[Rr]eferencia:?", f.texto_entre(0, 300), maxsplit=1)
        if len(en_linea) == 2 and re.search(r"[A-Za-z]{2}", en_linea[1]) and not en_linea[1].strip().startswith("%"):
            return re.sub(r"\s+", " ", en_linea[1]).strip()
        partes: list[str] = []
        for g in filas[j + 1: j + 6]:
            izq = [p.texto for p in g.palabras if p.x0 < 300]
            if len(izq) >= 2 and es_pct(izq[-1]):
                partes.append(f"{' '.join(izq[:-1])} {izq[-1]}")
            else:
                break
        return "; ".join(partes)
    return ""


def _politicas(filas: list[Fila]) -> tuple[str, str, str]:
    liquidez = liquidacion = recompra = ""
    for f in filas:
        t = f.texto
        if "Liquidez" in t:
            liquidez = f.texto_entre(390, 700).strip() or liquidez
        if t.startswith("Liquidaci"):
            liquidacion = cerca(filas, f, 140, 325, dy=8)
        if "recompra" in t:
            recompra = cerca(filas, f, 390, 700, dy=2)
    return liquidez, liquidacion, recompra


def _distribuidoras(filas: list[Fila], contexto: str) -> list[str]:
    ini = next((f for f in filas if f.texto.startswith("Prestadores de Servicios")), None)
    fin = next((f for f in filas if f.texto.startswith("Centro de Atenci")), None)
    if ini is None or fin is None:
        return []
    bloque = [f for f in filas if ini.top < f.top < fin.top]
    # La columna de valores empieza en la X más frecuente de la primera palabra con
    # X entre 100 y 300 de cada renglón (ignora palabras sueltas de etiqueta).
    inicios = Counter(round(next(p.x0 for p in f.palabras if 100 < p.x0 < 300))
                      for f in bloque if any(100 < p.x0 < 300 for p in f.palabras))
    if not inicios:
        return []
    x_val = inicios.most_common(1)[0][0]
    lineas = [f.texto_entre(x_val - 5, x_val + 215).strip() for f in bloque]
    lineas = [l for l in lineas if l]
    entes = entes_por_forma_juridica(" ".join(lineas))
    if len(entes) < 4:
        entes = entes_prestadores(lineas)
    # Orden estructural: Operadora, Distribuidora(s)..., Valuadora, Calificadora.
    if len(entes) < 4:
        raise ErrorParseo(f"{contexto}: prestadores incompletos {entes}")
    return [re.sub(r"(Inversi[oó]n)\.$", lambda m: m.group(1), e.strip()) for e in entes[1:-2]]
