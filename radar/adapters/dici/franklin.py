"""Franklin Templeton México (CNBV: OPFRANK). El sitio es una SPA, pero publica la lista de
documentos en un JSON sin autenticación; el URL de cada PDF (Widen) no se arma con la clave.
Se toma "Documento Clave" (DICI) y "Prospecto Actualizado Anual" por clave. El DICI no lista
distribuidoras (remite a la web); el prospecto lista a terceros (Citi, Monex, Multiva, GBM...)."""
from __future__ import annotations

import json
import re

from radar.adapters.base import DocARevisar, ErrorParseo
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.red import Cliente

API = "https://www.franklintempleton.com.mx/api/literature/v1/documents?channel=es-mx"
TIPOS = {"Documento Clave": "dici", "Prospecto Actualizado Anual": "prospecto"}


def documentos_desde_json(datos: dict, claves: list[str]) -> list[DocARevisar]:
    vistos: dict[tuple[str, str], tuple[str, str]] = {}  # (clave, tipo) -> (fecha, url)
    for d in datos.get("document", []):
        tipo = TIPOS.get((d.get("dctermsDescription") or "").strip())
        url = d.get("downloadUrl") or ""
        if not tipo or not url:
            continue
        m = re.search(r"-\s*([A-Z0-9][A-Z0-9+-]{3,})\s*(?:,|$)", d.get("dctermsTitle") or "")
        if not m or m.group(1) not in claves:
            continue
        clave, fecha = m.group(1), d.get("frkReferenceDate") or ""
        if (clave, tipo) not in vistos or fecha > vistos[(clave, tipo)][0]:
            vistos[(clave, tipo)] = (fecha, url)
    docs = []
    for k in claves:
        for tipo in ("dici", "prospecto"):
            if (k, tipo) in vistos:
                docs.append(DocARevisar(k, tipo, vistos[(k, tipo)][1], f"{tipo.upper()}_{k}.pdf", opcional=True))
            elif tipo == "dici":
                docs.append(DocARevisar(k, tipo, "", f"DICI_{k}.pdf", opcional=True))  # no publicado
    return docs


class Franklin(AdaptadorCnbvConDici):
    marcas = ("franklin",)

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        r = cliente.get(API)
        if r.status != 200:
            raise ErrorParseo(f"Franklin: la lista de documentos respondió HTTP {r.status}")
        return documentos_desde_json(json.loads(r.contenido), claves)
