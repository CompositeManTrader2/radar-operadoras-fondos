from datetime import date

import pytest

from radar.core.clasificacion import (
    EtfNoClasificado, canonica, clasificar_posicion, diccionario_etfs, nombre_emisora_sic,
)
from radar.core.modelo import EFE, POR_CONFIRMAR, RF, RV_ETF, RV_LOCAL, RV_SIC, Categoria, Posicion, Procedencia


def pos(emisora, cat, tv="1ISP"):
    return Posicion(f"{tv}_{emisora}_*", tv, emisora, "*", 1, 100.0, 0.1, "", "", "", cat,
                    Procedencia("x", "f.pdf", 1, date(2026, 10, 30)))


@pytest.mark.parametrize("t", ["IB01", "IBTA", "VDST", "SHV", "BIL", "FLOT", "IEF", "IBGS"])
def test_etf_de_deuda_es_renta_fija(t):
    p = pos(t, Categoria.ETF_EXTRANJERO)
    clasificar_posicion(p, "test")
    assert p.clase == RF


@pytest.mark.parametrize("t", ["VOO", "SPY", "IWM", "VGT", "QQQM", "ACWI", "EEM", "RING", "ESGU"])
def test_etf_de_renta_variable(t):
    p = pos(t, Categoria.ETF_EXTRANJERO)
    clasificar_posicion(p, "test")
    assert p.clase == RV_ETF and p.mercado == "SIC"


def test_etf_local_de_deuda_es_rf():
    p = pos("IB1MXX", Categoria.ETF_LOCAL, tv="1B")
    clasificar_posicion(p, "test")
    assert p.clase == RF


def test_etf_sin_clasificar_falla():
    with pytest.raises(EtfNoClasificado, match="ZZZZ"):
        clasificar_posicion(pos("ZZZZ", Categoria.ETF_EXTRANJERO), "test")


def test_reporto_es_efectivo_no_deuda():
    p = pos("BPAG91", Categoria.REPORTO, tv="IQ")
    clasificar_posicion(p, "test")
    assert p.clase == EFE


def test_accion_sic_y_local():
    a = pos("AAPL", Categoria.ACCION_SIC, tv="1ASP")
    b = pos("FEMSA", Categoria.ACCION_LOCAL, tv="1")
    clasificar_posicion(a, "t")
    clasificar_posicion(b, "t")
    assert (a.clase, b.clase) == (RV_SIC, RV_LOCAL)


@pytest.mark.parametrize("raw", ["FEMSA UBD", "1_FEMSA_UBD", "1ASP_FEMSA", "FEMSA"])
def test_emisora_canonica(raw):
    assert canonica(raw) == "FEMSA"


def test_sic_no_confirmada_no_se_inventa():
    assert nombre_emisora_sic("0JN9") == POR_CONFIRMAR
    assert nombre_emisora_sic("AAPL") == "Apple"


def test_diccionario_sin_duplicados_y_subyacentes_validos():
    d = diccionario_etfs()
    assert set(d.values()) <= {"RV", "DEUDA", "MATERIA_PRIMA"}
    assert d["NAFTRAC"] == "RV"


def test_fondo_extranjero_56sp_por_subyacente():
    """56SP = fondo extranjero vía SIC. La CNBV lo llama "de deuda", pero hay de renta variable."""
    from datetime import date as _d
    from radar.core.clasificacion import clasificar_posicion, fondo_extranjero_por_confirmar
    from radar.core.modelo import RF, RV_ETF, Categoria, Posicion, Procedencia

    def p(em):
        return Posicion(f"56SP_{em}_LX", "56SP", em, "LX", 10, 100.0, None, "", "", "", Categoria.DEUDA,
                        Procedencia("x", "r7.xlsm", 1, _d(2026, 9, 30)))

    rv, deuda, mixto, nada = p("AMEGFMU"), p("TEMGBIA"), p("BGDHIX2"), p("ZZZZ56")
    for x in (rv, deuda, mixto, nada):
        clasificar_posicion(x, "t")
    assert (rv.clase, rv.categoria) == (RV_ETF, Categoria.ETF_EXTRANJERO)      # AM SURA Equity Global
    assert deuda.clase == RF                                                    # Templeton Global Bond
    assert mixto.clase == RV_ETF and "(e)" in mixto.nota
    assert nada.clase == RF and "[POR CONFIRMAR]" in nada.nota
    assert fondo_extranjero_por_confirmar("ZZZZ56") and fondo_extranjero_por_confirmar("CGCG")
    assert not fondo_extranjero_por_confirmar("AMEGFMU")
