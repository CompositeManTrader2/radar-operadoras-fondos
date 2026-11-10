"""BlackRock México: híbrido (cartera CNBV + DICI y prospecto propios). DICI REALES."""
import pytest

from conftest import doc, FIX
from radar.adapters import REGISTRO
from radar.adapters.base import regimen_prospecto
from radar.adapters.dici.blackrock import BlackRock, slug
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici

D = FIX / "blackrock"


def _dici(nombre, prospecto=None):
    ad = REGISTRO["blackrock"]
    p = (D / prospecto, doc(D / prospecto, "blackrock", None, "prospecto")) if prospecto else None
    return ad.parsear_dici(D / nombre, doc(D / nombre, "blackrock", None, "dici"), p)


def test_registrado_como_hibrido():
    ad = REGISTRO["blackrock"]
    assert isinstance(ad, BlackRock) and isinstance(ad, AdaptadorCnbvConDici) and ad.clave_cnbv == "IMPFOND"


def test_documentos_con_respaldo_en_citi():
    docs = REGISTRO["blackrock"].documentos(None, ["BLKEM1", "BLKLIQ+", "BLK2030"])
    d = {(x.fondo_clave, x.tipo): x for x in docs}
    em = d[("BLKEM1", "dici")]
    assert em.url.endswith("/fact-sheet/blkem1-dici.pdf") and em.alternativas[0].endswith(
        "/BLKEM1_DocumentoClaveActualizacionAnual.pdf") and em.opcional
    assert d[("BLKLIQ+", "prospecto")].url.endswith("/blkliqp-prospecto.pdf") and slug("GOLD1+") == "gold1p"
    assert d[("BLK2030", "prospecto")].url.endswith("/lifepath-prospecto.pdf")


def test_dici_comisiones_sin_signo_y_series_entre_comillas():
    x = _dici("BLKEM1_dici.pdf")
    assert x.fondo_clave == "BLKEM1" and x.fecha_doc.isoformat() == "2026-02-28"
    assert x.categoria_regulatoria == "RVESACCINT" and x.indice_referencia == "MSCI Emerging Markets Index"
    s = {v.serie: v for v in x.series}
    assert len(s) == 9
    assert s["B1-A"].comision_administracion == pytest.approx(0.0046) and s["B1-A"].costo_total == pytest.approx(0.014)
    assert s["B1-D"].comision_administracion == pytest.approx(0.0061) and s["B1-D"].costo_total == pytest.approx(0.0185)


def test_distribuidoras_en_dos_columnas_y_sin_casa_de_bolsa_hermana():
    x = _dici("BLKEM1_dici.pdf")
    assert x.distribuidoras == [
        "Banco Nacional de México, S.A., integrante del Grupo Financiero Banamex",
        "Banco Citi México, S.A., Institución de Banca Múltiple, Grupo Financiero Citi México",
        "Citi México Casa de Bolsa, S.A. de C.V., Grupo Financiero Citi México",
    ]
    p = REGISTRO["blackrock"].perfil([x])
    assert p.casa_de_bolsa_hermana is False and "Citi México Casa de Bolsa" in p.evidencia_casa_de_bolsa
    assert "DISCREPANCIA" not in p.evidencia_casa_de_bolsa


def test_fuente_truetype_cmap_12_no_truena():
    """BLKUSEQ: pdfminer no implementa el cmap TrueType formato 12 (AssertionError)."""
    x = _dici("BLKUSEQ_dici.pdf", "BLKUSEQ_prospecto.pdf")
    assert x.fondo_clave == "BLKUSEQ" and len(x.series) == 9
    assert (x.rv_min, x.rv_max) == (0.8, 1.0)


def test_regimen_por_incisos_con_cifras_en_renglon_propio():
    mn, mx, pagina, fuente = regimen_prospecto(D / "BLKUSEQ_prospecto.pdf")
    assert (mn, mx, fuente) == (0.8, 1.0, "tabla de parámetros")
