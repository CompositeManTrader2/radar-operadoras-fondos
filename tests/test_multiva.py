from datetime import date

import pytest

from conftest import FIX, doc
from radar.adapters.multiva import Multiva
from radar.core.clasificacion import clasificar_cartera
from radar.core.modelo import ADMINISTRADO, EFE, NO_DISPONIBLE, RV_ETF, RV_LOCAL, Categoria
from radar.core.validacion import validar_cuadre

A = Multiva()
DIR = FIX / "multiva"


def _cartera(nombre, clave):
    r = DIR / nombre
    return clasificar_cartera(A.parsear_cartera(r, doc(r, "multiva", clave, "cartera_mensual")))


def test_cartera_multipc_cuadra_con_renglones_agregados():
    c = _cartera("OPMULTIMULTIPCPublicaciones20261030.pdf", "MULTIPC")
    assert c.fecha_corte == date(2026, 10, 30)
    assert c.nombre_legal.startswith("MULTIAS")
    validar_cuadre(c, 0.001)
    assert c.total_cartera == pytest.approx(284_519_872.33)
    assert c.activo_neto_estimado  # Multiva no publica activo neto (e)
    agregado = next(p for p in c.posiciones if p.emisora == "OTROS-1")
    assert agregado.es_agregado and agregado.clase == RV_LOCAL
    assert agregado.valor_razonable == pytest.approx(41_842_838.14)
    otros = next(p for p in c.posiciones if p.emisora == "OTROS-VALORES")
    assert otros.clase == EFE
    gm = next(p for p in c.posiciones if p.emisora == "GMEXICO")
    assert (gm.serie, gm.titulos, gm.calificacion) == ("B", 130_501, "ALTA")
    # Fila partida en dos Y (calificación 1 pt arriba) se reconstruye completa.
    wal = next(p for p in c.posiciones if p.emisora == "WALMEX")
    assert wal.calificacion == "ALTA" and wal.titulos == 328_261
    rep = next(p for p in c.posiciones if p.categoria is Categoria.REPORTO)
    assert rep.clase == EFE


def test_cartera_multieq_tracks_extranjeros():
    c = _cartera("OPMULTIMULTIEQPublicaciones20261030.pdf", "MULTIEQ")
    validar_cuadre(c, 0.001)
    etfs = {p.emisora: p for p in c.posiciones if p.clase == RV_ETF}
    assert set(etfs) == {"VOO", "SPY", "IWM"}
    assert etfs["VOO"].titulos == 86_946


def test_dici_multipc_con_prospecto_y_casa_de_bolsa_hermana():
    r, p = DIR / "202610_MULTIPC.pdf", DIR / "MULTIPC_2026.pdf"
    d = A.parsear_dici(r, doc(r, "multiva", "MULTIPC", "dici"), (p, doc(p, "multiva", "MULTIPC", "prospecto")))
    assert d.fondo_clave == "MULTIPC"
    assert d.categoria_regulatoria.startswith("RVESACC")
    be1 = next(s for s in d.series if s.serie == "BE-1")
    assert be1.comision_administracion == pytest.approx(0.0090)
    assert be1.costo_total == pytest.approx(0.0313)
    bm1 = next(s for s in d.series if s.serie == "BM-1")
    assert bm1.costo_total == pytest.approx(0.0188)
    assert (d.rv_min, d.rv_max) == (0.8, 1.0)
    assert d.composicion_total == pytest.approx(284_520_000)  # DICI en miles
    assert A.perfil([d]).casa_de_bolsa_hermana is True
    assert any("Casa de Bolsa Multiva" in x for x in d.distribuidoras)


def test_prospecto_generico_es_la_verdad():
    nombres = A.nombres_en_generico(DIR / "MULTIVA GENERICO VIGENTE 2026.pdf")
    assert len(nombres) == 12
    assert "multias" in nombres and "fondo de inversion estrategia platino" in nombres


def test_descubrimiento_web_vs_documentos():
    fondos, docs = A.descubrir_desde_html((DIR / "fondos.html").read_text(encoding="utf-8"))
    por = {f.clave: f for f in fondos}
    assert por["MVESG"].estatus == NO_DISPONIBLE   # en la web, sin documentos
    assert por["SUR2026"].estatus == NO_DISPONIBLE  # de terceros: solo distribuido
    assert por["MULTIPC"].estatus == ADMINISTRADO
    assert set(por["MULTIPC"].urls) == {"cartera_mensual", "dici", "prospecto"}
    assert sum(1 for d in docs if d.tipo == "cartera_mensual") == 12
    assert any(d.tipo == "prospecto_generico" for d in docs)


def test_confirmar_universo_contra_generico():
    c = _cartera("OPMULTIMULTIPCPublicaciones20261030.pdf", "MULTIPC")
    fondos, _ = A.descubrir_desde_html((DIR / "fondos.html").read_text(encoding="utf-8"))
    fondos = A.confirmar_universo(fondos, {"MULTIPC": c}, DIR / "MULTIVA GENERICO VIGENTE 2026.pdf")
    por = {f.clave: f for f in fondos}
    assert por["MULTIPC"].estatus == ADMINISTRADO
    assert por["MULTIEQ"].estatus == NO_DISPONIBLE  # sin cartera parseada en este test
