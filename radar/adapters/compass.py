"""Adaptador Vinci Compass (Compass Investments de México, S.A. de C.V., SOFI).

Sitio WordPress. La página de fondos propios enlaza una página por fondo; cada una
trae secciones desplegables con los documentos:
  CARTERA MENSUAL                     COMPASS<CLAVE>Publicaciones<AAAAMMDD>.pdf
  DOCUMENTOS CON INFORMACIÓN CLAVE    DICI_<CLAVE>_<MMAA>.pdf
  PROSPECTO PARTICULAR / GENÉRICO
Ojo: las rutas llevan espacios y acentos en Unicode descompuesto (NFD); se usan
exactamente como vienen en el href.

Formatos: la cartera es el formato "Publicaciones" (igual que Multiva) y el DICI la
plantilla de dos páginas por serie (igual que Finaccess).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from radar.adapters import formato_dici, formato_publicaciones
from radar.adapters.base import distribuidoras_unicas
from radar.adapters.base import Adaptador, DocARevisar, ErrorParseo, norm
from radar.core.modelo import (
    ADMINISTRADO, DISTRIBUIDO, NO_DISPONIBLE, Cartera, Dici, Documento, FondoDescubierto, PerfilOperadora,
)
from radar.core.pdffilas import iterar_paginas
from radar.red import Cliente

BASE = "https://latam.vincicompass.com"
PAGINA_FONDOS = BASE + "/es/mexico/fondos-asset-management/"
PAGINA_TERCEROS = BASE + "/es/mexico/fondos-de-terceros/"
RUTA_FONDO = re.compile(r'href="\s*((?:https://latam\.vincicompass\.com)?/es/mexico/fondos-asset-management/'
                        r'fondos-asset-management-mexico/[^"/]+/([a-z0-9+-]+))/?\s*"')
RE_CARTERA = re.compile(r"COMPASS(?P<clave>.+?)Publicaciones(?P<fecha>\d{8})\.pdf$")
RE_DICI = re.compile(r"DICI_(?P<clave>.+?)_(?P<mm>\d{2})(?P<aa>\d{2})\.pdf$")

SECCIONES = {
    "cartera mensual": "cartera_mensual",
    "documentos con informacion clave": "dici",
    "documento con informacion clave": "dici",
    "prospecto particular": "prospecto",
    "prospecto generico": "prospecto_generico",
}


def _nombre(url: str) -> str:
    return unquote(url.rstrip("/").rsplit("/", 1)[1])


def secciones_de_fondo(html: str, base: str) -> dict[str, list[str]]:
    """{tipo_doc: [urls]} de la página de un fondo."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, list[str]] = {}
    for b in soup.select("button.com_acc-deploy-button"):
        tipo = SECCIONES.get(norm(b.get_text(" ", strip=True)))
        area = b.find_next_sibling("div")
        if not tipo or area is None:
            continue
        for a in area.select("a[href]"):
            out.setdefault(tipo, []).append(urljoin(base, a["href"].strip()))
    return out


def _mas_reciente(tipo: str, urls: list[str]) -> str | None:
    def clave_orden(u: str):
        n = _nombre(u)
        if tipo == "cartera_mensual" and (m := RE_CARTERA.search(n)):
            return (m.group("fecha"), n)
        if tipo == "dici" and (m := RE_DICI.search(n)):
            return (f"20{m.group('aa')}{m.group('mm')}", n)
        return ("", n)
    if tipo == "prospecto":
        urls = [u for u in urls if _nombre(u).lower().startswith("prospecto")]
    return max(urls, key=clave_orden) if urls else None


class Compass(Adaptador):
    clave = "compass"
    nombre = "Vinci Compass"
    clave_cnbv = "SEICOMP"

    # ------------------------------------------------------------------ perfil
    def perfil(self, dicis: list[Dici]) -> PerfilOperadora:
        distrib = distribuidoras_unicas(dicis)
        hermana = None
        if distrib:
            hermana = any("casa de bolsa" in norm(d) and ("compass" in norm(d) or "vinci" in norm(d)) for d in distrib)
        evidencia = ("Distribuidoras listadas en los DICI: " + "; ".join(distrib)
                     if distrib else "Sin DICI parseado [POR CONFIRMAR]")
        return PerfilOperadora(self.clave, self.nombre, PAGINA_FONDOS,
                               "Vinci Compass (sin casa de bolsa en el padrón CNBV)", hermana, evidencia)

    # ---------------------------------------------------------- descubrimiento
    def descubrir(self, cliente: Cliente) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        r = cliente.get(PAGINA_FONDOS)
        if r.status != 200:
            raise ErrorParseo(f"Vinci Compass: la página de fondos respondió HTTP {r.status}")
        paginas: dict[str, str] = {}
        for ruta, slug in sorted(set(RUTA_FONDO.findall(r.texto))):
            p = cliente.get(urljoin(BASE, ruta))
            if p.status == 200:
                paginas[slug] = p.texto
        terceros = cliente.get(PAGINA_TERCEROS)
        return self.descubrir_desde_html(paginas, terceros.texto if terceros.status == 200 else "")

    def descubrir_desde_html(self, paginas: dict[str, str], html_terceros: str = "") -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        fondos: list[FondoDescubierto] = []
        docs: list[DocARevisar] = []
        genericos: set[str] = set()
        for slug in sorted(paginas):
            secc = secciones_de_fondo(paginas[slug], BASE)
            urls = {t: u for t in ("cartera_mensual", "dici", "prospecto") if (u := _mas_reciente(t, secc.get(t, [])))}
            genericos.update(secc.get("prospecto_generico", []))
            m = RE_CARTERA.search(_nombre(urls["cartera_mensual"])) if "cartera_mensual" in urls else None
            if m is None:
                fondos.append(FondoDescubierto(slug.upper(), "", NO_DISPONIBLE, urls,
                                               "Página del fondo sin cartera mensual publicada"))
                continue
            clave = m.group("clave")
            fondos.append(FondoDescubierto(clave, "", ADMINISTRADO, urls))
            docs.extend(DocARevisar(clave, t, u, _nombre(u)) for t, u in sorted(urls.items()))
        for u in sorted(genericos)[:1]:
            docs.append(DocARevisar(None, "prospecto_generico", u, _nombre(u)))
        propios = {f.clave for f in fondos}
        for k in sorted(set(re.findall(r'/fondos-de-terceros/[^"]*?/([a-z0-9+-]+)/?"', html_terceros))):
            if k.upper() not in propios:
                fondos.append(FondoDescubierto(k.upper(), "", DISTRIBUIDO, {}, "Fondo de terceros: solo se distribuye"))
        return fondos, docs

    # ------------------------------------------------------------------ fechas
    def fecha_documento(self, tipo: str, ruta: Path) -> date | None:
        if tipo.startswith("cartera"):
            return formato_publicaciones.fecha_cartera(next(iterar_paginas(ruta)), "Vinci Compass")
        if tipo == "dici":
            return formato_dici.fecha_dici(ruta)
        return None

    # -------------------------------------------------------------- documentos
    def parsear_cartera(self, ruta: Path, doc: Documento) -> Cartera:
        c = formato_publicaciones.parsear(ruta, doc, self.clave, "Vinci Compass")
        base = re.split(r",?\s*\bS\.?\s?A\.?(?=[\s,]|$)", c.nombre_legal, flags=re.I)[0].strip()
        c.nombre_corto = base.title().replace(" De ", " de ")
        return c

    def parsear_dici(self, ruta: Path, doc: Documento, prospecto: tuple[Path, Documento] | None) -> Dici:
        return formato_dici.parsear(ruta, doc, prospecto, self.clave, "Vinci Compass")
