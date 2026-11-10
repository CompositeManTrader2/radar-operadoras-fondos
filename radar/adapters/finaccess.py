"""Adaptador Finaccess México.

Descubrimiento: la home llama cargaFondo('finaccess','<grupo>','<clave>').
URLs estables y predecibles, SIEMPRE apuntan al corte más reciente: no hay
archivo histórico; el store guarda cada descarga fechada.
  cartera mensual  /PDF/cartera_mensual_<clave>.pdf
  cartera "diaria" /PDF/cartera_<clave>.pdf    (en la práctica un corte fechado distinto)
  DICI             /PDF/DICI_<CLAVE>.pdf
  prospecto        /PDF/ProspEspecifico<CLAVE>.pdf
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from radar.adapters import formato_dici
from radar.adapters.base import distribuidoras_unicas
from radar.adapters.base import (
    Adaptador, DocARevisar, ErrorParseo, comisiones_del_fondo, entes_prestadores, norm,
    regimen_prospecto, serie_portada, tipo_fondo_por_denominacion,
)
from radar.core.modelo import (
    ADMINISTRADO, DISTRIBUIDO, Cartera, Categoria, Dici, Documento, FondoDescubierto,
    PerfilOperadora, Posicion, Procedencia, SerieDici,
)
from radar.core.numeros import es_entero, es_monto, es_pct, fecha_es, mes_a_numero, monto, pct
from radar.core.pdffilas import Fila, PaginaPdf, iterar_paginas, leer_pdf
from radar.red import Cliente

BASE = "https://www.finaccess.com.mx"

# Tipo de instrumento tal como lo escribe Finaccess -> categoría normalizada.
# Un tipo que no esté aquí hace FALLAR el parseo (no se adivina).
TIPOS: dict[str, Categoria] = {
    "Acciones BMV": Categoria.ACCION_LOCAL,
    "FIBRA": Categoria.FIBRA,
    "ETF Mex": Categoria.ETF_LOCAL,
    "Acciones SIC": Categoria.ACCION_SIC,
    "ETF SIC": Categoria.ETF_EXTRANJERO,
    "Reporto": Categoria.REPORTO,
    "USD O/N": Categoria.DEPOSITO,  # depósito bancario en dólares a un día
}
TIPOS_DEUDA = re.compile(
    r"^(Cete|Cert\. Dep[oó]sito|Europesos|Bonos IPAB|Org Multilat\.|Bondes|Udibonos|CB |"
    r"Bonos M|M Bono|Pagar[eé]|PRLV|Eurobonos?|EBono|UMS|Treasury|T-?Bill|Certificados?)"
)
# Acciones de otros fondos ("Fondo Deuda", "Fondo RV", ...): se transparentan.
TIPOS_FONDO = re.compile(r"^Fondo\b")
TENENCIAS = {"D", "R", "P", "V", "C"}

RE_CALIF = re.compile(
    r"^(Alta|Media|Baja|M[ií]nima|Nula|NA|N/A|mx(AAA|AA|A|BBB|BB|B)[+-]?|(AAA|AA|A|BBB|BB|B)[+-]?|"
    r"A[1-3]|\(mex\)|HR\S*|F\d\+?\S*|mxA-\d\+?|AAA\S*|Aaa\S*)$"
)


def _tipo_a_categoria(tipo: str, contexto: str) -> Categoria:
    if tipo in TIPOS:
        return TIPOS[tipo]
    if TIPOS_DEUDA.match(tipo):
        return Categoria.DEUDA
    if TIPOS_FONDO.match(tipo):
        return Categoria.FONDO
    raise ErrorParseo(
        f"Tipo de instrumento desconocido {tipo!r} ({contexto}). "
        "Agrégalo a TIPOS/TIPOS_DEUDA en radar/adapters/finaccess.py."
    )


class Finaccess(Adaptador):
    clave = "finaccess"
    nombre = "Finaccess México"
    clave_cnbv = "FACCESS"

    # ------------------------------------------------------------------ perfil
    def perfil(self, dicis: list[Dici]) -> PerfilOperadora:
        distrib = distribuidoras_unicas(dicis)
        hermana = None
        if distrib:
            hermana = any("casa de bolsa" in norm(d) and "finaccess" in norm(d) for d in distrib)
        evidencia = (
            "Distribuidoras listadas en los DICI: " + "; ".join(distrib)
            if distrib else "Sin DICI parseado [POR CONFIRMAR]"
        )
        return PerfilOperadora(
            clave=self.clave,
            nombre=self.nombre,
            sitio=BASE,
            grupo_financiero="Finaccess (no forma parte de un grupo financiero con casa de bolsa en México)",
            casa_de_bolsa_hermana=hermana,
            evidencia_casa_de_bolsa=evidencia,
        )

    # ---------------------------------------------------------- descubrimiento
    def descubrir(self, cliente: Cliente) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        r = cliente.get(BASE + "/")
        if r.status != 200:
            raise ErrorParseo(f"Finaccess: la home respondió HTTP {r.status}")
        return self.descubrir_desde_html(r.texto)

    def descubrir_desde_html(self, html: str) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        fondos: dict[str, FondoDescubierto] = {}
        terceros: dict[str, FondoDescubierto] = {}
        soup = BeautifulSoup(html, "html.parser")
        for m in re.finditer(r"cargaFondo\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([a-z0-9]+)'\s*\)", html):
            operadora, _grupo, clave = m.groups()
            if operadora != "finaccess":
                terceros.setdefault(clave.upper(), FondoDescubierto(
                    clave.upper(), "", DISTRIBUIDO, {}, f"Fondo de {operadora}: solo se distribuye"))
                continue
            if clave.upper() in fondos:
                continue
            K = clave.upper()
            fondos[K] = FondoDescubierto(
                clave=K,
                nombre_comercial="",
                estatus=ADMINISTRADO,
                urls={
                    "cartera_mensual": f"{BASE}/PDF/cartera_mensual_{clave}.pdf",
                    "cartera_diaria": f"{BASE}/PDF/cartera_{clave}.pdf",
                    "dici": f"{BASE}/PDF/DICI_{K}.pdf",
                    "prospecto": f"{BASE}/PDF/ProspEspecifico{K}.pdf",
                },
            )
        # Nombre comercial: bloque <div class="info-fund"><h3>AXES CP</h3><p>Deuda Local - Corto Plazo. ...
        for info in soup.select(".info-fund"):
            h3, p = info.find("h3"), info.find("p")
            if not h3 or not p:
                continue
            k = re.sub(r"\s+", "", h3.get_text()).upper()
            desc = re.sub(r"\s+", " ", p.get_text(" ")).strip().split(".")[0].strip()
            if k in fondos and desc and not fondos[k].nombre_comercial:
                fondos[k].nombre_comercial = desc
        docs = [
            DocARevisar(f.clave, tipo, url, url.rsplit("/", 1)[1])
            for f in sorted(fondos.values(), key=lambda x: x.clave)
            for tipo, url in f.urls.items()
        ]
        return sorted(fondos.values(), key=lambda x: x.clave) + sorted(terceros.values(), key=lambda x: x.clave), docs

    # ------------------------------------------------------------------ fechas
    def fecha_documento(self, tipo: str, ruta: Path) -> date | None:
        if tipo not in ("cartera_mensual", "cartera_diaria", "dici"):
            return None
        primera = [next(iterar_paginas(ruta))]
        if tipo.startswith("cartera"):
            return self._fecha_cartera(primera)
        if tipo == "dici":
            for f in primera[0].filas():
                m = re.search(r"Principales inversiones en el mes de (\w+) del (\d{4})", f.texto)
                if m:
                    mes, anio = mes_a_numero(m.group(1)), int(m.group(2))
                    return date(anio, mes, calendar.monthrange(anio, mes)[1])
        return None

    @staticmethod
    def _fecha_cartera(paginas: list[PaginaPdf]) -> date:
        for f in paginas[0].filas():
            m = re.search(r"Cartera de Valores al (\d{1,2})/(\w+)/(\d{4})", f.texto)
            if m:
                return fecha_es(*m.groups())
        raise ErrorParseo("Finaccess: no se encontró 'Cartera de Valores al dd/mes/aaaa'")

    # ----------------------------------------------------------------- cartera
    def parsear_cartera(self, ruta: Path, doc: Documento) -> Cartera:
        paginas = leer_pdf(ruta)
        fecha = self._fecha_cartera(paginas)
        filas = [f for pg in paginas for f in pg.filas()]
        nombre_legal = categoria = clave = ""
        for f in filas[:12]:
            t = f.texto
            if not nombre_legal and "Fondo de Inversi" in t:
                nombre_legal = re.sub(r"\s+,", ",", t).strip()
            if not clave and f.palabras and re.match(r"^AXES[A-Z]+$", f.palabras[0].texto):
                clave = f.palabras[0].texto
                categoria = " ".join(p.texto for p in f.palabras[1:])
                categoria = re.sub(r"\s+AAAf/\S+(\s*\(mex\))?$", "", categoria).strip()
        if not clave or not nombre_legal:
            raise ErrorParseo(f"Finaccess: encabezado incompleto en {ruta.name}")
        if doc.fondo_clave and clave != doc.fondo_clave:
            raise ErrorParseo(f"Finaccess: {ruta.name} dice ser {clave}, se esperaba {doc.fondo_clave}")

        posiciones: list[Posicion] = []
        total = activo_neto = None
        for f in filas:
            w = f.palabras
            textos = [p.texto for p in w]
            if textos and textos[0] == "Total" and total is None:
                montos = [t for t in textos[1:] if es_monto(t) and "," in t]
                if montos:
                    total = monto(montos[-1])
                continue
            if "Activo" in textos and "Neto:" in textos:
                i = textos.index("Neto:")
                nums = [t for t in textos[i + 1:] if es_monto(t)]
                if nums:
                    activo_neto = monto(nums[0])
                continue
            if self._es_posicion(textos):
                posiciones.append(self._posicion(f, textos, doc, fecha, clave))
        if total is None or activo_neto is None:
            raise ErrorParseo(f"Finaccess {clave}: no se encontró Total o Activo Neto en {ruta.name}")
        return Cartera(
            operadora=self.clave,
            fondo_clave=clave,
            nombre_legal=nombre_legal,
            categoria=categoria,
            fecha_corte=fecha,
            tipo_doc=doc.tipo,
            activo_neto=activo_neto,
            activo_neto_estimado=False,
            total_cartera=total,
            posiciones=posiciones,
            procedencia=Procedencia(doc.doc_id, Path(doc.archivo).name, 1, fecha),
            tipo_fondo=tipo_fondo_por_denominacion(nombre_legal),
        )

    @staticmethod
    def _es_posicion(t: list[str]) -> bool:
        return (
            len(t) >= 5 and t[0] in TENENCIAS and "_" in t[1]
            and es_pct(t[-1]) and es_monto(t[-2])
        )

    def _posicion(self, f: Fila, t: list[str], doc: Documento, fecha: date, clave: str) -> Posicion:
        emisora_raw = t[1]
        partes = emisora_raw.split("_", 2)
        if len(partes) < 2:
            raise ErrorParseo(f"Finaccess {clave}: emisora sin formato TV_EMISORA_SERIE: {emisora_raw}")
        tv, emisora = partes[0], partes[1]
        serie = partes[2] if len(partes) > 2 else ""
        pct_cartera = pct(t[-1])
        valor = monto(t[-2])
        resto = t[2:-2]
        titulos = None
        if resto and es_entero(resto[-1]):
            titulos = monto(resto[-1])
            resto = resto[:-1]
        while resto and es_pct(resto[-1]):  # tasas y cupones: no se usan
            resto = resto[:-1]
        calif: list[str] = []
        while resto and RE_CALIF.match(resto[0]):
            calif.append(resto.pop(0))
        tipo = " ".join(resto)
        contexto = f"Finaccess {clave} {fecha} {emisora_raw}"
        if not tipo:
            raise ErrorParseo(f"Tipo de instrumento vacío ({contexto})")
        categoria = _tipo_a_categoria(tipo, contexto)
        return Posicion(
            emisora_raw=emisora_raw,
            tipo_valor=tv,
            emisora=emisora,
            serie=serie,
            titulos=titulos,
            valor_razonable=valor,
            pct_cartera=pct_cartera,
            tipo_instrumento_raw=tipo,
            calificacion=" ".join(calif),
            divisa="",
            categoria=categoria,
            procedencia=Procedencia(doc.doc_id, Path(doc.archivo).name, f.pagina, fecha),
            fondo_subyacente=emisora if categoria is Categoria.FONDO else None,
        )

    # -------------------------------------------------------------------- DICI
    def parsear_dici(self, ruta: Path, doc: Documento, prospecto: tuple[Path, Documento] | None) -> Dici:
        return formato_dici.parsear(ruta, doc, prospecto, self.clave, "Finaccess")
