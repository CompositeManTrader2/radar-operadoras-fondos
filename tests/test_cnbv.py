from datetime import date

import pytest

from conftest import FIX, doc
from radar.config import cargar_parametros
from radar.core.clasificacion import clasificar_cartera
from radar.core.metricas import piso_encadenado, rotacion_observada
from radar.core.modelo import EFE, RV_LOCAL, Categoria
from radar.fuentes import cnbv
from radar.pipeline import construir_metricas

R7 = FIX / "cnbv" / "R7_2026_muestra.xlsx"
R1 = FIX / "cnbv" / "R1_2026_S2_muestra.xlsx"


def _r7():
    d = doc(R7, "cnbv", None, "cnbv_r7")
    return cnbv.carteras_r7(cnbv.leer_minfo(R7), "finaccess", "FACCESS", d)


def test_r7_cartera_axesbmv():
    (c,) = _r7()
    clasificar_cartera(c)
    assert c.fondo_clave == "AXESBMV" and c.fecha_corte == date(2026, 8, 31) and c.tipo_doc == "cnbv_r7"
    assert len(c.posiciones) == 20
    gm = next(p for p in c.posiciones if p.emisora == "GMEXICO")
    assert (gm.serie, gm.titulos, gm.valor_razonable) == ("B", 431_658, 100_843_942)
    rep = next(p for p in c.posiciones if p.categoria is Categoria.REPORTO)
    assert rep.clase == EFE  # reporto = efectivo, aunque el título sea un Bondes
    assert next(p for p in c.posiciones if p.emisora == "NAFTRAC").clase == RV_LOCAL
    assert c.total_cartera == pytest.approx(754_594_619, abs=1)
    assert "hoja MINFO fila" in gm.procedencia.cita()


def test_r1_activo_neto_oficial():
    d = doc(R1, "cnbv", None, "cnbv_r1")
    (an,) = cnbv.activos_r1(cnbv.leer_minfo(R1), "FACCESS", d)
    assert (an.fondo, an.fecha, an.activo_neto) == ("AXESBMV", date(2026, 8, 31), pytest.approx(754_352_923.36))


def test_store_prioriza_cartera_de_la_operadora_en_el_mismo_mes(entorno, tmp_path):
    from radar.store.db import Store

    store = Store(tmp_path / "s.sqlite")
    (c,) = _r7()
    clasificar_cartera(c)
    assert store.guardar_cartera(c)
    otra = _r7()[0]
    clasificar_cartera(otra)
    otra.tipo_doc, otra.fecha_corte = "cartera_mensual", date(2026, 8, 28)
    store.guardar_cartera(otra)  # la mensual de la operadora desplaza a R7 del mismo mes
    assert [x.tipo_doc for x in store.carteras("finaccess")] == ["cartera_mensual"]
    assert not store.guardar_cartera(c)  # y R7 ya no entra como corte de ese mes


def test_pipeline_usa_r7_como_corte_y_r1_como_activo_neto(entorno):
    store, prm = entorno
    ago = store.carteras("finaccess", date(2026, 8, 31))
    bmv = next(c for c in ago if c.fondo_clave == "AXESBMV")
    assert bmv.tipo_doc == "cnbv_r7" and not bmv.activo_neto_estimado
    assert bmv.activo_neto == pytest.approx(754_352_923.36)
    m = construir_metricas("finaccess", date(2026, 10, 30), store, prm)
    f = next(x for x in m.fondos if x.clave == "AXESBMV")
    assert [r.corte_a for r in f.rotacion.pares] == [date(2026, 8, 31), date(2026, 9, 10)]
    assert f.rotacion.minimo == pytest.approx(piso_encadenado(f.rotacion.pares))
    assert f.discrepancias == []  # R7 vs R1 difieren 0.03 %


def test_multiva_rotacion_medida_y_calibracion(entorno):
    store, prm = entorno
    m = construir_metricas("multiva", date(2026, 10, 30), store, prm)
    pc = next(x for x in m.fondos if x.clave == "MULTIPC")
    assert pc.rotacion.medida and pc.rotacion.pares[0].corte_a == date(2026, 8, 31)
    # ORBIA, NEMAK, TLEVISA… vienen desglosadas en R7 y agrupadas en el PDF:
    # no cuentan como ventas.
    assert pc.rotacion.pares[0].ventas < 5_000_000
    assert m.calibracion is not None and m.calibracion[0] == date(2026, 8, 31)
    assert abs(m.calibracion[1]) < 0.01


def test_piso_encadenado_es_mas_ajustado_que_el_par_largo():
    from radar.core.modelo import Cartera, Posicion, Procedencia

    def c(f, t):
        p = Posicion("1_A_*", "1", "A", "*", t, t * 10.0, None, "", "", "", Categoria.ACCION_LOCAL,
                     Procedencia("x", "f", 1, f), emisora_canonica="A", clase=RV_LOCAL, mercado="LOCAL")
        return Cartera("op", "F", "", "", f, "cartera_mensual", t * 10.0, False, t * 10.0, [p],
                       Procedencia("x", "f", 1, f))

    a, b, d = c(date(2026, 7, 31), 100), c(date(2026, 8, 31), 150), c(date(2026, 9, 30), 100)
    largo = rotacion_observada(a, d)       # cambio neto 0: no ve nada
    tramos = [rotacion_observada(a, b), rotacion_observada(b, d)]
    assert largo.anual == 0
    assert piso_encadenado(tramos) > 0
