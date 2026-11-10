import re
from datetime import date

from radar.pipeline import construir_metricas
from radar.render import plantillas as T
from radar.render.html import render_comparativo, render_operadora


def _html(entorno, op, corte):
    store, prm = entorno
    return render_operadora(construir_metricas(op, corte, store, prm), prm)


def test_mismo_corte_mismo_html(entorno):
    a = _html(entorno, "finaccess", date(2026, 10, 30))
    b = _html(entorno, "finaccess", date(2026, 10, 30))
    assert a == b
    c = _html(entorno, "multiva", date(2026, 10, 30))
    assert c == _html(entorno, "multiva", date(2026, 10, 30))


def test_estructura_y_textos_fijos(entorno):
    h = _html(entorno, "finaccess", date(2026, 10, 30))
    for _, etiqueta in T.INDICADORES:
        assert etiqueta in h
    for col in T.COLUMNAS_FONDOS:
        assert f">{col}<" in h.replace("&amp;", "&")
    for titulo in (T.TITULO_DONA_FONDOS, T.TITULO_DONA_ACTIVOS, T.TITULO_TOP_RV, T.TITULO_TOP_RF,
                   T.TITULO_METODOLOGIA, T.TITULO_SUPUESTOS, T.TITULO_HUECOS, T.TITULO_FUENTES):
        assert titulo in h
    assert "PISO" in h
    assert "<script" not in h and "http://" not in h.split("<body>")[1].split("Fuentes")[0]
    # Tema oscuro: el encabezado se oscurece (no se aclara).
    assert "--encabezado:#2A1838" in h


def _esqueleto(html: str) -> list[str]:
    """Títulos, encabezados de columna y etiquetas, con cifras enmascaradas."""
    piezas = re.findall(r"<(h1|h2|h3|th)[^>]*>(.*?)</\1>", html)
    piezas += re.findall(r'<div class="etiqueta">(.*?)</div>', html)
    return [re.sub(r"\d", "#", t if isinstance(t, str) else t[1]) for t in piezas]


def test_regla_de_actualizacion_solo_cambian_cifras(entorno):
    """Dos cortes distintos producen el mismo esqueleto de texto."""
    store, prm = entorno
    m_oct = construir_metricas("finaccess", date(2026, 10, 30), store, prm)
    h_oct = render_operadora(m_oct, prm)
    # Mismo documento con otras cifras: escalar montos del corte simulado.
    for f in m_oct.fondos:
        f.activo_neto *= 1.37
    h_otro = render_operadora(m_oct, prm)
    assert h_oct != h_otro
    assert _esqueleto(h_oct) == _esqueleto(h_otro)


def test_comparativo(entorno):
    store, prm = entorno
    ms = [construir_metricas(op, date(2026, 10, 30), store, prm) for op in ("finaccess", "multiva")]
    h = render_comparativo(ms, prm, ["2026-09-30", "2026-10-31"])
    assert T.TITULO_CALIFICACION in h and T.TITULO_DISPERSION in h
    assert "veto" in h  # Multiva tiene casa de bolsa hermana
    assert h == render_comparativo(ms, prm, ["2026-09-30", "2026-10-31"])
    for col in T.COLUMNAS_CALIFICACION:
        assert col in h
