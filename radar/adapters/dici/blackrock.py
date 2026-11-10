"""BlackRock México Operadora (CNBV: IMPFOND). Cartera y activo neto por la CNBV; DICI y
prospecto por HTTP simple, armados desde la clave del fondo.

- DICI: blackrock.com publica el completo (todas las series) para ~10 fondos; Citi
  (distribuidor) publica el suyo para ~30 (solo las series que distribuye y con algunos
  meses más de rezago). Se intenta primero blackrock.com y después Citi. Citi responde
  HTTP 200 con un JSON cuando no existe: la descarga valida la firma %PDF.
- Prospecto: blackrock.com; el "+" de la clave se escribe "p" y los LifePath comparten
  un prospecto.

BlackRock México no tiene casa de bolsa ni grupo financiero en México; sus DICI listan
a Banamex / Citi México Casa de Bolsa y a Banco S3 CACEIS como distribuidoras (terceros).
"""
from __future__ import annotations

from radar.adapters.base import DocARevisar
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.red import Cliente

BASE = "https://www.blackrock.com/mx/intermediarios/literature"
CITI = "https://www.citigroup.com/rcs/citigpa/storage/public/Mexico"
LIFEPATH = {"BLK2030", "BLK2040", "BLK2050", "BLK2060", "BLKRET"}


def slug(clave: str) -> str:
    return clave.lower().replace("+", "p")


class BlackRock(AdaptadorCnbvConDici):
    marcas = ("blackrock",)

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        docs: list[DocARevisar] = []
        for k in claves:
            docs.append(DocARevisar(k, "dici", f"{BASE}/fact-sheet/{slug(k)}-dici.pdf", f"DICI_{k}.pdf",
                                    alternativas=(f"{CITI}/{k}_DocumentoClaveActualizacionAnual.pdf",),
                                    opcional=True))
            pros = "lifepath" if k in LIFEPATH else slug(k)
            docs.append(DocARevisar(k, "prospecto", f"{BASE}/prospectus/{pros}-prospecto.pdf",
                                    f"Prospecto_{k}.pdf", opcional=True))
        return docs
