"""Métricas por fondo y por operadora.

exposicion_rv   = activo_neto × %RV
headroom        = (límite máximo RV del régimen − %RV) × activo_neto
importe_anual   = exposicion_rv × rotación × 2           (dos puntas)
bolsa_comision  = importe_local × COMISION_LOCAL + importe_sic × COMISION_SIC
ingreso_esperado= bolsa × CAPTURA_OBJETIVO × probabilidad_de_alta

ROTACIÓN observada (piso): compara TÍTULOS por instrumento entre dos cortes,
valora cada delta al precio implícito del corte posterior (valor/títulos),
compras = Σ deltas > 0, ventas = Σ |deltas < 0|,
rotación anual ≈ ((compras + ventas)/2) / exposición RV promedio × 12/meses.
Es un PISO: solo ve el cambio neto entre cierres, no las vueltas intermedias.
Con menos de N cortes se reporta banda, nunca cifra puntual.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from radar.config import Parametros
from radar.core.modelo import (
    CLASES, CLASES_RV, EFE, MERCADO_LOCAL, MERCADO_SIC, RF, RV_LOCAL, Cartera, Categoria, Dici,
    PerfilOperadora,
)

DIAS_MES = 30.4375


# ------------------------------------------------------------------ mezcla
@dataclass
class Mezcla:
    por_clase: dict[str, float]           # montos (pesos de cartera) por clase, con transparencia
    rv_local: float
    rv_sic: float
    rv_directo_acciones: float            # acciones/FIBRAs en directo (sin ETFs)
    en_fondos: float                      # monto en acciones de otros fondos
    notas: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(self.por_clase.values())

    def pct(self, clase: str) -> float:
        return self.por_clase.get(clase, 0.0) / self.total if self.total else 0.0

    @property
    def pct_rv(self) -> float:
        return sum(self.pct(c) for c in CLASES_RV)


def mezcla(c: Cartera, hermanas: dict[str, Cartera], _prof: int = 0, excluir: frozenset[str] = frozenset()) -> Mezcla:
    """Mezcla por clase. Las acciones de otros fondos se transparentan con la
    cartera del fondo subyacente (mismo corte o el más reciente anterior), salvo las
    de `excluir` (fondos hermanos analizados: ya cuentan en su propia cifra)."""
    por = {k: 0.0 for k in CLASES}
    loc = sic = directo = en_fondos = 0.0
    notas: list[str] = []
    for p in c.posiciones:
        if p.categoria is Categoria.FONDO:
            en_fondos += p.valor_razonable
            if (p.fondo_subyacente or "") in excluir:
                continue
            sub = hermanas.get(p.fondo_subyacente or "")
            if sub is not None and _prof < 3 and sub.fondo_clave != c.fondo_clave:
                m = mezcla(sub, hermanas, _prof + 1)
                if m.total:
                    f = p.valor_razonable / m.total
                    for k in CLASES:
                        por[k] += m.por_clase[k] * f
                    loc += m.rv_local * f
                    sic += m.rv_sic * f
                    directo += m.rv_directo_acciones * f
                    continue
            # Sin cartera del subyacente: se asigna por tipo de fondo (e).
            clase = RV_LOCAL if p.tipo_valor.startswith("52") else RF
            por[clase] += p.valor_razonable
            if clase == RV_LOCAL:
                loc += p.valor_razonable
            notas.append(f"{p.emisora_raw}: subyacente sin cartera, asignado a {clase} (e)")
            continue
        por[p.clase] += p.valor_razonable
        if p.clase in CLASES_RV:
            if p.mercado == MERCADO_SIC:
                sic += p.valor_razonable
            else:
                loc += p.valor_razonable
            if p.categoria in (Categoria.ACCION_LOCAL, Categoria.FIBRA, Categoria.ACCION_SIC):
                directo += p.valor_razonable
    return Mezcla(por, loc, sic, directo, en_fondos, notas)


# ---------------------------------------------------------------- rotación
@dataclass
class Rotacion:
    corte_a: date
    corte_b: date
    meses: float
    compras: float
    ventas: float
    base: float                # exposición RV promedio
    anual: float               # piso anualizado
    instrumentos: int
    sin_titulos: float         # monto RV que no se pudo seguir (agregados / sin títulos)


def _libro_rv(c: Cartera) -> tuple[dict[str, tuple[float, float, str]], float, float, dict[str, float]]:
    """Libro de RV por instrumento: (títulos, valor, tipo de valor). Devuelve también,
    por tipo de valor, el monto que la cartera reporta en renglones agregados sin emisora."""
    libro: dict[str, tuple[float, float, str]] = {}
    excluido = 0.0
    total = 0.0
    agregados: dict[str, float] = {}
    for p in c.posiciones:
        if p.clase not in CLASES_RV:
            continue
        total += p.valor_razonable
        if p.es_agregado or not p.titulos:
            excluido += p.valor_razonable
            if p.es_agregado:
                agregados[p.tipo_valor] = agregados.get(p.tipo_valor, 0.0) + p.valor_razonable
            continue
        t, v, _ = libro.get(p.clave_instrumento, (0.0, 0.0, p.tipo_valor))
        libro[p.clave_instrumento] = (t + p.titulos, v + p.valor_razonable, p.tipo_valor)
    return libro, total, excluido, agregados


def rotacion_observada(a: Cartera, b: Cartera) -> Rotacion:
    """Si una cartera agrupa un tipo de valor en renglones sin emisora (Multiva,
    Compass) y la otra lo desglosa (CNBV R7), un instrumento que solo aparece en la
    desglosada puede estar dentro del agregado: no se cuenta uno por uno. Pero el
    agregado acota cuánto pudo quedarse: lo que excede su valor es operación segura
    (ventas seguras >= Σ omitidas en A − agregado en B; simétrico para compras)."""
    if b.fecha_corte <= a.fecha_corte:
        raise ValueError("corte_b debe ser posterior a corte_a")
    la, ta, xa, ga = _libro_rv(a)
    lb, tb, xb, gb = _libro_rv(b)
    compras = ventas = 0.0
    omitidas_a: dict[str, float] = {}
    omitidas_b: dict[str, float] = {}
    for k in sorted(set(la) | set(lb)):
        if k not in la and lb[k][2] in ga:
            omitidas_b[lb[k][2]] = omitidas_b.get(lb[k][2], 0.0) + lb[k][1]
            continue
        if k not in lb and la[k][2] in gb:
            omitidas_a[la[k][2]] = omitidas_a.get(la[k][2], 0.0) + la[k][1]
            continue
        t_a, v_a, _ = la.get(k, (0.0, 0.0, ""))
        t_b, v_b, _ = lb.get(k, (0.0, 0.0, ""))
        precio = v_b / t_b if t_b else (v_a / t_a if t_a else 0.0)
        delta = (t_b - t_a) * precio
        if delta > 0:
            compras += delta
        else:
            ventas += -delta
    ventas += sum(max(0.0, v - gb.get(tv, 0.0)) for tv, v in omitidas_a.items())
    compras += sum(max(0.0, v - ga.get(tv, 0.0)) for tv, v in omitidas_b.items())
    meses = (b.fecha_corte - a.fecha_corte).days / DIAS_MES
    # Base: exposición RV promedio escalada a activo neto (para fondos de RV ≈ activo neto).
    base = ((ta / a.total_cartera * a.activo_neto if a.total_cartera else 0.0)
            + (tb / b.total_cartera * b.activo_neto if b.total_cartera else 0.0)) / 2
    anual = ((compras + ventas) / 2) / base * (12 / meses) if base and meses else 0.0
    return Rotacion(a.fecha_corte, b.fecha_corte, meses, compras, ventas, base, anual,
                    len(set(la) | set(lb)), max(xa, xb))


@dataclass
class BandaRotacion:
    minimo: float
    maximo: float
    puntual: float | None       # solo con >= N cortes
    cortes: int
    medida: bool                # False => supuesto (e)
    pares: list[Rotacion]

    @property
    def media(self) -> float:
        """Punto medio de la banda; se usa para la bolsa. No cambia de definición al
        llegar a N cortes (la cifra puntual es solo para mostrar)."""
        return (self.minimo + self.maximo) / 2


def piso_encadenado(pares: list[Rotacion]) -> float:
    """Piso de rotación anual sobre una cadena de cortes consecutivos:
    Σ (compras+ventas)/2  /  Σ (base × meses/12), es decir, el promedio de los pisos
    de cada tramo ponderado por exposición × meses. Es >= que comparar directo el
    primer corte contra el último (lo operado nunca es menor que la suma de los
    cambios netos de cada tramo); no es >= que cualquier tramo aislado."""
    operado = sum((r.compras + r.ventas) / 2 for r in pares)
    exposicion = sum(r.base * r.meses / 12 for r in pares)
    return operado / exposicion if exposicion else 0.0


def banda_rotacion(serie: list[Cartera], prm: Parametros) -> BandaRotacion:
    serie = sorted(serie, key=lambda c: c.fecha_corte)
    pares = [rotacion_observada(a, b) for a, b in zip(serie, serie[1:])]
    # Base mínima: 1 % del activo neto promedio (evita pisos de 12x sobre 0.5 mdp).
    pares = [r for r, (a, b) in zip(pares, zip(serie, serie[1:]))
             if r.base > 0.01 * (a.activo_neto + b.activo_neto) / 2 and r.meses <= prm.max_meses_par]
    if not pares:
        return BandaRotacion(prm.sin_medicion_min, prm.sin_medicion_max, None, len(serie), False, [])
    piso = piso_encadenado(pares)
    # Solo cortes de fin de mes cuentan para pasar de banda a cifra puntual.
    mensuales = {c for r in pares for c in (r.corte_a, r.corte_b)
                 if next(x for x in serie if x.fecha_corte == c).tipo_doc in ("cartera_mensual", "cnbv_r7")}
    puntual = piso if len(mensuales) >= prm.cortes_para_cifra else None
    return BandaRotacion(piso, piso * prm.multiplicador_techo, puntual, len(pares) + 1, True, pares)


# -------------------------------------------------------------- por fondo
@dataclass
class MetricasFondo:
    clave: str
    nombre_corto: str
    nombre_legal: str
    tipo_fondo: str
    categoria: str
    categoria_regulatoria: str
    fecha_corte: date
    activo_neto: float
    activo_neto_estimado: bool
    total_cartera: float
    mezcla: Mezcla
    es_fondo_de_fondos: bool
    rv_min: float | None
    rv_max: float | None
    rotacion: BandaRotacion
    cartera: Cartera
    dici: Dici | None
    discrepancias: list[str] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    historia: list[Cartera] = field(default_factory=list)
    en_hermanos: float = 0.0   # valor en acciones de fondos hermanos analizados (excluido)

    @property
    def factor_propio(self) -> float:
        return 1 - self.en_hermanos / self.total_cartera if self.total_cartera else 1.0

    @property
    def activo_neto_propio(self) -> float:
        """Activo neto sin las acciones de fondos hermanos (que ya cuentan en el subyacente)."""
        return self.activo_neto * self.factor_propio

    # montos escalados a activo neto propio
    def _monto(self, pct: float) -> float:
        return self.activo_neto_propio * pct

    @property
    def pct_rv(self) -> float:
        return self.mezcla.pct_rv

    @property
    def pct_rf(self) -> float:
        return self.mezcla.pct(RF)

    @property
    def pct_efe(self) -> float:
        return self.mezcla.pct(EFE)

    @property
    def exposicion_rv(self) -> float:
        return self._monto(self.pct_rv)

    @property
    def monto_rf(self) -> float:
        return self._monto(self.pct_rf)

    @property
    def monto_efe(self) -> float:
        return self._monto(self.pct_efe)

    @property
    def share_local(self) -> float:
        t = self.mezcla.rv_local + self.mezcla.rv_sic
        return self.mezcla.rv_local / t if t else 0.0

    @property
    def headroom(self) -> float | None:
        if self.rv_max is None:
            return None
        return max(0.0, self.rv_max - self.pct_rv) * self.activo_neto_propio

    def importe_anual(self, rot: float) -> float:
        return self.exposicion_rv * rot * 2

    def bolsa(self, rot: float, prm: Parametros) -> float:
        imp = self.importe_anual(rot)
        return imp * self.share_local * prm.comision_local + imp * (1 - self.share_local) * prm.comision_sic

    def bolsa_banda(self, prm: Parametros) -> tuple[float, float]:
        return self.bolsa(self.rotacion.minimo, prm), self.bolsa(self.rotacion.maximo, prm)


def es_fondo_de_fondos(c: Cartera, umbral: float) -> bool:
    en_fondos = sum(p.valor_razonable for p in c.posiciones if p.categoria is Categoria.FONDO)
    return c.total_cartera > 0 and en_fondos / c.total_cartera >= umbral


def dici_para(dicis: list[Dici], clave: str, corte: date) -> Dici | None:
    cand = [d for d in dicis if d.fondo_clave == clave]
    if not cand:
        return None
    previos = [d for d in cand if d.fecha_doc and (d.fecha_doc.year, d.fecha_doc.month) <= (corte.year, corte.month)]
    return max(previos or cand, key=lambda d: d.fecha_doc or date.min)


def metricas_fondo(c: Cartera, hermanas: dict[str, Cartera], historia: list[Cartera],
                   dici: Dici | None, prm: Parametros, conciliaciones: list[dict] | None = None,
                   excluir_hermanos: bool = True) -> MetricasFondo:
    fdf = es_fondo_de_fondos(c, prm.umbral_fondo_de_fondos)
    # Un fondo que no es FdF pero tiene acciones de fondos hermanos: esa parte se excluye
    # (doble conteo y no genera ejecución). El FdF se transparenta completo (se excluye entero).
    hermanos = frozenset(k for k in hermanas if k != c.fondo_clave) if (excluir_hermanos and not fdf) else frozenset()
    m = mezcla(c, hermanas, excluir=hermanos)
    en_hermanos = sum(p.valor_razonable for p in c.posiciones
                      if p.categoria is Categoria.FONDO and (p.fondo_subyacente or "") in hermanos)
    rv_min = dici.rv_min if dici else None
    rv_max = dici.rv_max if dici else None
    notas = list(c.notas) + m.notas
    if c.tipo_fondo == "RV" and rv_max == 0:
        notas.append("Régimen: el prospecto no mostró renglones de RV en un fondo de RV; límite [POR CONFIRMAR]")
        rv_min = rv_max = None
    if rv_max is not None and m.pct_rv > rv_max + 0.02:
        # El régimen no se estima con la composición; solo se descarta una lectura
        # imposible (el fondo tiene más RV que el máximo leído).
        notas.append(f"Régimen: máximo leído {rv_max:.0%} menor que la RV que tiene el fondo "
                     f"({m.pct_rv:.1%}); lectura descartada [POR CONFIRMAR]")
        rv_min = rv_max = None
    disc: list[str] = []
    # Solo se comparan documentos del mismo mes (un DICI de octubre no se contrasta
    # contra una cartera de septiembre).
    if (dici and dici.composicion_total and dici.fecha_doc
            and (dici.fecha_doc.year, dici.fecha_doc.month) == (c.fecha_corte.year, c.fecha_corte.month)):
        dif = abs(dici.composicion_total - c.total_cartera) / c.total_cartera
        if dif > prm.umbral_discrepancia:
            disc.append(
                f"Total de cartera: {c.total_cartera:,.0f} según {c.procedencia.cita()} vs "
                f"{dici.composicion_total:,.0f} según {dici.procedencia.cita()} ({dif:.1%})"
            )
    if dici:
        disc.extend(n for n in dici.notas if n.startswith("Comisiones serie"))
    for k in conciliaciones or []:
        if k["fecha"][:7] != c.fecha_corte.isoformat()[:7] or not k["monto_b"]:
            continue
        dif = abs(k["monto_a"] - k["monto_b"]) / k["monto_b"]
        if dif > prm.umbral_discrepancia:
            disc.append(
                f"{k['concepto'].capitalize()}: {k['monto_a']:,.0f} según {k['cita_a']} vs "
                f"{k['monto_b']:,.0f} según {k['cita_b']} ({dif:.1%})"
            )
    return MetricasFondo(
        clave=c.fondo_clave, nombre_corto=c.nombre_corto, nombre_legal=c.nombre_legal,
        tipo_fondo=c.tipo_fondo, categoria=c.categoria,
        categoria_regulatoria=(dici.categoria_regulatoria if dici else c.categoria),
        fecha_corte=c.fecha_corte, activo_neto=c.activo_neto, activo_neto_estimado=c.activo_neto_estimado,
        total_cartera=c.total_cartera, mezcla=m,
        es_fondo_de_fondos=fdf,
        rv_min=rv_min, rv_max=rv_max,
        rotacion=banda_rotacion([h for h in historia if h.fecha_corte <= c.fecha_corte], prm),
        cartera=c, dici=dici, discrepancias=disc, notas=notas,
        historia=[h for h in historia if h.fecha_corte <= c.fecha_corte],
        en_hermanos=en_hermanos,
    )


# ----------------------------------------------------------- por operadora
def escala(valor: float, cortes: list[float]) -> int:
    """1 por debajo del primer corte; +1 por cada corte alcanzado (máx. 5)."""
    return 1 + sum(1 for c in cortes if valor >= c)


@dataclass
class Calificacion:
    bolsa: float
    independencia: float
    ajuste: float
    recurrencia: float
    headroom: float
    friccion: float
    total: float
    tier: str
    veto: bool
    provisional: bool = False     # rotación sin medir en > la mitad de la exposición RV: no puede ser Tier 1


@dataclass
class MetricasOperadora:
    clave: str
    nombre: str
    corte: date
    perfil: PerfilOperadora | None
    fondos: list[MetricasFondo]                 # analizados (sin FdF ni NO DISPONIBLE)
    excluidos_fdf: list[MetricasFondo]
    no_disponibles: list[tuple[str, str]]
    corte_previo: date | None
    activo_neto_previo: float | None             # mismos fondos que en el corte actual
    activo_neto_comparable: float | None = None  # activo neto actual de esos mismos fondos
    sin_cartera: list[tuple[str, str]] = field(default_factory=list)       # administrados sin cartera del corte
    calibracion: tuple[date, float, float] | None = None                    # total cartera vs activo neto CNBV

    @property
    def activo_neto(self) -> float:
        """Suma sin doble conteo: excluye acciones de fondos hermanos."""
        return sum(f.activo_neto_propio for f in self.fondos)

    @property
    def en_hermanos(self) -> float:
        return sum(f.activo_neto - f.activo_neto_propio for f in self.fondos)

    @property
    def exposicion_rv(self) -> float:
        return sum(f.exposicion_rv for f in self.fondos)

    @property
    def monto_rf(self) -> float:
        return sum(f.monto_rf for f in self.fondos)

    @property
    def monto_efe(self) -> float:
        return sum(f.monto_efe for f in self.fondos)

    @property
    def fondos_con_rv(self) -> list[MetricasFondo]:
        return [f for f in self.fondos if f.exposicion_rv > 0]

    @property
    def headroom(self) -> float:
        return sum(f.headroom or 0.0 for f in self.fondos)

    def bolsa_banda(self, prm: Parametros) -> tuple[float, float]:
        b = [f.bolsa_banda(prm) for f in self.fondos]
        return sum(x for x, _ in b), sum(y for _, y in b)

    def bolsa_media(self, prm: Parametros) -> float:
        return sum(f.bolsa(f.rotacion.media, prm) for f in self.fondos)

    def importe_banda(self) -> tuple[float, float]:
        return (sum(f.importe_anual(f.rotacion.minimo) for f in self.fondos),
                sum(f.importe_anual(f.rotacion.maximo) for f in self.fondos))

    def ingreso_esperado(self, prm: Parametros) -> tuple[float, float]:
        sup = prm.supuestos(self.clave, self.perfil.casa_de_bolsa_hermana if self.perfil else None)
        p = sup.probabilidad_de_alta if sup else 0.0
        lo, hi = self.bolsa_banda(prm)
        return lo * prm.captura_objetivo * p, hi * prm.captura_objetivo * p

    def rotacion_ponderada(self) -> tuple[float, bool]:
        """Rotación media ponderada por exposición RV; bool = ¿toda medida?"""
        con = [f for f in self.fondos if f.exposicion_rv > 0]
        tot = sum(f.exposicion_rv for f in con)
        if not tot:
            return 0.0, False
        return sum(f.rotacion.media * f.exposicion_rv for f in con) / tot, all(f.rotacion.medida for f in con)

    @property
    def pct_directo(self) -> float:
        rv = sum(f.mezcla.rv_local + f.mezcla.rv_sic for f in self.fondos)
        d = sum(f.mezcla.rv_directo_acciones for f in self.fondos)
        return d / rv if rv else 0.0

    @property
    def momentum(self) -> float | None:
        """Crecimiento MENSUAL del activo neto de los mismos fondos entre el corte previo
        y el actual (comparable entre operadoras con ventanas distintas). Incluye
        rendimiento de mercado, no solo flujos."""
        if not self.activo_neto_previo or not self.activo_neto_comparable or not self.corte_previo:
            return None
        meses = (self.corte - self.corte_previo).days / DIAS_MES
        if meses <= 0:
            return None
        return (self.activo_neto_comparable / self.activo_neto_previo) ** (1 / meses) - 1

    def fraccion_rotacion_medida(self) -> float:
        con = [f for f in self.fondos if f.exposicion_rv > 0]
        tot = sum(f.exposicion_rv for f in con)
        return sum(f.exposicion_rv for f in con if f.rotacion.medida) / tot if tot else 0.0

    def calificacion(self, prm: Parametros) -> Calificacion:
        s_bolsa = escala(self.bolsa_media(prm), prm.bolsa_cortes)
        hermana = self.perfil.casa_de_bolsa_hermana if self.perfil else None
        s_ind = 1 if hermana else (5 if hermana is False else 3)
        s_aj = round(1 + 4 * self.pct_directo, 1)
        rot, _ = self.rotacion_ponderada()
        s_rec = escala(rot, prm.rotacion_cortes)
        # Headroom: solo sobre fondos con régimen conocido; sin ninguno, neutral (3).
        con_reg = [f for f in self.fondos if f.rv_max is not None and f.exposicion_rv > 0]
        exp_reg = sum(f.exposicion_rv for f in con_reg)
        s_head = escala(sum(f.headroom or 0.0 for f in con_reg) / exp_reg, prm.headroom_cortes) if exp_reg else 3
        mom = self.momentum   # mensual
        s_mom = 3 if mom is None else (5 if mom >= 0.015 else 4 if mom >= 0 else 2 if mom >= -0.015 else 1)
        s_hm = (s_head + s_mom) / 2
        sup = prm.supuestos(self.clave, self.perfil.casa_de_bolsa_hermana if self.perfil else None)
        s_fr = sup.friccion_alta if sup else 3
        w = prm.pesos
        total = (w["bolsa"] * s_bolsa + w["independencia"] * s_ind + w["ajuste"] * s_aj
                 + w["recurrencia"] * s_rec + w["headroom"] * s_hm + w["friccion"] * s_fr)
        veto = bool(hermana)
        provisional = self.fraccion_rotacion_medida() < 0.5
        if total >= prm.tier1_min and not veto and not provisional:
            tier = "Tier 1"
        elif total >= prm.tier2_min:
            tier = "Tier 2"
        else:
            tier = "Tier 3"
        return Calificacion(s_bolsa, s_ind, s_aj, s_rec, s_hm, s_fr, total, tier, veto, provisional)
