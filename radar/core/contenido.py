"""Qué información mandarle a cada operadora (research, noticias, ideas) según lo que opera.

Todo sale de sus carteras: qué emisoras tiene y cuánto pesan, qué compró o vendió entre los
dos últimos cortes, cómo reparte su renta variable (México, SIC, ETFs, sectores) y su renta
fija (tasas, inflación, crédito, global). Las reglas son fijas y explícitas para que la
sugerencia se pueda auditar; no hay texto generado ni datos externos.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

from radar.core.metricas import MetricasOperadora
from radar.core.modelo import CLASES_RV, POR_CONFIRMAR, RF, RV_ETF, RV_LOCAL, RV_SIC, Cartera, Categoria

RUTA_EMISORAS = Path(__file__).parent / "datos" / "emisoras.csv"
SIN_SECTOR = "Sin sector"

# Umbrales de las reglas (fracciones).
UMBRAL_MOVIMIENTO = 0.05      # cambio de títulos para decir "aumentó" / "redujo"
UMBRAL_MEXICO = 0.25          # peso de RV México dentro de la RV
UMBRAL_SIC = 0.25
UMBRAL_ETF = 0.15
UMBRAL_SECTOR = 0.20          # peso de un sector dentro de la RV con sector conocido
UMBRAL_FIBRAS = 0.05
UMBRAL_RF = 0.40              # peso de la RF en los activos
UMBRAL_SEGMENTO_RF = 0.10     # peso de un segmento dentro de la RF
UMBRAL_HEADROOM = 0.25        # headroom / exposición RV

# Segmentos de renta fija por clave de tipo de valor (catálogo Indeval / CNBV R7).
SEGMENTOS_RF = {
    "Gubernamental tasa revisable (Bondes, IPAB)": {"LF", "LD", "LG", "IM", "IQ", "IS"},
    "Cetes": {"BI"},
    "Tasa fija (Bonos M)": {"M", "MP"},
    "Inflación (Udibonos)": {"S", "SP", "2U"},
    "Crédito corporativo y bancario": {"91", "92", "93", "94", "95", "90", "71", "2", "F", "I", "CD", "83", "JE"},
    "Deuda global y en dólares": {"56SP", "D1", "D2", "D4", "D5", "D6", "D7", "D8", "JI", "1I", "1ISP", "1B"},
}


@dataclass(frozen=True)
class InfoEmisora:
    nombre: str
    sector: str


@lru_cache(maxsize=1)
def catalogo_emisoras() -> dict[str, InfoEmisora]:
    with RUTA_EMISORAS.open(encoding="utf-8") as fh:
        filas = csv.DictReader(l for l in fh if not l.startswith("#"))
        return {r["ticker"].strip(): InfoEmisora(r["nombre"].strip(), r["sector"].strip()) for r in filas}


@lru_cache(maxsize=1)
def _catalogo_etfs() -> dict[str, tuple[str, str]]:
    ruta = Path(__file__).parent / "datos" / "etfs.csv"
    with ruta.open(encoding="utf-8") as fh:
        filas = csv.DictReader(l for l in fh if not l.startswith("#"))
        return {r["ticker"].strip(): (r["descripcion"].strip(), r["subyacente"].strip()) for r in filas}


def info_emisora(ticker: str) -> InfoEmisora:
    """Catálogo propio de emisoras; si no está, ETFs (descripción del diccionario) y nombres SIC."""
    if ticker in catalogo_emisoras():
        return catalogo_emisoras()[ticker]
    etf = _catalogo_etfs().get(ticker)
    if etf:
        tipo = {"RV": "ETF de renta variable", "DEUDA": "ETF de deuda", "MATERIA_PRIMA": "ETF de materias primas"}
        return InfoEmisora(etf[0], tipo.get(etf[1], "ETF"))
    from radar.core.clasificacion import nombre_emisora_sic

    nombre = nombre_emisora_sic(ticker)
    return InfoEmisora(nombre or POR_CONFIRMAR, SIN_SECTOR)


@dataclass
class EmisoraClave:
    emisora: str
    nombre: str
    sector: str
    mercado: str           # México | SIC | ETF
    monto: float           # valor en el corte actual
    peso_rv: float         # dentro de la RV de la operadora
    fondos: int            # fondos que la tienen
    movimiento: str        # Nueva | Aumentó | Redujo | Estable | Salida | Sin corte previo
    cambio_titulos: float | None   # variación de títulos (fracción) en los fondos comparables
    monto_movimiento: float        # compra (+) o venta (−) estimada al precio del corte


@dataclass
class Tema:
    titulo: str
    por_que: str
    que_enviar: str


@dataclass
class PlanContenido:
    operadora: str
    corte: date
    corte_previo: date | None
    perfil: list[str]
    emisoras: list[EmisoraClave]
    salidas: list[EmisoraClave]
    temas: list[Tema]
    segmentos_rf: dict[str, float] = field(default_factory=dict)

    def markdown(self, nombre: str) -> str:
        """Plan listo para pegar en un correo o en el CRM."""
        out = [f"# Qué enviarle a {nombre}", f"Corte de cartera: {self.corte.isoformat()}"
               + (f" · comparado contra {self.corte_previo.isoformat()}" if self.corte_previo else ""), ""]
        out += ["## Perfil", *[f"- {p}" for p in self.perfil], "", "## Temas y material sugerido"]
        for t in self.temas:
            out += [f"### {t.titulo}", f"- Por qué: {t.por_que}", f"- Qué enviar: {t.que_enviar}"]
        out += ["", "## Emisoras clave", "| Emisora | Nombre | Sector | Peso en su RV | Movimiento |", "|---|---|---|---|---|"]
        out += [f"| {e.emisora} | {e.nombre} | {e.sector} | {e.peso_rv:.1%} | {e.movimiento} |" for e in self.emisoras]
        return "\n".join(out) + "\n"


def _mercado(clase: str) -> str:
    return {RV_LOCAL: "México", RV_SIC: "SIC", RV_ETF: "ETF"}[clase]


def _previa(historia: list[Cartera], corte: date) -> Cartera | None:
    previas = [c for c in historia if c.fecha_corte < corte and c.tipo_doc in ("cartera_mensual", "cnbv_r7")]
    return max(previas, key=lambda c: c.fecha_corte) if previas else None


def _rv(c: Cartera):
    return [p for p in c.posiciones if p.clase in CLASES_RV and not p.es_agregado and p.categoria is not Categoria.FONDO]


def _segmento_rf(tv: str) -> str:
    return next((s for s, tvs in SEGMENTOS_RF.items() if tv.upper() in tvs), "Otra deuda")


def _lista(xs: list[str], n: int = 5) -> str:
    xs = xs[:n]
    return ", ".join(xs[:-1]) + (" y " if len(xs) > 1 else "") + xs[-1] if xs else ""


def plan_contenido(m: MetricasOperadora, n_emisoras: int = 15) -> PlanContenido:
    monto: dict[str, float] = defaultdict(float)
    mercado: dict[str, str] = {}
    fondos: dict[str, set[str]] = defaultdict(set)
    tit_hoy: dict[str, float] = defaultdict(float)      # solo fondos con corte previo
    tit_antes: dict[str, float] = defaultdict(float)
    valor_antes: dict[str, float] = defaultdict(float)
    precio: dict[str, float] = {}
    comparables: set[str] = set()
    fechas_previas: list[date] = []
    rf_seg: dict[str, float] = defaultdict(float)
    agrupadas: set[str] = set()   # entraron o salieron de un renglón agregado: no es compra ni venta

    for f in m.fondos:
        previa = _previa(f.historia, f.fecha_corte)
        tv_agr_hoy = {p.tipo_valor for p in f.cartera.posiciones if p.es_agregado}
        tv_agr_antes = {p.tipo_valor for p in previa.posiciones if p.es_agregado} if previa else set()
        for p in _rv(f.cartera):
            k = p.emisora_canonica
            monto[k] += p.valor_razonable
            mercado.setdefault(k, _mercado(p.clase))
            fondos[k].add(f.clave)
            if p.titulos:
                precio[k] = p.valor_razonable / p.titulos
            if previa is not None and p.titulos is not None:
                tit_hoy[k] += p.titulos
            if p.tipo_valor in tv_agr_antes:
                agrupadas.add(k)
        for p in f.cartera.posiciones:
            if p.clase == RF and not p.es_agregado:
                rf_seg[_segmento_rf(p.tipo_valor)] += p.valor_razonable
        if previa is not None:
            fechas_previas.append(previa.fecha_corte)
            for p in _rv(previa):
                k = p.emisora_canonica
                comparables.add(k)
                if p.tipo_valor in tv_agr_hoy:
                    agrupadas.add(k)
                mercado.setdefault(k, _mercado(p.clase))
                if p.titulos is not None:
                    tit_antes[k] += p.titulos
                valor_antes[k] += p.valor_razonable

    rv_total = sum(monto.values())

    def movimiento(k: str) -> tuple[str, float | None, float]:
        if k not in comparables and k not in tit_hoy:
            return "Sin corte previo", None, 0.0
        if k in agrupadas:
            return "Sin desglose en un corte", None, 0.0
        antes, hoy = tit_antes.get(k, 0.0), tit_hoy.get(k, 0.0)
        if antes <= 0 and hoy > 0:
            return "Nueva", None, hoy * precio.get(k, 0.0)
        if antes > 0 and hoy <= 0:
            return "Salida", -1.0, -valor_antes.get(k, 0.0)
        if antes <= 0:
            return "Sin corte previo", None, 0.0
        cambio = hoy / antes - 1
        est = "Aumentó" if cambio >= UMBRAL_MOVIMIENTO else "Redujo" if cambio <= -UMBRAL_MOVIMIENTO else "Estable"
        return est, cambio, (hoy - antes) * precio.get(k, 0.0)

    def clave(k: str) -> EmisoraClave:
        info = info_emisora(k)
        mov, cambio, mmov = movimiento(k)
        return EmisoraClave(k, info.nombre, info.sector, mercado.get(k, ""), monto.get(k, 0.0),
                            monto.get(k, 0.0) / rv_total if rv_total else 0.0, len(fondos.get(k, ())), mov, cambio, mmov)

    orden = sorted(monto, key=lambda k: (-monto[k], k))
    emisoras = [clave(k) for k in orden[:n_emisoras]]
    salidas = sorted((clave(k) for k in comparables
                      if tit_antes.get(k, 0) > 0 and k not in monto and k not in agrupadas),
                     key=lambda e: (e.monto_movimiento, e.emisora))[:10]
    todas = [clave(k) for k in orden]
    corte_previo = max(fechas_previas) if fechas_previas else None

    # --------------------------------------------------------------- perfil
    por_mercado = defaultdict(float)
    for k, v in monto.items():
        por_mercado[mercado[k]] += v
    an = m.activo_neto
    perfil = [f"Activos netos {an / 1e6:,.0f} mdp: renta variable {m.exposicion_rv / an:.0%}, renta fija "
              f"{m.monto_rf / an:.0%}, efectivo y reportos {m.monto_efe / an:.0%}." if an else "Sin activos netos."]
    if rv_total:
        perfil.append("Su renta variable: " + ", ".join(
            f"{mk} {por_mercado[mk] / rv_total:.0%}" for mk in ("México", "SIC", "ETF") if por_mercado.get(mk)) + ".")
    con_sector = [e for e in todas if e.sector != SIN_SECTOR and not e.sector.startswith("ETF")]
    rv_sector = sum(e.monto for e in con_sector)
    sectores: dict[str, float] = defaultdict(float)
    for e in con_sector:
        sectores[e.sector] += e.monto
    if rv_sector:
        top_s = sorted(sectores.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        perfil.append(f"Sectores principales (sobre {rv_sector / rv_total:.0%} de su RV con sector conocido): "
                      + ", ".join(f"{s} {v / rv_sector:.0%}" for s, v in top_s) + ".")
    rf_total = sum(rf_seg.values())
    if rf_total:
        top_rf = sorted(rf_seg.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        perfil.append("Su renta fija: " + ", ".join(f"{s} {v / rf_total:.0%}" for s, v in top_rf) + ".")
    if corte_previo:
        meses = round((m.corte - corte_previo).days / 30.4)
        perfil.append(f"Movimientos medidos entre {corte_previo.isoformat()} y {m.corte.isoformat()} "
                      "(cambio de títulos, sin efecto precio)."
                      + (f" Son {meses} meses: muestran cambios acumulados, no la operación reciente."
                         if meses > 2 else ""))
    else:
        perfil.append("Aún no hay corte previo comparable: los movimientos se verán con la siguiente cartera.")

    # --------------------------------------------------------------- temas
    temas: list[Tema] = []

    def nombres(xs: list[EmisoraClave], n: int = 5) -> str:
        return _lista([e.emisora for e in xs], n)

    locales = [e for e in todas if e.mercado == "México"]
    sic = [e for e in todas if e.mercado == "SIC"]
    etfs = [e for e in todas if e.mercado == "ETF"]
    if rv_total and por_mercado.get("México", 0) / rv_total >= UMBRAL_MEXICO:
        temas.append(Tema(
            "Mercado mexicano y emisoras locales",
            f"{por_mercado['México'] / rv_total:.0%} de su renta variable está en México; principales: {nombres(locales)}.",
            f"Research y reportes trimestrales de {nombres(locales)}; estrategia y valuación del IPC; avisos de "
            "colocaciones, ofertas y operaciones de bloque en esas emisoras."))
    if rv_total and por_mercado.get("SIC", 0) / rv_total >= UMBRAL_SIC:
        temas.append(Tema(
            "Acciones globales vía SIC",
            f"{por_mercado['SIC'] / rv_total:.0%} de su renta variable son acciones extranjeras; principales: {nombres(sic)}.",
            f"Ideas y research internacional de {nombres(sic)}; calendario de reportes de EE. UU.; propuesta de "
            "ejecución en el SIC (liquidez, horarios, costo)."))
    if rv_total and por_mercado.get("ETF", 0) / rv_total >= UMBRAL_ETF:
        temas.append(Tema(
            "ETFs",
            f"{por_mercado['ETF'] / rv_total:.0%} de su renta variable está en ETFs; principales: {nombres(etfs)}.",
            "Flujos y posicionamiento de esos ETFs, comparativos de costo entre ETFs equivalentes y alternativas de "
            "ejecución."))
    for s, v in sorted(sectores.items(), key=lambda kv: (-kv[1], kv[0])):
        if rv_sector and v / rv_sector >= UMBRAL_SECTOR:
            del_sector = [e for e in con_sector if e.sector == s]
            temas.append(Tema(
                f"Sector: {s}",
                f"{v / rv_sector:.0%} de su renta variable con sector conocido ({nombres(del_sector)}).",
                f"Research sectorial de {s.lower()}, comparables y noticias de {nombres(del_sector)}."))
    fibras = sum(e.monto for e in con_sector if e.sector == "Inmobiliario y FIBRAs")
    if rv_total and fibras / rv_total >= UMBRAL_FIBRAS and not any(t.titulo.endswith("FIBRAs") for t in temas):
        temas.append(Tema("FIBRAs", f"{fibras / rv_total:.0%} de su renta variable en FIBRAs e inmobiliarias.",
                          "Ocupación, distribuciones, emisiones y valuación de las FIBRAs que tiene."))
    nuevas = [e for e in todas if e.movimiento in ("Nueva", "Aumentó") and e.monto_movimiento > 0]
    nuevas.sort(key=lambda e: (-e.monto_movimiento, e.emisora))
    if nuevas:
        temas.append(Tema(
            "Ideas que está comprando",
            f"Compró o aumentó {nombres(nuevas)} (≈ {sum(e.monto_movimiento for e in nuevas[:5]) / 1e6:,.0f} mdp).",
            f"Seguimiento de esas tesis: research, noticias y niveles de {nombres(nuevas)}; ofrecer liquidez si sigue "
            "acumulando."))
    if salidas:
        temas.append(Tema(
            "Nombres que vendió",
            f"Salió de {nombres(salidas)}.",
            "Ideas de reemplazo en los mismos sectores y research de por qué podría volver a entrar."))
    if rf_total and an and rf_total / an >= UMBRAL_RF:
        for s, v in sorted(rf_seg.items(), key=lambda kv: (-kv[1], kv[0])):
            if v / rf_total < UMBRAL_SEGMENTO_RF or s == "Otra deuda":
                continue
            que = {
                "Gubernamental tasa revisable (Bondes, IPAB)": "Política monetaria de Banxico y expectativas de la tasa de "
                "referencia; subastas de Bondes.",
                "Cetes": "Banxico, subastas semanales de Cetes y curva de corto plazo.",
                "Tasa fija (Bonos M)": "Curva de Bonos M, duración y estrategia de tasas.",
                "Inflación (Udibonos)": "Inflación (INPC) y breakevens; subastas de Udibonos.",
                "Crédito corporativo y bancario": "Nuevas emisiones de deuda corporativa y bancaria, calificaciones y spreads.",
                "Deuda global y en dólares": "Treasuries, Fed y tipo de cambio; deuda en dólares de emisores mexicanos.",
            }[s]
            temas.append(Tema(f"Renta fija: {s}", f"{v / rf_total:.0%} de su renta fija.", que))
    if m.exposicion_rv and m.headroom / m.exposicion_rv >= UMBRAL_HEADROOM:
        temas.append(Tema(
            "Espacio para más renta variable",
            f"Sus regímenes le permiten ≈ {m.headroom / 1e6:,.0f} mdp más en renta variable "
            f"({m.headroom / m.exposicion_rv:.0%} de lo que hoy tiene).",
            "Ideas de inversión concretas en renta variable acordes a su régimen."))
    if m.perfil and m.perfil.casa_de_bolsa_hermana:
        temas.append(Tema(
            "Tiene casa de bolsa hermana",
            "El ruteo interno compite con la mesa.",
            "Priorizar material diferenciado: research independiente, ideas SIC y ejecución que su grupo no cubra."))

    return PlanContenido(m.clave, m.corte, corte_previo, perfil, emisoras, salidas, temas, dict(rf_seg))
