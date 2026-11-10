"""Principal Fondos de Inversión (CNBV: PRINPAL). DICI y prospecto por alias fijos del sitio
(Drupal devuelve el PDF directo). Los LifeCycle (PRINR25..55) van sin guion y comparten
prospecto; los PRINLS también comparten uno. Principal no tiene casa de bolsa en México: sus
DICI listan a Actinver Casa de Bolsa, GBM Casa de Bolsa, Skandia, Mifel, Banregio, etc."""
from __future__ import annotations

import re

from radar.adapters.base import DocARevisar
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.red import Cliente

BASE = "https://principal.com.mx"


class Principal(AdaptadorCnbvConDici):
    marcas = ("principal",)

    def documentos(self, cliente: Cliente, claves: list[str]) -> list[DocARevisar]:
        docs: list[DocARevisar] = []
        for k in claves:
            ciclo = re.fullmatch(r"PRINR\d\d", k) is not None
            docs.append(DocARevisar(k, "dici", f"{BASE}/{k}DICI" if ciclo else f"{BASE}/{k}-DICI",
                                    f"DICI_{k}.pdf", opcional=True))
            if ciclo:
                pros = "prospectoparticularlifecycle"
            elif k.startswith("PRINLS"):
                pros = "prospectoparticular"
            else:
                pros = f"prospecto{k.lower()}"
            docs.append(DocARevisar(k, "prospecto", f"{BASE}/{pros}", f"Prospecto_{k}.pdf", opcional=True))
        return docs
