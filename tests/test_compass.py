from datetime import date

import pytest

from conftest import FIX, doc
from radar.adapters.base import entes_por_forma_juridica
from radar.adapters.compass import Compass, secciones_de_fondo
from radar.core.clasificacion import EtfNoClasificado, clasificar_cartera
from radar.core.modelo import EFE, RF, RV_LOCAL, Categoria
from radar.core.validacion import validar_cuadre

A = Compass()
DIR = FIX / "compass"


def _cartera(nombre, clave):
    r = DIR / nombre
    return A.parsear_cartera(r, doc(r, "compass", clave, "cartera_mensual"))


def test_cartera_colrvl_formato_publicaciones():
    c = clasificar_cartera(_cartera("COMPASSCOLRVLPublicaciones20260930.pdf", "COLRVL"))
    assert c.fecha_corte == date(2026, 9, 30)
    validar_cuadre(c, 0.001)
    assert c.total_cartera == pytest.approx(285_812_178.68)
    bbajio = next(p for p in c.posiciones if p.emisora == "BBAJIO")
    assert (bbajio.tipo_valor, bbajio.serie, bbajio.titulos, bbajio.clase) == ("41", "O", 229_816, RV_LOCAL)
    # Columnas ubicadas con los datos: el desfase encabezado/datos difiere de Multiva.
    q = next(p for p in c.posiciones if p.emisora == "Q")
    assert q.serie == "*" and q.calificacion == "ALTA"
    assert next(p for p in c.posiciones if p.emisora == "FMTY").categoria is Categoria.FIBRA


def test_i_liqg_rescata_renglon_con_texto_encimado():
    """El PDF encima la etiqueta del renglón agregado IQ sobre sus cifras; sin el
    rescate por carácter el cuadre falla por 301.7 mdp (3.1 %)."""
    c = clasificar_cartera(_cartera("COMPASSI+LIQGPublicaciones20260930.pdf", "I+LIQG"))
    validar_cuadre(c, 0.001)
    iq = next(p for p in c.posiciones if p.emisora == "OTROS-IQ")
    assert (iq.titulos, iq.valor_razonable, iq.clase) == (3_000_000, 301_694_548.00, RF)
    assert "rescatadas por carácter" in iq.nota


def test_agregado_de_etfs_sin_referencia_no_se_adivina():
    c = _cartera("COMPASSI+GLOBVPublicaciones20260930.pdf", "I+GLOBV")
    assert any(p.es_agregado and p.categoria is Categoria.ETF_EXTRANJERO for p in c.posiciones)
    with pytest.raises(EtfNoClasificado, match="agregado"):
        clasificar_cartera(c, referencia=None)


def test_dici_colrvl_y_regimen_por_letra():
    r, p = DIR / "DICI_COLRVL_1026.pdf", DIR / "Prospecto_20_COLRVL_-_Act_Marzo_2026.pdf"
    d = A.parsear_dici(r, doc(r, "compass", "COLRVL", "dici"), (p, doc(p, "compass", "COLRVL", "prospecto")))
    assert d.fecha_doc == date(2026, 10, 31)
    b = next(s for s in d.series if s.serie == "B-E1")
    assert (b.comision_administracion, b.costo_total) == (pytest.approx(0.008), pytest.approx(0.00915))
    assert (d.rv_min, d.rv_max) == (0.95, 1.0)   # c.1 Acciones … 95 % – 100 %
    assert d.indice_referencia.startswith("S&P/")
    assert d.liquidez == "Diario" and d.limite_recompra == "5%"


def test_dici_inconsistente_del_emisor_se_reporta_no_se_oculta():
    r = DIR / "DICI_I+USD_1026.pdf"
    d = A.parsear_dici(r, doc(r, "compass", "I+USD", "dici"), None)
    fc = next(s for s in d.series if s.serie == "B-FC")
    assert fc.costo_total == pytest.approx(0.00864)  # se conserva el Total publicado
    assert any("B-FC" in n and "suman" in n for n in d.notas)


def test_distribuidoras_en_lista_corrida_y_sin_casa_de_bolsa_hermana():
    r = DIR / "DICI_I+GLOBV_1026.pdf"
    d = A.parsear_dici(r, doc(r, "compass", "I+GLOBV", "dici"), None)
    assert "Casa de Bolsa Ve Por Mas, S.A. de C.V." in d.distribuidoras
    assert not any(x.startswith("Casa") and "Compass" in x for x in d.distribuidoras)
    assert A.perfil([d]).casa_de_bolsa_hermana is False


def test_separacion_de_entes_no_confunde_casa_con_sa():
    t = ("Compass Investments de México, S.A. de C.V., S.O.F.I., Casa de Bolsa Ve Por Mas, S.A. de C.V., "
         "Grupo Bursátil Mexicano S.A. de C.V. Casa de Bolsa, Operadora Covaf, S.A. de C.V., "
         "Sociedad Operadora Limitada de Fondos de Inversión. N/A")
    assert entes_por_forma_juridica(t) == [
        "Compass Investments de México, S.A. de C.V., S.O.F.I.",
        "Casa de Bolsa Ve Por Mas, S.A. de C.V.",
        "Grupo Bursátil Mexicano S.A. de C.V. Casa de Bolsa",
        "Operadora Covaf, S.A. de C.V., Sociedad Operadora Limitada de Fondos de Inversión.",
        "N/A",
    ]


def test_descubrimiento_pagina_de_fondo():
    html = (DIR / "fondo_colrvl.html").read_text(encoding="utf-8")
    secc = secciones_de_fondo(html, "https://latam.vincicompass.com")
    assert any(u.endswith("COMPASSCOLRVLPublicaciones20260930.pdf") for u in secc["cartera_mensual"])
    assert any(u.endswith("DICI_COLRVL_1026.pdf") for u in secc["dici"])
    fondos, docs = A.descubrir_desde_html({"colrvl": html})
    assert [f.clave for f in fondos] == ["COLRVL"]
    assert {d.tipo for d in docs} == {"cartera_mensual", "dici", "prospecto", "prospecto_generico"}
    assert all(not d.nombre_archivo.startswith("X Montos") for d in docs)
