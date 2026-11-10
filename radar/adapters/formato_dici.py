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
from radar.core.numeros import MESES, es_monto, es_pct, mes_a_numero, monto, sin_acentos
from radar.core.pdffilas import Fila, iterar_paginas, leer_pdf

RE_FECHA = re.compile(r"(?:Principales inversiones (?:en el|al) mes de:?|^Informaci[oó]n a) (\w+) (?:del |de )?(\d{4})")


# Principal / Skandia: "Cartera de inversión al :30/oct/2026"; Franklin: "Principales
# inversiones al : 30 de octubre de 2026".
RE_FECHA_DIA = re.compile(r"(?:Cartera de inversi[oó]n|Principales inversiones) al\s*:\s*(\d{1,2})"
                          r"(?:/|\s+de\s+)([A-Za-zé]+)(?:/|\s+de\s+)(\d{4})")


def _mes(nombre: str) -> int | None:
    n = sin_acentos(nombre).lower().strip(" .")
    return MESES.get(n) or next((v for k, v in MESES.items() if len(n) == 3 and k.startswith(n)), None)


def fecha_dici(ruta: Path) -> date | None:
    for f in next(iterar_paginas(ruta)).filas():
        m = RE_FECHA.search(f.texto)
        if m and _mes(m.group(1)):
            mes, anio = _mes(m.group(1)), int(m.group(2))
            return date(anio, mes, calendar.monthrange(anio, mes)[1])
        m = RE_FECHA_DIA.search(f.texto)
        if m and _mes(m.group(2)):
            return date(int(m.group(3)), _mes(m.group(2)), int(m.group(1)))
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
                if not categoria:  # BlackRock: el valor va en el renglón siguiente
                    sig_f = next((g for g in filas if 0 < g.top - f.top < 12), None)
                    categoria = sig_f.texto_entre(120, 320).strip() if sig_f else ""
            if composicion_total is None and f.palabras and f.palabras[0].x0 > 300 and (
                    f.palabras[0].texto == "Total" or f.texto.startswith("Cartera Total")):
                montos = [p.texto for p in f.palabras if es_monto(p.texto) and "," in p.texto]
                if montos:
                    composicion_total = monto(montos[0])
        if not indice:
            indice = _indice(filas) or _indice_en_politica(filas)
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
    rv_min, rv_max = rv_coherente(categoria, rv_min, rv_max, notas)
    return Dici(
        operadora=operadora, fondo_clave=clave or (doc.fondo_clave or ""), fecha_doc=fecha,
        categoria_regulatoria=categoria, rv_min=rv_min, rv_max=rv_max, fuente_regimen=fuente_regimen,
        liquidez=liquidez, plazo_liquidacion=liquidacion, limite_recompra=recompra,
        indice_referencia=indice, distribuidoras=distribuidoras, series=series,
        composicion_total=composicion_total, procedencia=Procedencia(doc.doc_id, archivo, 1, fecha), notas=notas,
    )


def rv_coherente(categoria: str, rv_min, rv_max, notas: list[str]):
    """Un fondo de deuda (IDCP, IDLP...) no puede tener RV: si se leyó, el renglón habla de
    acciones de fondos (p. ej. TEMGBIA, alimentador de un fondo de bonos extranjero)."""
    if rv_max and re.search(r"\bID[A-Z]{2,}", categoria):
        notas.append(f"Régimen: se leyó RV hasta {rv_max:.0%} en un fondo de deuda ({categoria}); "
                     "se descarta [POR CONFIRMAR]")
        return None, None
    return rv_min, rv_max


def _indice_en_politica(filas: list[Fila]) -> str:
    """BlackRock: '... rendimiento competitivo con respecto al índice MSCI ..., publicado en'."""
    txt = " ".join(f.texto_entre(300, 620).strip() for f in filas)
    m = re.search(r"respecto (?:al|del) [íi]ndice:? (.+?)(?:,? publicad|\.\s|;)", txt)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


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
    ini = next((f for f in filas if norm(f.texto).startswith("prestadores de servicios")), None)
    fin = next((f for f in filas if f.texto.startswith("Centro de Atenci")), None)
    if ini is None or fin is None:
        return []
    bloque = [f for f in filas if ini.top < f.top < fin.top]
    # La columna de valores empieza en la menor X que se repite (>= 2 renglones) como
    # primera palabra a la derecha de las etiquetas (ignora "(s)", "de" sueltos).
    x_lab = min(p.x0 for f in bloque for p in f.palabras) if bloque else 0
    inicios = Counter(round(next(p.x0 for p in f.palabras if x_lab + 40 < p.x0 < 300))
                      for f in bloque if any(x_lab + 40 < p.x0 < 300 for p in f.palabras))
    repetidos = [x for x, n in inicios.items() if n >= 2]
    if not repetidos:
        return []
    x_val = min(repetidos)
    # La leyenda legal ("Advertencias") corre en una segunda columna: se corta donde empieza.
    der = Counter(round(p.x0) for f in bloque for p in f.palabras if p.x0 > x_val + 150)
    corte = der.most_common(1)[0][0] - 3 if der else x_val + 215
    lineas = [f.texto_entre(x_val - 5, corte).strip() for f in bloque]
    lineas = [l for l in lineas if l]
    # Texto entre las etiquetas "Distribuidora(s)" y "Valuadora" (plantillas en las que la
    # lista no se separa por renglón: BlackRock con " / ", Principal con comas).
    txt_d = ""
    ini_d = next((f for f in bloque if norm(f.texto_entre(0, x_val - 3)).startswith("distribuidora")), None)
    fin_d = next((f for f in bloque if norm(f.texto_entre(0, x_val - 3)).startswith("valuadora")), None)
    if ini_d is not None:
        tope = fin_d.top if fin_d is not None else ini_d.top + 40
        cand = [f for f in bloque if ini_d.top - 25 <= f.top < tope - 6]
        txt_d = " ".join(f.texto_entre(x_val - 3, corte).strip() for f in cand)
        txt_d = re.sub(r"\s+", " ", re.sub(r"^Distribuidora\s*\(s\)", "", txt_d)).strip()
    if " / " in txt_d:
        return [t.strip(" ,;/") for t in txt_d.split(" / ") if t.strip(" ,;/")]
    entes = entes_por_forma_juridica(" ".join(lineas))
    if len(entes) < 4:
        entes = entes_prestadores(lineas)
    # Orden estructural: Operadora, Distribuidora(s)..., Valuadora, Calificadora.
    if len(entes) >= 4:
        return [re.sub(r"(Inversi[oó]n)\.$", lambda m: m.group(1), e.strip()) for e in entes[1:-2]]
    if not txt_d:
        raise ErrorParseo(f"{contexto}: prestadores ilegibles {entes}")
    return entes_por_forma_juridica(txt_d) or [txt_d]
