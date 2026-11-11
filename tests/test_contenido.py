"""Plan de contenido por operadora (qué research y noticias mandarle)."""
from datetime import date

from radar.config import cargar_parametros
from radar.core.contenido import info_emisora, plan_contenido
from radar.core.metricas import MetricasOperadora, metricas_fondo
from radar.core.modelo import RV_LOCAL, RV_SIC, Cartera, Categoria, PerfilOperadora, Posicion, Procedencia

PRM = cargar_parametros()


def _p(em, titulos, valor, clase=RV_LOCAL, tv="1", agregado=False):
    cat = Categoria.ACCION_SIC if clase == RV_SIC else Categoria.ACCION_LOCAL
    return Posicion(f"{tv}_{em}_*", tv, em, "*", titulos, valor, None, "", "", "", cat,
                    Procedencia("x", "f.pdf", 1, date(2026, 9, 30)), es_agregado=agregado,
                    emisora_canonica=em, clase=clase, mercado="LOCAL" if clase == RV_LOCAL else "SIC")


def _c(fecha, pos, clave="F1"):
    tot = sum(p.valor_razonable for p in pos)
    return Cartera("op", clave, "X, Fondo de Inversión de Renta Variable", "", fecha, "cartera_mensual", tot, False,
                   tot, pos, Procedencia("x", "f.pdf", 1, fecha), tipo_fondo="RV")


def _operadora(antes, hoy, hermana=False):
    f = metricas_fondo(hoy, {hoy.fondo_clave: hoy}, [antes, hoy], None, PRM)
    return MetricasOperadora("op", "Op", hoy.fecha_corte, PerfilOperadora("op", "Op", "", "", hermana, ""),
                             [f], [], [], None, None, None)


def test_movimientos_por_titulos_sin_efecto_precio():
    antes = _c(date(2026, 8, 31), [_p("WALMEX", 100, 1000), _p("AMX", 50, 500), _p("FEMSA", 10, 300)])
    # WALMEX sube de precio pero no de títulos; FEMSA aumenta 50 %; AMX sale; GFNORTE entra.
    hoy = _c(date(2026, 9, 30), [_p("WALMEX", 100, 1500), _p("FEMSA", 15, 450), _p("GFNORTE", 20, 400)])
    plan = plan_contenido(_operadora(antes, hoy))
    mov = {e.emisora: e.movimiento for e in plan.emisoras}
    assert mov == {"WALMEX": "Estable", "FEMSA": "Aumentó", "GFNORTE": "Nueva"}
    assert [e.emisora for e in plan.salidas] == ["AMX"]
    assert plan.corte_previo == date(2026, 8, 31)
    titulos = {t.titulo for t in plan.temas}
    assert {"Mercado mexicano y emisoras locales", "Ideas que está comprando", "Nombres que vendió"} <= titulos
    compra = next(t for t in plan.temas if t.titulo == "Ideas que está comprando")
    assert "FEMSA" in compra.por_que and "GFNORTE" in compra.por_que


def test_renglon_agregado_no_cuenta_como_venta():
    """Multiva agrupa a veces las acciones SIC en un renglón sin emisora: no es una venta."""
    antes = _c(date(2026, 8, 31), [_p("NVDA", 10, 900, RV_SIC, "1ASP"), _p("AMX", 50, 500)])
    hoy = _c(date(2026, 9, 30), [_p("OTROS-1ASP", None, 950, RV_SIC, "1ASP", agregado=True), _p("AMX", 50, 520)])
    plan = plan_contenido(_operadora(antes, hoy))
    assert plan.salidas == []


def test_casa_de_bolsa_hermana_y_markdown():
    antes = _c(date(2026, 8, 31), [_p("AMX", 50, 500)])
    hoy = _c(date(2026, 9, 30), [_p("AMX", 50, 500)])
    plan = plan_contenido(_operadora(antes, hoy, hermana=True))
    assert any(t.titulo == "Tiene casa de bolsa hermana" for t in plan.temas)
    md = plan.markdown("Op")
    assert md.startswith("# Qué enviarle a Op") and "| AMX | América Móvil | Telecomunicaciones y medios |" in md


def test_catalogo_de_emisoras_y_etfs():
    assert info_emisora("GMEXICO").sector == "Materiales y minería"
    assert info_emisora("VOO").sector == "ETF de renta variable"
    assert info_emisora("ZZZZ9").nombre == "[POR CONFIRMAR]"


def test_noticias_rss_y_consulta():
    from radar.noticias import consulta, parsear_rss

    xml = (b'<?xml version="1.0"?><rss><channel>'
           b'<item><title>Grupo Mexico sube dividendo - El Economista</title><source>El Economista</source>'
           b'<pubDate>Mon, 02 Nov 2026 08:00:00 GMT</pubDate><link>https://news.google.com/a</link></item>'
           b'<item><title>Nota vieja - Reforma</title><source>Reforma</source>'
           b'<pubDate>Sun, 01 Nov 2026 07:00:00 GMT</pubDate><link>https://news.google.com/b</link></item>'
           b'<item><title>Sin liga segura</title><link>javascript:alert(1)</link></item>'
           b'</channel></rss>')
    ns = parsear_rss(xml)
    assert [x.titulo for x in ns] == ["Grupo Mexico sube dividendo", "Nota vieja"]
    assert ns[0].fuente == "El Economista"
    assert consulta("AMX", "América Móvil").startswith('"América Móvil"')
    assert consulta("ZZZ", "[POR CONFIRMAR]").startswith('"ZZZ" (acciones OR')
