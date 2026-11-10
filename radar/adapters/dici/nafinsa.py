"""Operadora de Fondos Nafinsa (CNBV: OPNAFIN). El sitio lista los fondos en fund:index; cada
ficha (fund:detail&fund_id=N) trae la clave en su <h2> y las descargas (fund:download&path_id=P)
bajo encabezados <h5>: un DICI por tipo de adquirente (personas físicas, morales, no sujetas a
retención...) y el prospecto particular. Los path_id no se deducen de la clave: se leen de la
ficha en cada corrida.

Se toma un DICI por fondo, en este orden: personas físicas, morales, no sujetas a retención,
otros (la nota metodológica no es DICI). El servidor a veces deja colgada la primera conexión;
los reintentos del cliente HTTP la resuelven. Nafinsa no tiene casa de bolsa (banca de desarrollo)
y sus DICI solo listan a la propia operadora como distribuidora.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from radar.adapters.base import DocARevisar, ErrorParseo, norm
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.red import Cliente

BASE = "https://www.ofnafin.com.mx/webofinsa/index.php"
INDICE = f"{BASE}?a=ofn&c=fund:index"
PRIORIDAD = (r"f.sicas?", r"morales?", r"retenci")


def fondos_del_indice(html: str) -> list[int]:
    return sorted({int(m) for m in re.findall(r"fund:detail&(?:amp;)?fund_id=(\d+)", html)})


def documentos_de_ficha(html: str) -> tuple[str, str | None, str | None]:
    """(clave, path_id del DICI elegido, path_id del prospecto particular)."""
    soup = BeautifulSoup(html, "html.parser")
    h2 = soup.select_one(".info-tab h2") or soup.find("h2")
    clave = re.sub(r"\s+", "", h2.get_text()).upper() if h2 else ""
    dicis: list[tuple[int, str]] = []
    prospecto = None
    for h5 in soup.find_all("h5"):
        titulo = norm(h5.get_text())
        ul = h5.find_next_sibling("ul")
        if ul is None:
            continue
        for li in ul.find_all("li"):
            a = li.find("a", href=re.compile(r"path_id=\d+"))
            if a is None:
                continue
            pid = re.search(r"path_id=(\d+)", a["href"]).group(1)
            etiqueta = norm(li.get_text(" "))
            if titulo.startswith("documento con inform"):
                if "metodolog" in etiqueta:
                    continue
                rango = next((i for i, rx in enumerate(PRIORIDAD) if re.search(rx, etiqueta)), len(PRIORIDAD))
                dicis.append((rango, pid))
            elif titulo.startswith("prospecto") and (prospecto is None or "particular" in etiqueta):
                prospecto = pid
    dici = min(dicis)[1] if dicis else None
    return clave, dici, prospecto


def _descarga(pid: str) -> str:
    return f"{BASE}?a=ofn&c=fund:download&path_id={pid}&"


class Nafinsa(AdaptadorCnbvConDici):
    marcas = ("nafin",)

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        r = cliente.get(INDICE)
        if r.status != 200:
            raise ErrorParseo(f"Nafinsa: la lista de fondos respondió HTTP {r.status}")
        encontrados: dict[str, tuple[str | None, str | None]] = {}
        for fid in fondos_del_indice(r.texto):
            f = cliente.get(f"{BASE}?a=ofn&c=fund:detail&fund_id={fid}&")
            if f.status != 200:
                continue
            clave, dici, pros = documentos_de_ficha(f.texto)
            if clave in claves and clave not in encontrados:
                encontrados[clave] = (dici, pros)
        docs: list[DocARevisar] = []
        for k in claves:
            dici, pros = encontrados.get(k, (None, None))
            docs.append(DocARevisar(k, "dici", _descarga(dici) if dici else "", f"DICI_{k}.pdf", opcional=True))
            if pros:
                docs.append(DocARevisar(k, "prospecto", _descarga(pros), f"Prospecto_{k}.pdf", opcional=True))
        return docs
