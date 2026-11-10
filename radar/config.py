"""Rutas y parámetros. Los parámetros viven en config/parametros.toml."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def dir_datos() -> Path:
    return Path(os.environ.get("RADAR_DATOS", RAIZ / "data"))


def dir_salidas() -> Path:
    return Path(os.environ.get("RADAR_SALIDAS", RAIZ / "salidas"))


def ruta_db() -> Path:
    return dir_datos() / "radar.sqlite"


def ruta_parametros() -> Path:
    return Path(os.environ.get("RADAR_PARAMETROS", RAIZ / "config" / "parametros.toml"))


@dataclass(frozen=True)
class SupuestosOperadora:
    probabilidad_de_alta: float
    friccion_alta: int
    friccion_nota: str


@dataclass(frozen=True)
class Parametros:
    comision_local_pb: float
    comision_sic_pb: float
    captura_objetivo: float
    cortes_para_cifra: int
    multiplicador_techo: float
    max_meses_par: float
    sin_medicion_min: float
    sin_medicion_max: float
    umbral_fondo_de_fondos: float
    tolerancia_cuadre: float
    umbral_discrepancia: float
    pesos: dict[str, float]
    tier1_min: float
    tier2_min: float
    bolsa_cortes: list[float]
    rotacion_cortes: list[float]
    headroom_cortes: list[float]
    operadoras: dict[str, SupuestosOperadora] = field(default_factory=dict)
    default: SupuestosOperadora | None = None
    default_con_hermana: SupuestosOperadora | None = None

    def supuestos(self, clave: str, hermana: bool | None = None) -> SupuestosOperadora | None:
        """Supuestos comerciales (e) de la operadora; si no tiene entrada propia, el genérico."""
        if clave in self.operadoras:
            return self.operadoras[clave]
        return self.default_con_hermana if hermana else self.default

    @property
    def comision_local(self) -> float:
        return self.comision_local_pb / 10_000

    @property
    def comision_sic(self) -> float:
        return self.comision_sic_pb / 10_000


def cargar_parametros(ruta: Path | None = None) -> Parametros:
    datos = tomllib.loads((ruta or ruta_parametros()).read_text(encoding="utf-8"))
    c, r, k, q = datos["comisiones"], datos["rotacion"], datos["clasificacion"], datos["calificacion"]
    pesos = {
        "bolsa": q["PESO_BOLSA"],
        "independencia": q["PESO_INDEPENDENCIA"],
        "ajuste": q["PESO_AJUSTE"],
        "recurrencia": q["PESO_RECURRENCIA"],
        "headroom": q["PESO_HEADROOM"],
        "friccion": q["PESO_FRICCION"],
    }
    if abs(sum(pesos.values()) - 1) > 1e-9:
        raise ValueError(f"Los pesos de la calificación no suman 1: {pesos}")
    ops = {
        nombre: SupuestosOperadora(v["probabilidad_de_alta"], v["friccion_alta"], v["friccion_nota"])
        for nombre, v in datos.get("operadoras", {}).items()
    }
    dflt = datos.get("operadoras_default")
    default = default_h = None
    if dflt:
        default = SupuestosOperadora(dflt["probabilidad_de_alta"], dflt["friccion_alta"], dflt["friccion_nota"])
        default_h = SupuestosOperadora(dflt.get("probabilidad_de_alta_con_hermana", dflt["probabilidad_de_alta"]),
                                       dflt["friccion_alta"], dflt["friccion_nota"])
    return Parametros(
        comision_local_pb=c["COMISION_LOCAL_PB"],
        comision_sic_pb=c["COMISION_SIC_PB"],
        captura_objetivo=c["CAPTURA_OBJETIVO"],
        cortes_para_cifra=r["CORTES_PARA_CIFRA"],
        multiplicador_techo=r["MULTIPLICADOR_TECHO"],
        max_meses_par=r["MAX_MESES_PAR"],
        sin_medicion_min=r["SIN_MEDICION_MIN"],
        sin_medicion_max=r["SIN_MEDICION_MAX"],
        umbral_fondo_de_fondos=k["UMBRAL_FONDO_DE_FONDOS"],
        tolerancia_cuadre=k["TOLERANCIA_CUADRE"],
        umbral_discrepancia=k["UMBRAL_DISCREPANCIA"],
        pesos=pesos,
        tier1_min=q["TIER1_MIN"],
        tier2_min=q["TIER2_MIN"],
        bolsa_cortes=list(q["BOLSA_MXN_CORTES"]),
        rotacion_cortes=list(q["ROTACION_CORTES"]),
        headroom_cortes=list(q["HEADROOM_CORTES"]),
        operadoras=ops,
        default=default,
        default_con_hermana=default_h,
    )
