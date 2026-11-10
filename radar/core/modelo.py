"""Modelo de datos del radar.

Régimen de inversión = lo que el fondo PUEDE tener (DICI/prospecto).
Composición efectiva = lo que TIENE (cartera de valores). Nunca se mezclan.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum

# Clases de activo: cada posición cae en exactamente una.
RV_LOCAL = "RV_LOCAL"  # acciones BMV/BIVA, FIBRAS, ETFs listados en México con subyacente RV
RV_SIC = "RV_SIC"      # acciones extranjeras en directo vía SIC
RV_ETF = "RV_ETF"      # ETFs extranjeros con subyacente renta variable
RF = "RF"              # deuda y ETFs con subyacente deuda
EFE = "EFE"            # reportos y depósitos bancarios a la vista
CLASES = (RV_LOCAL, RV_SIC, RV_ETF, RF, EFE)
CLASES_RV = (RV_LOCAL, RV_SIC, RV_ETF)

MERCADO_LOCAL = "LOCAL"
MERCADO_SIC = "SIC"

# Estatus de fondo en el universo de la operadora
ADMINISTRADO = "ADMINISTRADO"
NO_DISPONIBLE = "NO DISPONIBLE"
DISTRIBUIDO = "DISTRIBUIDO"  # fondo de terceros que la operadora solo distribuye

POR_CONFIRMAR = "[POR CONFIRMAR]"


class Categoria(str, Enum):
    """Categoría de instrumento, normalizada desde el tipo crudo de cada operadora."""

    ACCION_LOCAL = "ACCION_LOCAL"
    FIBRA = "FIBRA"
    ETF_LOCAL = "ETF_LOCAL"            # listado en México (p. ej. NAFTRAC)
    ACCION_SIC = "ACCION_SIC"
    ETF_EXTRANJERO = "ETF_EXTRANJERO"  # ETF listado fuera, operado vía SIC
    DEUDA = "DEUDA"
    REPORTO = "REPORTO"
    DEPOSITO = "DEPOSITO"              # chequeras, depósitos a la vista
    FONDO = "FONDO"                    # acciones de otro fondo de inversión


@dataclass(frozen=True)
class Procedencia:
    doc_id: str          # sha256 del documento
    archivo: str         # nombre del archivo descargado
    pagina: int
    fecha_doc: date | None  # fecha de corte del documento

    def cita(self) -> str:
        f = self.fecha_doc.isoformat() if self.fecha_doc else "s/f"
        if self.archivo.lower().endswith((".xlsm", ".xlsx")):
            return f"{self.archivo}, hoja MINFO fila {self.pagina}, {f}"
        return f"{self.archivo}, p. {self.pagina}, {f}"


@dataclass
class Documento:
    doc_id: str
    operadora: str
    fondo_clave: str | None
    tipo: str            # cartera_mensual | cartera_diaria | dici | prospecto | prospecto_generico
    url: str
    archivo: str         # ruta relativa al directorio de datos
    fecha_doc: date | None
    descargado: date
    bytes: int


@dataclass
class Posicion:
    emisora_raw: str
    tipo_valor: str
    emisora: str
    serie: str
    titulos: float | None
    valor_razonable: float
    pct_cartera: float | None
    tipo_instrumento_raw: str
    calificacion: str
    divisa: str
    categoria: Categoria
    procedencia: Procedencia
    es_agregado: bool = False         # renglón que agrupa posiciones sin desglose
    nota: str = ""
    fondo_subyacente: str | None = None
    # Se llenan en clasificación
    emisora_canonica: str = ""
    clase: str | None = None
    mercado: str | None = None

    @property
    def clave_instrumento(self) -> str:
        return f"{self.emisora_canonica}|{self.serie}"


@dataclass
class Cartera:
    operadora: str
    fondo_clave: str
    nombre_legal: str
    categoria: str
    fecha_corte: date
    tipo_doc: str                     # cartera_mensual | cartera_diaria
    activo_neto: float
    activo_neto_estimado: bool        # True si no se publica y se aproxima (e)
    total_cartera: float
    posiciones: list[Posicion]
    procedencia: Procedencia
    tipo_fondo: str = ""              # "RV" o "RF" según su denominación legal
    nombre_corto: str = ""
    notas: list[str] = field(default_factory=list)

    @property
    def suma_posiciones(self) -> float:
        return sum(p.valor_razonable for p in self.posiciones)


@dataclass
class SerieDici:
    serie: str
    posibles_adquirentes: str
    monto_minimo: str
    comision_administracion: float | None   # fracción anual
    costo_total: float | None               # fracción anual
    procedencia: Procedencia | None = None


@dataclass
class Dici:
    operadora: str
    fondo_clave: str
    fecha_doc: date | None
    categoria_regulatoria: str
    rv_min: float | None                    # régimen (lo que PUEDE tener)
    rv_max: float | None
    fuente_regimen: Procedencia | None
    liquidez: str
    plazo_liquidacion: str
    limite_recompra: str
    indice_referencia: str
    distribuidoras: list[str]
    series: list[SerieDici]
    composicion_total: float | None         # total de cartera que reporta el DICI
    procedencia: Procedencia
    notas: list[str] = field(default_factory=list)
    componentes_composicion: dict[str, float] = field(default_factory=dict)


@dataclass
class FondoDescubierto:
    clave: str
    nombre_comercial: str
    estatus: str
    urls: dict[str, str]           # tipo_doc -> url
    nota: str = ""


@dataclass
class PerfilOperadora:
    clave: str
    nombre: str
    sitio: str
    grupo_financiero: str
    casa_de_bolsa_hermana: bool | None
    evidencia_casa_de_bolsa: str


def a_dict(obj) -> dict:
    """asdict con fechas y enums serializables."""

    def conv(v):
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [conv(x) for x in v]
        return v

    return conv(asdict(obj))
