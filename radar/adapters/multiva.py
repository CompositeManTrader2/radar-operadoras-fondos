"""Adaptador Fondos de Inversión Multiva (sitio Liferay, UUID opacos).

Descubrimiento: la página de fondos trae todos los enlaces /documents/...
  OPMULTI<CLAVE>Publicaciones<YYYYMMDD>.pdf  -> cartera
  <YYYYMM>_<CLAVE>.pdf                       -> DICI
  <CLAVE>[ _]<YYYY>.pdf                      -> prospecto específico
  MULTIVA GENERICO VIGENTE <YYYY>.pdf        -> prospecto genérico
El prospecto genérico es la VERDAD sobre qué fondos administra la operadora: la
página comercial muestra también fondos de terceros que solo distribuye y alguno
sin documentos (MVESG). Lo que esté en la web y no en el genérico: NO DISPONIBLE.

La cartera de Multiva no publica activo neto: se aproxima con el total de la
cartera de valores y se marca como estimado (e).
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote_plus

from radar.adapters import formato_publicaciones
from radar.adapters.base import distribuidoras_unicas
from radar.adapters.base import (
    Adaptador, DocARevisar, ErrorParseo, cerca, comisiones_del_fondo, entes_prestadores, norm,
    regimen_prospecto, serie_portada, tipo_fondo_por_denominacion, unir_pct,
)
from radar.core.modelo import (
    ADMINISTRADO, NO_DISPONIBLE, Cartera, Categoria, Dici, Documento, FondoDescubierto,
    PerfilOperadora, Posicion, Procedencia, SerieDici,
)
from radar.core.tipos_valor import TipoValorDesconocido, categoria_por_tv
from radar.core.numeros import es_entero, es_monto, es_pct, fecha_es, mes_a_numero, monto, pct, sin_acentos
from radar.core.pdffilas import Fila, PaginaPdf, iterar_paginas, leer_pdf
from radar.red import Cliente

BASE = "https://www.multiva.com.mx"
PAGINA_FONDOS = BASE + "/personas/ahorro-e-inversion/fondos"

RE_CARTERA = re.compile(r"^OPMULTI(?P<clave>[A-Z0-9+]+)Publicaciones(?P<fecha>\d{8})\.pdf$")
RE_DICI = re.compile(r"^(?P<yyyymm>\d{6})_(?P<clave>[A-Z0-9+]+)\.pdf$")
RE_PROSP = re.compile(r"^(?P<clave>[A-Z0-9+]+)[ _](?P<yyyy>\d{4})\.pdf$")
RE_GENERICO = re.compile(r"^MULTIVA GENERICO VIGENTE (?P<yyyy>\d{4})\.pdf$")

def _categoria(tv: str, seccion: str, contexto: str) -> Categoria:
    try:
        return categoria_por_tv(tv, contexto, es_reporto=(seccion == "REPORTO"))
    except TipoValorDesconocido as e:
        raise ErrorParseo(str(e)) from e


def _nombre_base(denominacion: str) -> str:
    """'MULTIVA FONDO ACTIVO, S.A de C.V. FONDO DE ...' -> 'multiva fondo activo'"""
    n = norm(denominacion)
    n = re.split(r",?\s*\bs\.?\s?a\.?(?=[\s,]|$)", n)[0]
    return re.sub(r"[^a-z0-9+ ]", "", n).strip()


class Multiva(Adaptador):
    clave = "multiva"
    nombre = "Fondos de Inversión Multiva"
    clave_cnbv = "OPMULTI"

    # ------------------------------------------------------------------ perfil
    def perfil(self, dicis: list[Dici]) -> PerfilOperadora:
        distrib = distribuidoras_unicas(dicis)
        hermana = None
        if distrib:
            hermana = any("casa de bolsa" in norm(d) and "multiva" in norm(d) for d in distrib)
        evidencia = (
            "Distribuidoras listadas en los DICI: " + "; ".join(distrib)
            if distrib else "Sin DICI parseado [POR CONFIRMAR]"
        )
        return PerfilOperadora(
            clave=self.clave,
            nombre=self.nombre,
            sitio=PAGINA_FONDOS,
            grupo_financiero="Grupo Financiero Multiva",
            casa_de_bolsa_hermana=hermana,
            evidencia_casa_de_bolsa=evidencia,
        )

    # ---------------------------------------------------------- descubrimiento
    def descubrir(self, cliente: Cliente) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        r = cliente.get(PAGINA_FONDOS)
        if r.status != 200:
            raise ErrorParseo(f"Multiva: la página de fondos respondió HTTP {r.status}")
        return self.descubrir_desde_html(r.texto)

    def descubrir_desde_html(self, html: str) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        enlaces = sorted(set(re.findall(r'(/documents/\d+/\d+/[^"\'\s?]+\.pdf)/[0-9a-f-]+', html)))
        carteras: dict[str, tuple[str, str]] = {}
        dicis: dict[str, tuple[str, str]] = {}
        prosp: dict[str, tuple[str, str]] = {}
        generico: tuple[str, str] | None = None
        url_de: dict[str, str] = {}
        for ruta in enlaces:
            nombre = unquote_plus(ruta.rsplit("/", 1)[1])
            m_full = re.search(re.escape(ruta) + r'/[0-9a-f-]+', html)
            url = BASE + m_full.group(0) if m_full else BASE + ruta
            url_de[nombre] = url
            if m := RE_CARTERA.match(nombre):
                k = m.group("clave")
                if k not in carteras or m.group("fecha") > carteras[k][0]:
                    carteras[k] = (m.group("fecha"), nombre)
            elif m := RE_DICI.match(nombre):
                k = m.group("clave")
                if k not in dicis or m.group("yyyymm") > dicis[k][0]:
                    dicis[k] = (m.group("yyyymm"), nombre)
            elif m := RE_GENERICO.match(nombre):
                if generico is None or m.group("yyyy") > generico[0]:
                    generico = (m.group("yyyy"), nombre)
            elif m := RE_PROSP.match(nombre):
                k = m.group("clave")
                if k not in prosp or m.group("yyyy") > prosp[k][0]:
                    prosp[k] = (m.group("yyyy"), nombre)

        en_web = sorted(set(re.findall(r'"([A-Z][A-Z0-9+&-]{3,12}) Tipo: ', html)))
        fondos: list[FondoDescubierto] = []
        docs: list[DocARevisar] = []
        for k in sorted(set(en_web) | set(carteras)):
            urls: dict[str, str] = {}
            if k in carteras:
                urls["cartera_mensual"] = url_de[carteras[k][1]]
            if k in dicis:
                urls["dici"] = url_de[dicis[k][1]]
            if k in prosp:
                urls["prospecto"] = url_de[prosp[k][1]]
            if k in carteras:
                # Candidato: se confirma contra el prospecto genérico tras descargar.
                fondos.append(FondoDescubierto(k, "", ADMINISTRADO, urls, "por confirmar contra prospecto genérico"))
                for tipo, url in urls.items():
                    docs.append(DocARevisar(k, tipo, url, unquote_plus(url.split("/")[-2])))
            else:
                fondos.append(FondoDescubierto(
                    k, "", NO_DISPONIBLE, urls,
                    "Aparece en la web pero sin cartera de la operadora (fondo de terceros o sin documentos)",
                ))
        if generico is None:
            raise ErrorParseo("Multiva: no se encontró el prospecto genérico vigente")
        docs.append(DocARevisar(None, "prospecto_generico", url_de[generico[1]], generico[1]))
        return fondos, docs

    def nombres_en_generico(self, ruta: Path) -> list[str]:
        """Denominaciones de los fondos que la operadora administra (págs. 1-3)."""
        nombres: list[str] = []
        for pg in iterar_paginas(ruta):
            if pg.numero > 3:
                break
            for f in pg.filas():
                m = re.match(r"^\s*(.{3,80}?),?\s*S\.A\.?\s*(?:DE|de)\s*C\.V\.?,?\s*Fondo de Inversi", f.texto)
                if m and "administrad" not in norm(m.group(1)):
                    nombres.append(_nombre_base(m.group(1)))
        return sorted(set(n for n in nombres if n and "sociedad operadora" not in n))

    def confirmar_universo(self, fondos: list[FondoDescubierto], carteras: dict[str, Cartera], ruta_generico: Path) -> list[FondoDescubierto]:
        validos = set(self.nombres_en_generico(ruta_generico))
        for f in fondos:
            if f.estatus != ADMINISTRADO:
                continue
            c = carteras.get(f.clave)
            if c is None:
                f.estatus, f.nota = NO_DISPONIBLE, "Sin cartera parseada"
                continue
            base = _nombre_base(c.nombre_legal)
            if base in validos:
                f.nota = f"Confirmado en prospecto genérico como '{base}'"
            else:
                f.estatus = NO_DISPONIBLE
                f.nota = f"'{base}' no aparece en el prospecto genérico"
        return fondos

    # ------------------------------------------------------------------ fechas
    def fecha_documento(self, tipo: str, ruta: Path) -> date | None:
        if tipo.startswith("cartera"):
            return self._fecha_cartera(leer_pdf(ruta)[0])
        if tipo == "dici":
            for pg in iterar_paginas(ruta):
                for f in pg.filas():
                    m = re.search(r"Principales inversiones al mes de:?\s*(\w+) del (\d{4})", f.texto)
                    if m:
                        mes, anio = mes_a_numero(m.group(1)), int(m.group(2))
                        return date(anio, mes, calendar.monthrange(anio, mes)[1])
                break
        return None

    @staticmethod
    def _fecha_cartera(pg: PaginaPdf) -> date:
        return formato_publicaciones.fecha_cartera(pg, "Multiva")

    # ----------------------------------------------------------------- cartera
    def parsear_cartera(self, ruta: Path, doc: Documento) -> Cartera:
        c = formato_publicaciones.parsear(ruta, doc, self.clave, "Multiva")
        c.nombre_corto = _nombre_base(c.nombre_legal).title().replace(" De ", " de ").replace(" La ", " la ")
        return c

    # -------------------------------------------------------------------- DICI
    def parsear_dici(self, ruta: Path, doc: Documento, prospecto: tuple[Path, Documento] | None) -> Dici:
        paginas = leer_pdf(ruta)
        fecha = self.fecha_documento("dici", ruta)
        archivo = Path(doc.archivo).name
        clave = categoria = indice = liquidez = liquidacion = recompra = ""
        composicion_total = None
        componentes: dict[str, float] = {}
        distribuidoras: list[str] = []
        series: list[SerieDici] = []
        notas: list[str] = []
        rv_min = rv_max = None
        fuente_regimen = None

        for i, pg in enumerate(paginas):
            filas = unir_pct(pg.filas())
            if not any(f.texto.startswith("Clave de pizarra") for f in filas):
                continue
            serie, adq, minimo = serie_portada(filas)
            for f in filas:
                if f.texto.startswith("Clave de pizarra") and not clave:
                    clave = f.texto_entre(100, 330).strip()
                if f.texto.startswith("Categor") and not categoria:
                    categoria = cerca(filas, f, 100, 330)
            if not indice:
                hdr = next((f for f in filas if "Indice de referencia" in f.texto or "Índice de referencia" in f.texto), None)
                if hdr:
                    fila_s = next((f for f in filas if f.top > hdr.top and f.palabras and f.palabras[0].texto == serie), None)
                    if fila_s:
                        indice = " ".join(p.texto for p in fila_s.palabras[1:] if p.x0 < 290)
            if composicion_total is None:
                composicion_total, componentes = self._composicion(filas)
            if rv_min is None:
                rv_min, rv_max = self._regimen_texto(filas)
                if rv_max is not None:
                    fuente_regimen = Procedencia(doc.doc_id, archivo, pg.numero, fecha)
            sig = paginas[i + 1] if i + 1 < len(paginas) else None
            adm = total = None
            if sig is not None:
                sf = unir_pct(sig.filas())
                adm, total, inconsistencia = comisiones_del_fondo(
                    sf, serie, "pagadas por el fondo", f"Multiva DICI {archivo} p.{sig.numero}")
                if inconsistencia:
                    notas.append(str(inconsistencia))
                if not liquidez:
                    liquidez, liquidacion, recompra = self._politicas(sf)
                if not distribuidoras:
                    distribuidoras = self._distribuidoras(sf)
            series.append(SerieDici(serie, adq, minimo, adm, total, Procedencia(doc.doc_id, archivo, pg.numero + 1, fecha)))
        if not series:
            raise ErrorParseo(f"Multiva: no se encontraron series en {archivo}")

        if prospecto is not None:
            p_ruta, p_doc = prospecto
            pmin, pmax, pagina, _ = regimen_prospecto(p_ruta)
            if pagina is not None:
                rv_min, rv_max = pmin, pmax
                fuente_regimen = Procedencia(p_doc.doc_id, Path(p_doc.archivo).name, pagina, None)
        if rv_max is None:
            notas.append("Régimen de renta variable no localizado en DICI ni prospecto [POR CONFIRMAR]")
        if composicion_total is not None:
            notas.append("El DICI reporta montos en miles de pesos; se convierten a pesos.")
        return Dici(
            operadora=self.clave, fondo_clave=clave or (doc.fondo_clave or ""), fecha_doc=fecha,
            categoria_regulatoria=categoria, rv_min=rv_min, rv_max=rv_max, fuente_regimen=fuente_regimen,
            liquidez=liquidez, plazo_liquidacion=liquidacion, limite_recompra=recompra,
            indice_referencia=indice, distribuidoras=distribuidoras, series=series,
            composicion_total=composicion_total, procedencia=Procedencia(doc.doc_id, archivo, 1, fecha),
            notas=notas, componentes_composicion=componentes,
        )

    @staticmethod
    def _composicion(filas: list[Fila]) -> tuple[float | None, dict[str, float]]:
        total = None
        comp: dict[str, float] = {}
        tipos = ("Chequeras", "Deuda", "Renta Variable", "Reporto", "Fondos")
        for f in filas:
            der = [p for p in f.palabras if p.x0 >= 290]
            txt = " ".join(p.texto for p in der)
            montos = [p.texto for p in der if es_monto(p.texto) and "," in p.texto]
            if "CARTERA TOTAL" in txt and montos:
                total = monto(montos[0]) * 1000
            elif montos:
                for t in tipos:
                    if t in txt:
                        comp[t] = comp.get(t, 0.0) + monto(montos[0]) * 1000
                        break
        return total, comp

    @staticmethod
    def _regimen_texto(filas: list[Fila]) -> tuple[float | None, float | None]:
        der = " ".join(f.texto_entre(285, 2000) for f in filas)
        der = re.sub(r"\s+", " ", der)
        for trozo in re.split(r"[•�]|\s[a-f]\)\s", der):
            n = norm(trozo)
            if "renta variable" not in n:
                continue
            mn = re.search(r"(?:por lo menos|minimo|al menos)\s+(?:el\s+)?(\d+(?:\.\d+)?)\s?%", n)
            mx = re.search(r"maximo\s+(?:de\s+|el\s+)?(\d+(?:\.\d+)?)\s?%", n)
            if mx:
                return (float(mn.group(1)) / 100 if mn else 0.0), float(mx.group(1)) / 100
        return None, None

    @staticmethod
    def _politicas(filas: list[Fila]) -> tuple[str, str, str]:
        liquidez = liquidacion = recompra = ""
        for f in filas:
            n = norm(f.texto)
            if "liquidez" in n and not liquidez:
                liquidez = cerca(filas, f, 450, 2000, dy=3)
            if n.startswith("liquidacion de operaciones"):
                liquidacion = cerca(filas, f, 130, 375, dy=8)
            if "limite de" in n and not recompra:
                recompra = next((p.texto for g in filas if abs(g.top - f.top) <= 9 for p in g.palabras
                                 if p.x0 >= 450 and es_pct(p.texto)), "")
        return liquidez, liquidacion, recompra

    @staticmethod
    def _distribuidoras(filas: list[Fila]) -> list[str]:
        ini = next((f for f in filas if f.texto.startswith("Distribuidoras")), None)
        fin = next((f for f in filas if f.texto.startswith("Valuadora")), None)
        if ini is None or fin is None:
            return []
        lineas = [f.texto_entre(0, 312).strip() for f in filas if ini.top <= f.top < fin.top]
        txt = " ".join(lineas).replace("Distribuidoras:", "").strip()
        partes = re.split(r",\s*como distribuidor integral,\s*|;\s*", txt)
        return [re.sub(r"\s+", " ", p).strip(" ,.") for p in partes if p.strip(" ,.")]
