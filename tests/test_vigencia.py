"""Fechas de los documentos: registro en la fuente (Last-Modified) y en el radar (primera descarga)."""
from datetime import date

from radar.core.modelo import Documento
from radar.red import fecha_modificado
from radar.store.db import Store
from radar.vistas import _meses, estado_vigencia


def test_fecha_modificado_en_hora_de_la_cdmx():
    assert fecha_modificado("Thu, 12 Nov 2026 18:05:19 GMT") == date(2026, 11, 12)
    # 03:00 GMT del 13 son las 21:00 del 12 en la Ciudad de México (UTC-6)
    assert fecha_modificado("Fri, 13 Nov 2026 03:00:00 GMT") == date(2026, 11, 12)
    assert fecha_modificado(None) is None
    assert fecha_modificado("no es fecha") is None


def test_registro_conserva_la_primera_descarga(tmp_path):
    s = Store(tmp_path / "r.sqlite")
    d = Documento("abc", "cnbv", None, "cnbv_r7", "https://x/r7.xlsm", "raw/cnbv/abc_r7.xlsm",
                  date(2026, 9, 30), date(2026, 11, 18), 10, None)
    s.guardar_documento(d)
    # El mismo archivo se vuelve a bajar días después: el registro no se mueve y se aprende la
    # fecha de la fuente.
    s.guardar_documento(Documento("abc", "cnbv", None, "cnbv_r7", d.url, d.archivo, d.fecha_doc,
                                  date(2026, 11, 20), 10, date(2026, 11, 12)))
    x = s.documento("abc")
    assert x.descargado == date(2026, 11, 18)
    assert x.publicado == date(2026, 11, 12)
    # Una corrida sin encabezado no borra la fecha de la fuente.
    s.guardar_documento(Documento("abc", "cnbv", None, "cnbv_r7", d.url, d.archivo, d.fecha_doc,
                                  date(2026, 11, 23), 10, None))
    assert s.documento("abc").publicado == date(2026, 11, 12)
    assert s.documentos("cnbv")[0].descargado == date(2026, 11, 18)
    s.cerrar()


def test_estado_de_vigencia_por_meses_de_atraso():
    assert _meses(date(2026, 9, 30), date(2026, 10, 30)) == 1
    assert estado_vigencia(0) == ("Al día", "ok")
    assert estado_vigencia(1) == ("Rezagado 1 mes", "alerta")
    assert estado_vigencia(3)[0] == "Rezagado 3 meses"
