"""Fixtures: PDFs REALES de cada operadora guardados en tests/fixtures. Si el emisor
cambia de formato, estos tests rompen (y no el reporte)."""
from __future__ import annotations

import hashlib
import os
import shutil
from datetime import date
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def _cache_pdf(tmp_path_factory):
    os.environ["RADAR_CACHE_PDF"] = str(tmp_path_factory.mktemp("cache_pdf"))
    yield


def doc(ruta: Path, operadora: str, clave: str | None, tipo: str):
    from radar.core.modelo import Documento

    sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
    return Documento(sha, operadora, clave, tipo, f"fixture://{ruta.name}", ruta.name, None, date(2026, 11, 10),
                     ruta.stat().st_size)


@pytest.fixture(scope="session")
def entorno(tmp_path_factory):
    """Store construido con los fixtures por el pipeline real (sin red)."""
    from radar.adapters.finaccess import Finaccess
    from radar.adapters.multiva import Multiva
    from radar.config import cargar_parametros
    from radar.pipeline import parsear
    from radar.store.db import Store

    datos = tmp_path_factory.mktemp("datos")
    os.environ["RADAR_DATOS"] = str(datos)
    store = Store(datos / "radar.sqlite")
    prm = cargar_parametros()

    fin = Finaccess()
    fondos, _ = fin.descubrir_desde_html((FIX / "finaccess" / "home.html").read_text(encoding="utf-8"))
    store.guardar_universo("finaccess", fondos)
    mul = Multiva()
    fondos, _ = mul.descubrir_desde_html((FIX / "multiva" / "fondos.html").read_text(encoding="utf-8"))
    store.guardar_universo("multiva", fondos)

    archivos = [
        ("finaccess", "AXESBMV", "cartera_mensual", "finaccess/cartera_mensual_axesbmv_2026-10-30.pdf"),
        ("finaccess", "AXESBMV", "cartera_diaria", "finaccess/cartera_axesbmv_2026-09-10.pdf"),
        ("finaccess", "AXESGLO", "cartera_mensual", "finaccess/cartera_mensual_axesglo_2026-10-30.pdf"),
        ("finaccess", "AXESBMV", "dici", "finaccess/DICI_AXESBMV_2026-10.pdf"),
        ("finaccess", "AXESBMV", "prospecto", "finaccess/ProspEspecificoAXESBMV.pdf"),
        ("multiva", "MULTIPC", "cartera_mensual", "multiva/OPMULTIMULTIPCPublicaciones20261030.pdf"),
        ("multiva", "MULTIEQ", "cartera_mensual", "multiva/OPMULTIMULTIEQPublicaciones20261030.pdf"),
        ("multiva", "MULTIPC", "dici", "multiva/202610_MULTIPC.pdf"),
        ("multiva", "MULTIPC", "prospecto", "multiva/MULTIPC_2026.pdf"),
        ("multiva", None, "prospecto_generico", "multiva/MULTIVA GENERICO VIGENTE 2026.pdf"),
    ]
    from radar.fuentes import cnbv

    for tipo, rel in (("cnbv_r7", "cnbv/R7_2026_muestra.xlsx"), ("cnbv_r1", "cnbv/R1_2026_S2_muestra.xlsx")):
        destino = datos / "raw" / "cnbv" / Path(rel).name
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIX / rel, destino)
        d = doc(destino, "cnbv", None, tipo)
        d.archivo = destino.relative_to(datos).as_posix()
        d.fecha_doc = cnbv.fecha_documento(tipo, destino)
        store.guardar_documento(d)

    ads = {"finaccess": fin, "multiva": mul}
    for op, clave, tipo, rel in archivos:
        destino = datos / "raw" / op / Path(rel).name
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIX / rel, destino)
        d = doc(destino, op, clave, tipo)
        d.archivo = destino.relative_to(datos).as_posix()
        d.fecha_doc = ads[op].fecha_documento(tipo, destino)
        store.guardar_documento(d)
    parsear("finaccess", store, prm, log=lambda *_: None)
    parsear("multiva", store, prm, log=lambda *_: None)
    yield store, prm
    store.cerrar()
