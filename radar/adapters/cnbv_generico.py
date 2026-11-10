"""Adaptador genérico para operadoras cubiertas solo con la CNBV (R7 + R1).

No descarga nada propio: la cartera mensual y el activo neto llegan por la fuente
transversal radar/fuentes/cnbv.py (que `fetch` descarga una vez para todas). No hay
DICI, así que régimen, comisiones y distribuidoras quedan [POR CONFIRMAR]; la casa de
bolsa hermana sale de config/operadoras_cnbv.toml (padrón CNBV).
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from radar.adapters.base import Adaptador, DocARevisar, ErrorParseo
from radar.config import RAIZ
from radar.core.modelo import Cartera, Dici, Documento, FondoDescubierto, PerfilOperadora
from radar.red import Cliente, Respuesta

RUTA_CONFIG = RAIZ / "config" / "operadoras_cnbv.toml"


@dataclass(frozen=True)
class ConfigCnbv:
    clave: str
    nombre: str
    clave_cnbv: str
    grupo: str
    casa_de_bolsa_hermana: bool | None
    casa_de_bolsa: str
    nota: str
    fuente: str


def cargar_config(ruta: Path = RUTA_CONFIG) -> list[ConfigCnbv]:
    datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    fuente = datos.get("defaults", {}).get("fuente", "")
    out = []
    for clave, v in datos.items():
        if clave == "defaults":
            continue
        out.append(ConfigCnbv(clave, v["nombre"], v["clave_cnbv"], v.get("grupo", ""),
                              v.get("casa_de_bolsa_hermana"), v.get("casa_de_bolsa", ""),
                              v.get("nota", ""), fuente))
    return out


class AdaptadorCnbv(Adaptador):
    solo_cnbv = True

    def __init__(self, cfg: ConfigCnbv) -> None:
        self.cfg = cfg
        self.clave = cfg.clave
        self.nombre = cfg.nombre
        self.clave_cnbv = cfg.clave_cnbv

    def perfil(self, dicis: list[Dici]) -> PerfilOperadora:
        c = self.cfg
        if c.casa_de_bolsa_hermana:
            ev = f"{c.casa_de_bolsa} pertenece a {c.grupo}. Fuente: {c.fuente}."
        elif c.casa_de_bolsa_hermana is False:
            ev = f"Ninguna casa de bolsa del padrón pertenece a {c.grupo}. Fuente: {c.fuente}."
        else:
            ev = "[POR CONFIRMAR]"
        if c.nota:
            ev += f" {c.nota}"
        return PerfilOperadora(c.clave, c.nombre, "CNBV R7/R1", c.grupo, c.casa_de_bolsa_hermana, ev)

    def descubrir(self, cliente: Cliente) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        return [], []  # los fondos los aporta R1/R7 al parsear

    def fecha_documento(self, tipo: str, ruta: Path) -> date | None:
        return None

    def parsear_cartera(self, ruta: Path, doc: Documento) -> Cartera:
        raise ErrorParseo(f"{self.nombre}: sin adaptador de cartera propia (solo CNBV)")

    def parsear_dici(self, ruta: Path, doc: Documento, prospecto) -> Dici:
        raise ErrorParseo(f"{self.nombre}: sin adaptador de DICI (solo CNBV)")


class AdaptadorCnbvConDici(AdaptadorCnbv):
    """Híbrido: cartera y activo neto desde la CNBV (R7/R1); DICI y prospecto desde el
    sitio de la operadora (régimen, comisiones, liquidez y distribuidoras).

    Una subclase por operadora implementa `documentos()` (cómo descubrir sus DICI) y,
    si su DICI no sigue la plantilla común (formato_dici), `parsear_dici()`.
    """

    solo_cnbv = False
    #: palabras del grupo financiero: si un DICI lista una casa de bolsa con alguna de
    #: ellas como distribuidora, es casa de bolsa hermana (contradice al padrón => se marca).
    marcas: tuple[str, ...] = ()

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        """DICI y prospectos a bajar. `claves`: fondos de la operadora en el último R7."""
        raise NotImplementedError

    def bajar(self, cliente: Cliente, doc: DocARevisar) -> Respuesta | None:
        """Descarga especial (p. ej. una API que devuelve el PDF en base64). None: GET normal."""
        return None

    def descubrir(self, cliente: Cliente, claves: list[str] | None = None
                  ) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        return [], self.documentos(cliente, list(claves or []))

    def fecha_documento(self, tipo: str, ruta: Path) -> date | None:
        if tipo == "dici":
            from radar.adapters import formato_dici

            return formato_dici.fecha_dici(ruta)
        return None

    def parsear_dici(self, ruta: Path, doc: Documento, prospecto) -> Dici:
        from radar.adapters import formato_dici

        return formato_dici.parsear(ruta, doc, prospecto, self.clave, self.nombre)

    def perfil(self, dicis: list[Dici]) -> PerfilOperadora:
        from radar.adapters.base import distribuidoras_unicas, norm

        base = super().perfil(dicis)
        distrib = distribuidoras_unicas(dicis)
        if not distrib:
            return base
        from radar.adapters.base import entes_por_forma_juridica

        # Ente por ente: una lista corrida ("Principal Fondos..., GBM ..., Casa de Bolsa") no
        # debe juntar la marca de la operadora con la casa de bolsa de un tercero.
        entes = [e for d in distrib for e in (entes_por_forma_juridica(d) or [d])]
        propias = [e for e in entes if "casa de bolsa" in norm(e) and any(m in norm(e) for m in self.marcas)]
        hermana = base.casa_de_bolsa_hermana
        ev = base.evidencia_casa_de_bolsa + " Distribuidoras en los DICI: " + "; ".join(distrib) + "."
        if propias:
            if hermana is False:
                ev += f" DISCREPANCIA: el DICI lista {', '.join(propias)} del mismo grupo; se toma como hermana."
            hermana = True
        return PerfilOperadora(base.clave, base.nombre, "CNBV R7/R1 + DICI", base.grupo_financiero, hermana, ev)
