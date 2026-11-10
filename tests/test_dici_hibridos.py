"""Operadoras híbridas (cartera CNBV + DICI propio): Principal, Skandia, Franklin y SURA.
DICI REALES en tests/fixtures/hibridos."""
import pytest

from conftest import doc, FIX
from radar.adapters import REGISTRO
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.adapters.dici.franklin import documentos_desde_json
from radar.adapters.dici.sura import series_publicadas

D = FIX / "hibridos"


def _dici(op, nombre):
    return REGISTRO[op].parsear_dici(D / nombre, doc(D / nombre, op, None, "dici"), None)


@pytest.mark.parametrize("op", ["blackrock", "sura", "principal", "franklin", "skandia", "nafinsa"])
def test_registradas_como_hibridas(op):
    assert isinstance(REGISTRO[op], AdaptadorCnbvConDici)


def test_principal_urls_por_clave():
    d = {(x.fondo_clave, x.tipo): x.url for x in REGISTRO["principal"].documentos(None, ["PRINRVA", "PRINR25", "PRINLS1"])}
    assert d[("PRINRVA", "dici")] == "https://principal.com.mx/PRINRVA-DICI"
    assert d[("PRINR25", "dici")] == "https://principal.com.mx/PRINR25DICI"
    assert d[("PRINR25", "prospecto")].endswith("/prospectoparticularlifecycle")
    assert d[("PRINLS1", "prospecto")].endswith("/prospectoparticular")


def test_principal_dici_y_distribuidoras_de_terceros():
    x = _dici("principal", "PRINRVA_dici.pdf")
    assert x.fondo_clave == "PRINRVA" and x.fecha_doc.isoformat() == "2026-10-30" and len(x.series) == 16
    s = {v.serie: v for v in x.series}
    assert s["EC"].comision_administracion == pytest.approx(0.0053) and s["EC"].costo_total == pytest.approx(0.0202)
    assert any("Actinver Casa de Bolsa" in e for e in x.distribuidoras)
    assert any(e.startswith("GBM Grupo Bursátil Mexicano") for e in x.distribuidoras)
    p = REGISTRO["principal"].perfil([x])
    assert p.casa_de_bolsa_hermana is False and "DISCREPANCIA" not in p.evidencia_casa_de_bolsa


def test_skandia_dos_carpetas_y_solo_la_operadora_distribuye():
    (dici, _pros) = REGISTRO["skandia"].documentos(None, ["SK-GUB"])
    assert "RENTA%20VARIABLE/SK-GUB/DICI_SK-GUB.pdf" in dici.url and "DEUDA/SK-GUB" in dici.alternativas[0]
    x = _dici("skandia", "SK-RVMX_dici.pdf")
    assert x.fondo_clave == "SK-RVMX" and len(x.series) == 3 and x.fecha_doc.isoformat() == "2026-10-30"
    assert len(x.distribuidoras) == 1 and x.distribuidoras[0].startswith("Skandia Operadora de Fondos")


def test_franklin_lista_desde_el_json_y_dici():
    datos = {"document": [
        {"dctermsTitle": "Documento Clave - FT-MEXA", "dctermsDescription": "Documento Clave",
         "frkReferenceDate": "2026-10-30", "downloadUrl": "https://w.example/nuevo.pdf"},
        {"dctermsTitle": "Documento Clave - FT-MEXA", "dctermsDescription": "Documento Clave",
         "frkReferenceDate": "2025-10-30", "downloadUrl": "https://w.example/viejo.pdf"},
        {"dctermsTitle": "Cartera Mensual - FT-REAL, Cartera Mensual", "dctermsDescription": "Cartera Mensual",
         "frkReferenceDate": "2026-10-30", "downloadUrl": "https://w.example/c.pdf"},
    ]}
    docs = documentos_desde_json(datos, ["FT-MEXA", "FT-REAL"])
    d = {(x.fondo_clave, x.tipo): x for x in docs}
    assert d[("FT-MEXA", "dici")].url == "https://w.example/nuevo.pdf"  # el más reciente
    assert d[("FT-REAL", "dici")].url == "" and d[("FT-REAL", "dici")].opcional  # no publicado: aviso agregado
    x = _dici("franklin", "FT-MEXA_dici.pdf")
    assert x.fondo_clave == "FT-MEXA" and len(x.series) == 13 and x.fecha_doc.isoformat() == "2026-10-30"


def test_sura_series_del_arbol_de_rendimientos_y_dici():
    arbol = {"result": {"rendimientosFondos": [{"rendimientos": [{"rendimientos": [
        {"fondo": "SUR-FIB", "serie": " BM1"}, {"fondo": "SUR-FIB", "serie": " BM2"}, {"fondo": "SURRVMX", "serie": "BF0"}]}]}]}}
    assert series_publicadas(arbol) == {"SUR-FIB": "BM1", "SURRVMX": "BF0"}
    x = _dici("sura", "SURRVMX_dici.pdf")
    assert x.fondo_clave == "SURRVMX" and x.fecha_doc.isoformat() == "2026-10-31" and len(x.series) == 16
    assert x.distribuidoras and x.distribuidoras[0].startswith("SURA Investment Management México")
    assert (x.rv_min, x.rv_max) == (0.9, 1.0) and x.fuente_regimen.pagina == 1  # tabla Min./Max. de la portada


def test_fondo_de_deuda_no_hereda_rv_de_acciones_de_fondos():
    from radar.adapters.formato_dici import rv_coherente

    notas = []
    assert rv_coherente("Largo Plazo General (IDLP)", 0.9, 1.0, notas) == (None, None) and "fondo de deuda" in notas[0]
    assert rv_coherente("Discrecional (RVDIS)", 0.0, 1.0, []) == (0.0, 1.0)
    assert rv_coherente("Corto Plazo IDCP", 0.0, 0.0, []) == (0.0, 0.0)


def test_nafinsa_indice_y_ficha():
    from radar.adapters.dici.nafinsa import documentos_de_ficha, fondos_del_indice

    indice = (D / "nafinsa_indice.html").read_bytes().decode("utf-8", "replace")
    assert fondos_del_indice(indice) == [1, 2, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15]
    ficha = (D / "nafinsa_ficha_9.html").read_bytes().decode("utf-8", "replace")
    # Tres DICI (físicas 1647, morales 1648, no sujetas 2040) y la nota metodológica (1767, no es DICI).
    assert documentos_de_ficha(ficha) == ("NAFINDX", "1647", "2302")


def test_nafinsa_dici_sin_nombre_de_serie_en_comisiones():
    """Clase y serie "F / PF1"; la tabla de comisiones solo dice "Serie más representativa"
    sobre la segunda columna: esta serie es la otra."""
    x = _dici("nafinsa", "NAFINDX_pf_dici.pdf")
    assert x.fondo_clave == "NAFINDX" and [s.serie for s in x.series] == ["PF1", "PF2", "PF3"]
    s = {v.serie: v for v in x.series}
    assert s["PF1"].comision_administracion == pytest.approx(0.002365) and s["PF1"].costo_total == pytest.approx(0.00252)
    assert x.distribuidoras == ["Operadora de Fondos Nafinsa, S.A. de C.V., Sociedad Operadora de Fondos de Inversión"]
    assert REGISTRO["nafinsa"].perfil([x]).casa_de_bolsa_hermana is False
