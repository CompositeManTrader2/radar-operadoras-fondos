"""Skandia Operadora de Fondos (CNBV: SKANDIA). DICI y prospecto en un blob público con la
clave en la ruta; la carpeta es DEUDA o RENTA VARIABLE (se prueban ambas). Sus DICI solo
listan a la propia operadora como distribuidora."""
from __future__ import annotations

from radar.adapters.base import DocARevisar
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.red import Cliente

BASE = "https://hubdigital.skandia.com.mx/portalpublico/Fondos%20de%20inversi%C3%B3n/FONDOS%20SK"
GRUPOS = ("RENTA%20VARIABLE", "DEUDA")


class Skandia(AdaptadorCnbvConDici):
    marcas = ("skandia",)

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        docs: list[DocARevisar] = []
        for k in claves:
            for tipo, nombre in (("dici", f"DICI_{k}.pdf"), ("prospecto", f"Prospecto_{k}.pdf")):
                urls = [f"{BASE}/{g}/{k}/{nombre}" for g in GRUPOS]
                docs.append(DocARevisar(k, tipo, urls[0], nombre, alternativas=tuple(urls[1:]), opcional=True))
        return docs
