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


@pytest.mark.parametrize("op", ["blackrock", "sura", "principal", "franklin", "skandia", "nafinsa", "kapital"])
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
    assert rv_coherente("Largo Plazo General (IDLP)", 0.9, 1.0, notas) == (0.0, 0.0) and "fondo de deuda" in notas[0]
    assert rv_coherente("Discrecional (RVDIS)", 0.0, 1.0, []) == (0.0, 1.0)
    assert rv_coherente("Corto Plazo IDCP", 0.0, 0.0, []) == (0.0, 0.0)
    notas = ["Régimen: no se encontró la tabla de parámetros en el prospecto [POR CONFIRMAR]"]
    assert rv_coherente("GUBERNAMENTAL (IDCPGUB)", None, None, notas) == (0.0, 0.0)
    assert notas == ["Régimen: fondo de deuda (GUBERNAMENTAL (IDCPGUB)), sin renta variable por categoría"]


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


def test_kapital_buscador_de_fondos():
    from radar.adapters.dici.kapital import serie_representativa, series_por_fondo, url_archivo

    html = ('<option value="0"> SELECCIONA FONDO </option><option value="275">+TASA F1</option>'
            '<option value="280">+TASA F2</option><option value="1049">+TASA AHO1</option>'
            '<option value="900">KPTLGLO M1</option>')
    f = series_por_fondo(html)
    assert set(f) == {"+TASA", "KPTLGLO"}
    assert serie_representativa(f["+TASA"]) == ("F1", "275") and serie_representativa(f["KPTLGLO"]) == ("M1", "900")
    assert url_archivo("/Fondos/Documentos/DocumentoTASAD1F1.pdf").endswith(
        "a.php?archivo=%2FFondos%2FDocumentos%2FDocumentoTASAD1F1.pdf")


def test_kapital_dici_clave_con_etiqueta_y_regimen_min_max():
    """Kapital: 'Clave de Pizarra: KPTLGLO' en la misma línea; tabla de régimen con 'MIN MÁX'."""
    pros = D / "KPTLGLO_prospecto.pdf"
    x = REGISTRO["kapital"].parsear_dici(D / "KPTLGLO_dici.pdf", doc(D / "KPTLGLO_dici.pdf", "kapital", "KPTLGLO", "dici"),
                                         (pros, doc(pros, "kapital", "KPTLGLO", "prospecto")))
    assert x.fondo_clave == "KPTLGLO" and x.categoria_regulatoria == "DISCRECIONAL (RVDIS)"
    assert x.fecha_doc.isoformat() == "2026-10-31" and (x.rv_min, x.rv_max) == (0.5, 1.0)
    s = x.series[0]
    assert s.serie == "F1" and s.comision_administracion == pytest.approx(0.007) and s.costo_total == pytest.approx(0.038)
    p = REGISTRO["kapital"].perfil([x])
    assert p.casa_de_bolsa_hermana is True and "Kapital México Casa de Bolsa" in p.evidencia_casa_de_bolsa


def test_kapital_dici_con_clave_anterior_usa_la_de_la_cnbv():
    f = D / "KPTLMPG_dici_clave_anterior.pdf"
    x = REGISTRO["kapital"].parsear_dici(f, doc(f, "kapital", "KPTLMPG", "dici"), None)
    assert x.fondo_clave == "KPTLMPG" and any("+TASAMX" in n for n in x.notas)
    assert (x.rv_min, x.rv_max) == (0.0, 0.0)  # fondo de deuda: sin RV por categoría


def test_kapital_cartera_mensual_clave_por_marcadores_y_reportos_por_seccion():
    from radar.adapters import formato_kapital
    from radar.core.modelo import Categoria
    from radar.core.validacion import validar_cuadre

    f = D / "kapital_cartera_mensual_2026-09.pdf"
    assert formato_kapital.claves_por_pagina(f) == {1: "+TASA", 2: "+TASAA1", 3: "+TASACP", 4: "+TASAPR",
                                                    5: "KPTLGLO", 6: "KPTLMPG", 7: "KPTLUSD"}
    cs = {c.fondo_clave: c for c in REGISTRO["kapital"].parsear_cartera(f, doc(f, "kapital", None, "cartera_mensual"))}
    assert len(cs) == 7 and all(c.fecha_corte.isoformat() == "2026-09-30" for c in cs.values())
    for c in cs.values():
        validar_cuadre(c, 0.001)                       # cada fondo cuadra contra su TOTAL CARTERA
        assert all(p.titulos is None for p in c.posiciones)
    tasa = cs["+TASA"]
    assert tasa.total_cartera == pytest.approx(4_908_063_185) and tasa.activo_neto == pytest.approx(4_902_223_233)
    assert all(p.categoria is Categoria.REPORTO for p in tasa.posiciones)   # LF/IS bajo "Reportos"
    usd = cs["KPTLUSD"]
    assert {p.categoria for p in usd.posiciones} == {Categoria.ETF_EXTRANJERO, Categoria.DEUDA, Categoria.DEPOSITO}
    assert cs["KPTLGLO"].tipo_fondo == "RV" and cs["+TASA"].tipo_fondo == "RF"


def test_r7_sustituye_cartera_de_la_operadora_sin_titulos(tmp_path):
    from datetime import date
    from radar.core.modelo import RV_LOCAL, Cartera, Categoria, Posicion, Procedencia
    from radar.store.db import Store

    def cartera(tipo, titulos):
        p = Posicion("1_AMX_*", "1", "AMX", "*", titulos, 100.0, None, "", "", "", Categoria.ACCION_LOCAL,
                     Procedencia("x", "f.pdf", 1, date(2026, 9, 30)), emisora_canonica="AMX", clase=RV_LOCAL)
        return Cartera("kapital", "F1", "", "", date(2026, 9, 30), tipo, 100.0, False, 100.0, [p],
                       Procedencia("x", "f.pdf", 1, date(2026, 9, 30)))

    s = Store(tmp_path / "r.sqlite")
    s.guardar_cartera(cartera("cartera_mensual", None))
    assert s.cartera_sin_titulos("kapital", "F1", "2026-09-30")
    s.borrar_cartera("kapital", "F1", "2026-09-30")
    assert s.guardar_cartera(cartera("cnbv_r7", 10.0))
    assert not s.cartera_sin_titulos("kapital", "F1", "2026-09-30")
