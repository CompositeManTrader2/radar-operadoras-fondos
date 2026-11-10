"""Pruebas de las correcciones de docs/revision_modelo.md."""
from dataclasses import replace
from datetime import date

import pytest

from radar.config import cargar_parametros
from radar.core.metricas import (
    BandaRotacion, MetricasOperadora, banda_rotacion, metricas_fondo, rotacion_observada,
)
from radar.core.modelo import EFE, RV_LOCAL, RV_SIC, Cartera, Categoria, PerfilOperadora, Posicion, Procedencia
from radar.pipeline import _aplicar_alias, _posible_alias, alias_fondos


def _p(em, titulos, valor, clase=RV_LOCAL, cat=Categoria.ACCION_LOCAL, tv="1", agregado=False, sub=None):
    return Posicion(f"{tv}_{em}_*", tv, em, "*", titulos, valor, None, "", "", "", cat,
                    Procedencia("x", "f.pdf", 1, date(2026, 9, 30)), es_agregado=agregado,
                    emisora_canonica=em, clase=clase, mercado="LOCAL" if clase == RV_LOCAL else "SIC",
                    fondo_subyacente=sub)


def _c(fecha, pos, clave="F1", tipo="cartera_mensual"):
    tot = sum(p.valor_razonable for p in pos)
    return Cartera("op", clave, "X, Fondo de Inversión de Renta Variable", "", fecha, tipo, tot, False, tot, pos,
                   Procedencia("x", "f.pdf", 1, fecha), tipo_fondo="RV")


def test_ventas_seguras_con_renglon_agregado():
    """B agrupa '1ASP' en 100: de 500 que desaparecieron, al menos 400 se vendieron."""
    a = _c(date(2026, 8, 31), [_p("AAA", 10, 300, RV_SIC, Categoria.ACCION_SIC, "1ASP"),
                               _p("BBB", 10, 200, RV_SIC, Categoria.ACCION_SIC, "1ASP"),
                               _p("CCC", 10, 500)])
    b = _c(date(2026, 9, 30), [_p("OTROS-1ASP", None, 100, RV_SIC, Categoria.ACCION_SIC, "1ASP", agregado=True),
                               _p("CCC", 10, 500)])
    r = rotacion_observada(a, b)
    assert r.ventas == pytest.approx(400) and r.compras == 0


def test_excluye_tenencias_en_fondos_hermanos_sin_doble_conteo():
    prm = cargar_parametros()
    sub = _c(date(2026, 9, 30), [_p("AAA", 1, 1000)], clave="SUB")
    holder = _c(date(2026, 9, 30), [_p("SUB", 1, 200, None, Categoria.FONDO, "52", sub="SUB"),
                                    _p("BBB", 1, 800)], clave="HOLD")
    f = metricas_fondo(holder, {"SUB": sub, "HOLD": holder}, [holder], None, prm)
    assert not f.es_fondo_de_fondos
    assert f.en_hermanos == 200
    assert f.activo_neto_propio == pytest.approx(800)
    assert f.exposicion_rv == pytest.approx(800)  # solo lo propio; SUB ya cuenta sus 1,000


def test_media_no_salta_al_llegar_a_seis_cortes():
    b = BandaRotacion(0.4, 0.6, 0.4, 6, True, [])
    assert b.media == pytest.approx(0.5)


def test_base_minima_descarta_pisos_sobre_exposicion_testimonial():
    prm = cargar_parametros()
    deuda = [_p("BONO", 1, 99_500, None, Categoria.DEUDA)]
    for p in deuda:
        p.clase = "RF"
    a = _c(date(2026, 8, 31), deuda + [_p("ETF", 10, 500)])
    b = _c(date(2026, 9, 30), deuda + [_p("ETF", 0, 0)])
    assert not banda_rotacion([a, b], prm).medida  # 0.5 % del activo: no se reporta como medida


def _operadora(fondos, hermana=False, previo=None):
    return MetricasOperadora("op", "Op", date(2026, 9, 30), PerfilOperadora("op", "Op", "", "", hermana, ""),
                             fondos, [], [], previo[0] if previo else None, previo[1] if previo else None,
                             previo[2] if previo else None)


def test_calificacion_provisional_no_puede_ser_tier1():
    prm = replace(cargar_parametros(), tier1_min=0.0)
    f = metricas_fondo(_c(date(2026, 9, 30), [_p("AAA", 1, 1000)]), {}, [], None, prm)
    assert not f.rotacion.medida
    q = _operadora([f]).calificacion(prm)
    assert q.provisional and q.tier != "Tier 1"


def test_momentum_mensual_con_los_mismos_fondos():
    prm = cargar_parametros()
    f = metricas_fondo(_c(date(2026, 9, 30), [_p("AAA", 1, 1000)]), {}, [], None, prm)
    m = _operadora([f], previo=(date(2026, 7, 31), 1000.0, 1100.0))  # +10 % en 2 meses
    assert m.momentum == pytest.approx(1.1 ** (1 / ((date(2026, 9, 30) - date(2026, 7, 31)).days / 30.4375)) - 1)


def test_alias_cnbv_y_deteccion_por_traslape():
    assert alias_fondos("finaccess")["AXESCSD"] == "AXESCOB"
    c = _c(date(2026, 8, 31), [_p("A", 1, 1), _p("B", 1, 1), _p("C", 1, 1)], clave="AXESCSD")
    assert _aplicar_alias(c, {"AXESCSD": "AXESCOB"}).fondo_clave == "AXESCOB"
    propia = _c(date(2026, 9, 10), [_p("A", 2, 2), _p("B", 2, 2), _p("C", 2, 2), _p("D", 1, 1)], clave="OTRO")
    assert _posible_alias(_c(date(2026, 8, 31), [_p("A", 1, 1), _p("B", 1, 1), _p("C", 1, 1)], clave="X"),
                          {"OTRO": propia}) == ("OTRO", 1.0)
