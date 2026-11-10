from datetime import date

import pytest

from conftest import FIX, doc
from radar.adapters.finaccess import Finaccess
from radar.config import cargar_parametros
from radar.core.clasificacion import clasificar_cartera
from radar.core.modelo import ADMINISTRADO, DISTRIBUIDO, EFE, RF, RV_ETF, RV_LOCAL, Categoria
from radar.core.validacion import ErrorCuadre, validar_cuadre

A = Finaccess()
DIR = FIX / "finaccess"


def _cartera(nombre, clave, tipo="cartera_mensual"):
    r = DIR / nombre
    return A.parsear_cartera(r, doc(r, "finaccess", clave, tipo))


def test_cartera_mensual_axesbmv_cuadra_y_valores_puntuales():
    c = _cartera("cartera_mensual_axesbmv_2026-10-30.pdf", "AXESBMV")
    assert c.fecha_corte == date(2026, 10, 30)
    assert c.fondo_clave == "AXESBMV" and c.tipo_fondo == "RV"
    assert len(c.posiciones) == 20
    assert c.total_cartera == 832_683_562 and c.activo_neto == 832_471_167
    validar_cuadre(c, cargar_parametros().tolerancia_cuadre)
    gm = next(p for p in c.posiciones if p.emisora == "GMEXICO")
    # Fila reconstruida por coordenadas: títulos, valor y % de la MISMA fila.
    assert (gm.titulos, gm.valor_razonable, gm.pct_cartera) == (440_758, 98_866_426.98, pytest.approx(0.119))
    assert any(p.emisora == "PE&OLES" for p in c.posiciones)  # clave real de Peñoles en BMV


def test_clasificacion_reporto_es_efectivo_y_naftrac_local():
    c = clasificar_cartera(_cartera("cartera_mensual_axesbmv_2026-10-30.pdf", "AXESBMV"))
    rep = next(p for p in c.posiciones if p.categoria is Categoria.REPORTO)
    assert rep.clase == EFE
    naftrac = next(p for p in c.posiciones if p.emisora == "NAFTRAC")
    assert naftrac.clase == RV_LOCAL and naftrac.mercado == "LOCAL"
    fibra = next(p for p in c.posiciones if p.categoria is Categoria.FIBRA)
    assert fibra.clase == RV_LOCAL


def test_axesglo_etfs_clasificados_por_subyacente():
    c = clasificar_cartera(_cartera("cartera_mensual_axesglo_2026-10-30.pdf", "AXESGLO"))
    etfs = [p for p in c.posiciones if p.categoria is Categoria.ETF_EXTRANJERO]
    assert len(etfs) == 26 and all(p.clase == RV_ETF for p in etfs)
    dep = next(p for p in c.posiciones if p.categoria is Categoria.DEPOSITO)
    assert dep.clase == EFE  # depósito USD overnight


def test_cuadre_falla_y_dice_que_fondo():
    c = _cartera("cartera_mensual_axesbmv_2026-10-30.pdf", "AXESBMV")
    c.posiciones.pop(3)  # simula una posición omitida por el parser
    with pytest.raises(ErrorCuadre, match="AXESBMV"):
        validar_cuadre(c, 0.001)


def test_dici_comisiones_por_serie_sin_intercalado():
    r = DIR / "DICI_AXESBMV_2026-10.pdf"
    p = DIR / "ProspEspecificoAXESBMV.pdf"
    d = A.parsear_dici(r, doc(r, "finaccess", "AXESBMV", "dici"), (p, doc(p, "finaccess", "AXESBMV", "prospecto")))
    assert d.fecha_doc == date(2026, 10, 31)
    assert d.categoria_regulatoria == "Discrecional (RVDIS)"
    e1 = next(s for s in d.series if s.serie == "E1")
    # E1 y la serie representativa F1 comparten tabla: 'Otras/Valuación' difieren
    # (0.0113 % vs 0.0110 %). Si se intercalaran, el total sería 1.6362 %.
    assert e1.comision_administracion == pytest.approx(0.014987)
    assert e1.costo_total == pytest.approx(0.016365)
    assert e1.monto_minimo == "$2.00"
    assert len(d.series) == 10
    assert (d.rv_min, d.rv_max) == (0.6, 1.0)  # régimen: lo que PUEDE tener
    assert d.fuente_regimen.pagina == 6
    assert "Actinver Casa de Bolsa S.A. De C.V." in d.distribuidoras
    assert d.liquidez == "Diaria" and d.limite_recompra == "10%"
    assert d.indice_referencia.startswith("S&P/BMV IPC")
    assert d.composicion_total == 832_683_562


def test_perfil_sin_casa_de_bolsa_hermana():
    r = DIR / "DICI_AXESBMV_2026-10.pdf"
    d = A.parsear_dici(r, doc(r, "finaccess", "AXESBMV", "dici"), None)
    assert A.perfil([d]).casa_de_bolsa_hermana is False


def test_descubrimiento_desde_home():
    fondos, docs = A.descubrir_desde_html((DIR / "home.html").read_text(encoding="utf-8"))
    propios = [f for f in fondos if f.estatus == ADMINISTRADO]
    assert len(propios) == 15
    assert {f.clave for f in fondos if f.estatus == DISTRIBUIDO} >= {"TEMGBIA", "SCOTUSA"}
    cp = next(f for f in fondos if f.clave == "AXESCP")
    assert cp.nombre_comercial == "Deuda Local - Corto Plazo"
    assert cp.urls["cartera_mensual"].endswith("/PDF/cartera_mensual_axescp.pdf")
    assert cp.urls["dici"].endswith("/PDF/DICI_AXESCP.pdf")
    assert len(docs) == 15 * 4
