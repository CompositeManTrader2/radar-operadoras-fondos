"""KPTL México Operadora (Kapital; antes Intercam Fondos; CNBV: OPKPTL). Cartera y activo neto
por la CNBV; DICI y prospecto desde el buscador de fondos que Kapital publica en ibex.com.mx.

El buscador es una página pública que, al cargar, consulta un servicio (php/ws.php):
- metodo=fondos, id=<operadora>  -> lista de fondos y series ("+TASA F1", "KPTLGLO F1"...);
- metodo=datos_fondo              -> nombre del archivo del DICI de la serie ("DocumentoTASAD1F1.pdf")
                                     y del prospecto;
los PDF se bajan con a.php?archivo=/Fondos/Documentos/... o /Fondos/Prospecto/....

Hay un DICI por serie; se toma la F1 (personas físicas) o, si no existe, la primera serie. Algunos
DICI aún traen la clave anterior (+TASAMX = KPTLMPG): manda la clave de la CNBV. El DICI lista a
Kapital México Casa de Bolsa entre las distribuidoras (casa de bolsa hermana: veto).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from radar.adapters.base import DocARevisar, ErrorParseo
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.core.modelo import Dici, Documento
from radar.red import Cliente

BASE = "https://www.ibex.com.mx/dfondos"
SERVICIO = f"{BASE}/fondos/php/ws.php"
ID_OPERADORA = "10"   # "KAPITAL FONDOS" en el catálogo del buscador
ENCABEZADOS = {"Referer": f"{BASE}/fondos/buscador_simple.php", "X-Requested-With": "XMLHttpRequest"}


def series_por_fondo(html: str) -> dict[str, list[tuple[str, str]]]:
    """'<option value="275">+TASA F1</option>' -> {"+TASA": [("F1", "275"), ...]}."""
    out: dict[str, list[tuple[str, str]]] = {}
    for valor, texto in re.findall(r'<option value=["\']?(\d+)["\']?\s*>([^<]+)</option>', html):
        partes = texto.split()
        if valor == "0" or len(partes) < 2:
            continue
        out.setdefault(partes[0].upper(), []).append((partes[1].upper(), valor))
    return out


def serie_representativa(series: list[tuple[str, str]]) -> tuple[str, str]:
    return next((s for s in series if s[0] == "F1"), series[0])


def url_archivo(ruta: str) -> str:
    return f"{BASE}/a.php?archivo={quote(ruta, safe='')}"


class Kapital(AdaptadorCnbvConDici):
    marcas = ("kapital", "kptl")

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        html = cliente.post_form(SERVICIO, {"metodo": "fondos", "id": ID_OPERADORA}, ENCABEZADOS)
        fondos = series_por_fondo(html)
        if not fondos:
            raise ErrorParseo("Kapital: el buscador de fondos no devolvió fondos")
        docs: list[DocARevisar] = []
        for k in claves:
            dici = pros = ""
            if k in fondos:
                serie, valor = serie_representativa(fondos[k])
                datos = json.loads(cliente.post_form(SERVICIO, {"metodo": "datos_fondo", "cboFondo": valor,
                                                                "cboOperadora": ID_OPERADORA}, ENCABEZADOS))
                if datos.get("Documento_PDF"):
                    dici = url_archivo("/Fondos/Documentos/" + datos["Documento_PDF"])
                if datos.get("Prospectos_PDF"):
                    pros = url_archivo("/Fondos/Prospecto/" + datos["Prospectos_PDF"])
            docs.append(DocARevisar(k, "dici", dici, f"DICI_{k}.pdf", opcional=True))
            if pros:
                docs.append(DocARevisar(k, "prospecto", pros, f"Prospecto_{k}.pdf", opcional=True))
        return docs

    def parsear_dici(self, ruta: Path, doc: Documento, prospecto) -> Dici:
        d = super().parsear_dici(ruta, doc, prospecto)
        if doc.fondo_clave and d.fondo_clave != doc.fondo_clave:
            d.notas.append(f"El DICI trae la clave anterior {d.fondo_clave}; en la CNBV es {doc.fondo_clave}.")
            d.fondo_clave = doc.fondo_clave
        return d
