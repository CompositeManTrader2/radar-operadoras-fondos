from datetime import date

import pytest

from conftest import doc, FIX
from radar.adapters import REGISTRO
from radar.config import cargar_parametros
from radar.core.modelo import Categoria
from radar.core.tipos_valor import categoria_por_tv, es_derivado
from radar.fuentes import cnbv
from radar.fuentes.cnbv import FilaMinfo
from radar.pipeline import EtfsPendientes, etfs_sin_clasificar


def test_registro_cubre_todas_las_operadoras_de_la_cnbv():
    assert len(REGISTRO) == 29
    claves = {a.clave_cnbv for a in REGISTRO.values()}
    assert {"FACCESS", "OPMULTI", "SEICOMP", "IMPFOND", "OPGBM", "OPBBVAG"} <= claves
    assert len(claves) == 29  # sin duplicados


def test_perfil_desde_padron():
    assert REGISTRO["blackrock"].perfil([]).casa_de_bolsa_hermana is False
    gbm = REGISTRO["gbm"].perfil([])
    assert gbm.casa_de_bolsa_hermana is True and "GBM Casa de Bolsa" in gbm.evidencia_casa_de_bolsa


def _fila(n, **d):
    base = {"periodo": 202608, "operadora": "XOP", "fondo": "F1", "tipo de fondo": "Renta Variable",
            "tipo de inversion": "Inversión en Directo", "tv": "1", "tipo valor": "", "emisora": "AMX",
            "serie": "B", "titulos": 10, "valor a mercado total": 100.0}
    base.update(d)
    return FilaMinfo(n, base)


def test_r7_excluye_derivados_y_clasifica_garantias():
    filas = [
        _fila(1),
        _fila(2, tv="SWP", emisora="SWAP1", valor_a=0, **{"valor a mercado total": -5.0,
                                                            "tipo de inversion": "Inversiones en instrumentos financieros derivados"}),
        _fila(3, tv="AIM", emisora="SANTCME", **{"tipo de inversion": "Garantías en val por inversiones en inst financ derivados",
                                                 "valor a mercado total": 3.0}),
    ]
    d = doc(FIX / "cnbv" / "R7_2026_muestra.xlsx", "cnbv", None, "cnbv_r7")
    (c,) = cnbv.carteras_r7(filas, "x", "XOP", d)
    assert c.total_cartera == 103.0                    # el derivado no entra a la mezcla
    assert any("Derivados excluidos" in n for n in c.notas)
    assert next(p for p in c.posiciones if p.emisora == "SANTCME").categoria is Categoria.DEPOSITO


@pytest.mark.parametrize("tv,cat", [("YYSP", Categoria.ACCION_SIC), ("FE", Categoria.FIBRA), ("CHE", Categoria.DEPOSITO),
                                    ("MP", Categoria.DEUDA), ("1S", Categoria.ACCION_LOCAL)])
def test_tipos_de_valor_del_catalogo_cnbv(tv, cat):
    assert categoria_por_tv(tv, "t") is cat


def test_derivados_identificados():
    assert es_derivado("SWP") and es_derivado("FWDS") and not es_derivado("1ASP")


def test_etfs_pendientes_se_agrupan_sin_adivinar():
    filas = [_fila(1, tv="1ISP", emisora="ZZZ1", serie="*"), _fila(2, tv="1ISP", emisora="ZZZ2", serie="*"),
             _fila(3, tv="1ISP", emisora="VOO", serie="*")]
    d = doc(FIX / "cnbv" / "R7_2026_muestra.xlsx", "cnbv", None, "cnbv_r7")
    (c,) = cnbv.carteras_r7(filas, "x", "XOP", d)
    pend = etfs_sin_clasificar(c)
    assert set(pend) == {"ZZZ1", "ZZZ2"}
    e = EtfsPendientes("x", pend)
    assert "2 ETF sin clasificar" in str(e) and e.pendientes == pend


def test_supuestos_por_omision():
    prm = cargar_parametros()
    assert prm.supuestos("finaccess").probabilidad_de_alta == 0.35
    assert prm.supuestos("blackrock", False).probabilidad_de_alta == prm.default.probabilidad_de_alta
    assert prm.supuestos("gbm", True).probabilidad_de_alta == prm.default_con_hermana.probabilidad_de_alta


def test_vistas_de_la_plataforma(entorno):
    from radar import vistas as V

    store, prm = entorno
    u = V.cargar(store, prm)
    assert {"finaccess", "multiva"} <= set(u.metricas)
    df = V.comparativo(u, prm)
    assert list(df["Calificación"]) == sorted(df["Calificación"], reverse=True)
    m = u.metricas["finaccess"]
    assert len(V.tabla_fondos(m)) == len(m.fondos)
    assert len(V.top_rv(m)) <= 20 and len(V.top_rf(m)) <= 20
    f = next(x for x in m.fondos if x.clave == "AXESBMV")
    assert len(V.tramos_rotacion(f)) == 2
    assert V.posiciones(f)["Valor (mdp)"].sum() == pytest.approx(f.total_cartera / 1e6)


def test_hibrido_detecta_casa_de_bolsa_hermana_en_el_dici():
    from radar.adapters.cnbv_generico import AdaptadorCnbvConDici, ConfigCnbv
    from radar.core.modelo import Dici, Procedencia

    class Prueba(AdaptadorCnbvConDici):
        marcas = ("ejemplo",)

        def documentos(self, cliente, claves):
            return []

    cfg = ConfigCnbv("prueba", "Operadora Ejemplo", "OPEJ", "Grupo Ejemplo", False, "", "", "padrón")
    a = Prueba(cfg)

    def dici(distrib):
        return Dici("prueba", "F1", None, "", None, None, None, "", "", "", "", distrib, [], None,
                    Procedencia("x", "d.pdf", 1, None))

    limpio = a.perfil([dici(["Operadora Ejemplo, S.A. de C.V.", "Actinver Casa de Bolsa S.A. de C.V."])])
    assert limpio.casa_de_bolsa_hermana is False and "Actinver" in limpio.evidencia_casa_de_bolsa
    sucio = a.perfil([dici(["Casa de Bolsa Ejemplo, S.A. de C.V."])])
    assert sucio.casa_de_bolsa_hermana is True and "DISCREPANCIA" in sucio.evidencia_casa_de_bolsa
