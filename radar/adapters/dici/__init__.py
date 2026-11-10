"""Operadoras híbridas: cartera y activo neto por la CNBV (R7/R1); DICI y prospecto desde su
sitio (régimen, comisiones, liquidez y distribuidoras). Nafinsa queda fuera: su sitio tiene un
firewall que corta las conexiones que no vienen de un navegador."""
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.adapters.dici.blackrock import BlackRock
from radar.adapters.dici.franklin import Franklin
from radar.adapters.dici.principal import Principal
from radar.adapters.dici.skandia import Skandia
from radar.adapters.dici.sura import Sura

CLASES: dict[str, type[AdaptadorCnbvConDici]] = {
    "blackrock": BlackRock, "sura": Sura, "principal": Principal, "franklin": Franklin, "skandia": Skandia,
}
