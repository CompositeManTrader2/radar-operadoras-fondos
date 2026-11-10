"""SURA Investment Management México (CNBV: SIM). La página de rendimientos (CMS Modyo) usa
una API JSON pública sin sesión ni login; son las mismas consultas que hace la página al
cargar (no hay envío de formularios):

1. rendimientos/fondo-rendimiento -> fondos y series publicados;
2. resumen/fondo {fondo, serie}   -> ids del DICI ("infoClave") y del prospecto;
3. files/type-file-prospecto-info-clave | files/type-file-prospecto -> PDF en base64.

El DICI no lista distribuidoras (remite al prospecto, que nombra a la propia SURA IM y a
terceros: Ve por Más, Actinver, GBM, Finamex, Kuspit...). SURA no tiene casa de bolsa en
México. Su régimen va en la portada del DICI; el prospecto se guarda igual.
"""
from __future__ import annotations

import base64
import re
from datetime import date, timedelta
from pathlib import Path

from radar.adapters.base import DocARevisar, ErrorParseo, _es_renglon_rv
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.core.modelo import Dici, Documento, Procedencia
from radar.core.numeros import es_pct, pct
from radar.core.pdffilas import iterar_paginas
from radar.red import Cliente, ErrorDescarga, Respuesta

API = "https://inversiones.suramexico.com/cs-api-sites-suraim/v1"
ORIGEN = {"Origin": "https://www.surainvestments.com", "Referer": "https://www.surainvestments.com/",
          "Accept": "application/json"}
ARCHIVO = {"dici": ("type-file-prospecto-info-clave", "InfoClave", "infoClave"),
           "prospecto": ("type-file-prospecto", "Prospecto", "prospecto")}


def series_publicadas(datos: dict) -> dict[str, str]:
    """fondo -> primera serie, recorriendo el árbol de rendimientos (anidado por grupos)."""
    out: dict[str, str] = {}

    def recorrer(x):
        if isinstance(x, dict):
            if x.get("fondo") and x.get("serie"):
                out.setdefault(str(x["fondo"]).strip(), str(x["serie"]).strip())
            for v in x.values():
                recorrer(v)
        elif isinstance(x, list):
            for v in x:
                recorrer(v)

    recorrer(datos.get("result"))
    return out


def regimen_portada(ruta: Path) -> tuple[float | None, float | None, list[tuple[str, float, float]]]:
    """'b) Límites:  Min. Max.' de la portada del DICI: incisos '1.', '2.'... en la columna
    derecha, con las cifras al final del último renglón de cada inciso."""
    filas = next(iterar_paginas(ruta)).filas()
    hdr = next((f for f in filas if [p.texto for p in f.palabras if p.x0 > 300][:2] == ["Min.", "Max."]), None)
    if hdr is None:
        return None, None, []
    x_col = min(p.x0 for f in filas if f.top > hdr.top for p in f.palabras if 300 < p.x0 < 340) - 2
    renglones: list[tuple[str, float, float]] = []
    etiqueta: list[str] = []
    for f in filas:
        if f.top <= hdr.top:
            continue
        der = [p for p in f.palabras if p.x0 >= x_col]
        if not der:
            continue
        if re.match(r"^[a-z]\)", der[0].texto):  # "c) Política de inversión": fin de la tabla
            break
        if re.match(r"^\d+\.$", der[0].texto):
            etiqueta = []
        cifras = [p.texto for p in der if es_pct(p.texto)]
        etiqueta.extend(p.texto for p in der if not es_pct(p.texto))
        if len(cifras) == 2:
            renglones.append((" ".join(etiqueta), pct(cifras[0]), pct(cifras[1])))
            etiqueta = []
    rv = [r for r in renglones if _es_renglon_rv(r[0])]
    if not renglones:
        return None, None, []
    if not rv:
        return 0.0, 0.0, []
    return max(r[1] for r in rv), min(1.0, max(r[2] for r in rv)), rv


class Sura(AdaptadorCnbvConDici):
    marcas = ("sura",)

    def _post(self, cliente: Cliente, ruta: str, datos: dict) -> dict:
        r = cliente.post_json(f"{API}/{ruta}", datos, ORIGEN)
        if r.get("code") not in (0, None):
            raise ErrorParseo(f"SURA {ruta}: {r.get('message')}")
        return r

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        hoy = date.today()
        rend = self._post(cliente, "rendimientos/fondo-rendimiento", {
            "fechaInicio": (hoy - timedelta(days=7)).strftime("%d/%m/%Y"), "fechaFin": hoy.strftime("%d/%m/%Y"),
            "idAdquiriente": 0, "idCategoria": 0, "rendimientosAnualizados": True})
        series = series_publicadas(rend)
        if not series:
            raise ErrorParseo("SURA: la API de rendimientos no devolvió fondos")
        docs: list[DocARevisar] = []
        for k in claves:
            ids: dict = {}
            if k in series:
                try:
                    ids = (self._post(cliente, "resumen/fondo", {"fondo": k, "serie": series[k]})
                           .get("result") or {}).get("detalleFondo") or {}
                except (ErrorDescarga, ErrorParseo):
                    ids = {}
            for tipo, (ruta, clase, campo) in ARCHIVO.items():
                ident = ids.get(campo)
                url = f"{API}/files/{ruta}#{clase}/{k}/{ident}" if ident else ""
                docs.append(DocARevisar(k, tipo, url, f"{tipo.upper()}_{k}.pdf", opcional=True))
        return docs

    def bajar(self, cliente: Cliente, doc: DocARevisar) -> Respuesta | None:
        if not doc.url:
            return Respuesta(doc.url, 404, "", b"", False)
        ruta, frag = doc.url.split("#", 1)
        clase, clave, ident = frag.split("/")
        tipo = "dici" if clase == "InfoClave" else "prospecto"
        campo = ARCHIVO[tipo][2]
        datos = {"idClass": "InfFondo", "idKey": f"{clase}/{clave}", campo: int(ident)}
        datos["validacionClave" if tipo == "dici" else "necesitaValidacion"] = False
        try:
            r = cliente.post_json(ruta, datos, ORIGEN)
            cuerpo = base64.b64decode(((r.get("result") or {}).get("typeFile") or {}).get("body") or "")
        except (ErrorDescarga, ValueError):
            cuerpo = b""
        return Respuesta(doc.url, 200 if cuerpo else 404, "application/pdf", cuerpo, False)

    def parsear_dici(self, ruta: Path, doc: Documento, prospecto) -> Dici:
        """El régimen sale de la portada del DICI (tabla Min./Max.); el del prospecto queda de
        respaldo. En el prospecto de SURA la tabla mezcla límites por tipo de activo."""
        d = super().parsear_dici(ruta, doc, prospecto)
        mn, mx, rv = regimen_portada(ruta)
        if mx is not None:
            d.rv_min, d.rv_max = mn, mx
            d.fuente_regimen = Procedencia(doc.doc_id, Path(doc.archivo).name, 1, d.fecha_doc)
            d.notas = [n for n in d.notas if not n.startswith("Régimen")]
        return d
