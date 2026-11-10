from dataclasses import replace
from datetime import date

import pytest

from radar.config import cargar_parametros
from radar.core.metricas import (
    MetricasOperadora, banda_rotacion, es_fondo_de_fondos, mezcla, rotacion_observada,
)
from radar.core.modelo import (
    EFE, RF, RV_LOCAL, Cartera, Categoria, PerfilOperadora, Posicion, Procedencia,
)
from radar.pipeline import construir_metricas


def _p(em, titulos, valor, clase=RV_LOCAL, cat=Categoria.ACCION_LOCAL, f=date(2026, 9, 30), sub=None, tv="1"):
    return Posicion(f"1_{em}_*", tv, em, "*", titulos, valor, None, "", "", "", cat,
                    Procedencia("x", "f.pdf", 1, f), emisora_canonica=em, clase=clase,
                    mercado="LOCAL" if clase == RV_LOCAL else None, fondo_subyacente=sub)


def _c(fecha, posiciones, clave="F1", an=None):
    tot = sum(p.valor_razonable for p in posiciones)
    return Cartera("op", clave, "X, Fondo de Inversión de Renta Variable", "", fecha, "cartera_mensual",
                   an or tot, False, tot, posiciones, Procedencia("x", "f.pdf", 1, fecha), tipo_fondo="RV")


def test_rotacion_observada_formula():
    a = _c(date(2026, 8, 31), [_p("AAA", 100, 1000), _p("BBB", 50, 1000)])
    # AAA: +20 títulos a precio 12 => compra 240; BBB vendida toda a precio previo 20 => venta 1000
    b = _c(date(2026, 9, 30), [_p("AAA", 120, 1440), _p("CCC", 10, 500)])
    r = rotacion_observada(a, b)
    assert r.compras == pytest.approx(240 + 500)
    assert r.ventas == pytest.approx(1000)
    base = (2000 + 1940) / 2
    meses = 30 / 30.4375
    assert r.anual == pytest.approx(((740 + 1000) / 2) / base * 12 / meses)


def test_banda_no_puntual_con_menos_de_seis_cortes():
    prm = cargar_parametros()
    serie = [_c(date(2026, m, 28), [_p("AAA", 100 + m, 1000)]) for m in (7, 8, 9)]
    b = banda_rotacion(serie, prm)
    assert b.medida and b.puntual is None and b.cortes == 3
    assert b.maximo >= b.minimo


def test_sin_medicion_usa_banda_supuesta():
    prm = cargar_parametros()
    b = banda_rotacion([_c(date(2026, 9, 30), [_p("AAA", 1, 1)])], prm)
    assert not b.medida and (b.minimo, b.maximo) == (prm.sin_medicion_min, prm.sin_medicion_max)


def test_fondo_de_fondos_y_transparencia():
    sub = _c(date(2026, 9, 30), [_p("AAA", 1, 600), _p("BONO", 1, 400, clase=RF, cat=Categoria.DEUDA)], clave="SUB")
    fdf = _c(date(2026, 9, 30), [_p("SUB", 10, 900, clase=None, cat=Categoria.FONDO, sub="SUB", tv="52"),
                                 _p("REP", 1, 100, clase=EFE, cat=Categoria.REPORTO)], clave="FDF")
    assert es_fondo_de_fondos(fdf, 0.5)
    m = mezcla(fdf, {"SUB": sub})
    assert m.por_clase[RV_LOCAL] == pytest.approx(540)
    assert m.por_clase[RF] == pytest.approx(360)
    assert m.por_clase[EFE] == pytest.approx(100)


def test_veto_casa_de_bolsa_hermana_no_permite_tier1(entorno):
    store, prm = entorno
    m = construir_metricas("finaccess", date(2026, 10, 30), store, prm)
    q = m.calificacion(prm)
    assert q.independencia == 5 and not q.veto
    vetada = replace(m, perfil=PerfilOperadora("x", "x", "", "", True, ""))
    prm_max = replace(prm, tier1_min=0.0, tier2_min=0.0)
    qv = vetada.calificacion(prm_max)
    assert qv.veto and qv.independencia == 1 and qv.tier != "Tier 1"


def test_rotacion_real_finaccess_axesbmv(entorno):
    store, prm = entorno
    m = construir_metricas("finaccess", date(2026, 10, 30), store, prm)
    bmv = next(f for f in m.fondos if f.clave == "AXESBMV")
    # Tres cortes: R7 CNBV (31-ago), cartera "diaria" (10-sep) y mensual (30-oct).
    assert bmv.rotacion.medida and len(bmv.rotacion.pares) == 2
    par = bmv.rotacion.pares[-1]
    assert (par.corte_a, par.corte_b) == (date(2026, 9, 10), date(2026, 10, 30))
    assert 0 < bmv.rotacion.minimo < 5
    assert bmv.rotacion.puntual is None  # banda, no cifra, con < 6 cortes
    assert bmv.rv_max == 1.0 and bmv.headroom == pytest.approx((1.0 - bmv.pct_rv) * bmv.activo_neto)


def test_discrepancia_mayor_al_umbral_se_muestra(entorno):
    store, prm = entorno
    m = construir_metricas("finaccess", date(2026, 10, 30), store, prm)
    bmv = next(f for f in m.fondos if f.clave == "AXESBMV")
    assert bmv.discrepancias == []  # DICI y cartera coinciden
    from radar.core.metricas import metricas_fondo
    bmv.dici.composicion_total = bmv.total_cartera * 1.2
    f = metricas_fondo(bmv.cartera, {}, [bmv.cartera], bmv.dici, prm)
    assert len(f.discrepancias) == 1 and "20.0%" in f.discrepancias[0]
