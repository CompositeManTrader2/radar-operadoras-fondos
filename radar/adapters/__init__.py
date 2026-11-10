"""Registro de adaptadores.

- Adaptador propio (cartera y DICI de la operadora): un módulo + una línea aquí.
- Cobertura CNBV (R7/R1) para el resto: una entrada en config/operadoras_cnbv.toml.
"""
from radar.adapters.base import Adaptador
from radar.adapters.cnbv_generico import AdaptadorCnbv, cargar_config
from radar.adapters.compass import Compass
from radar.adapters.finaccess import Finaccess
from radar.adapters.multiva import Multiva

PROPIOS: tuple[Adaptador, ...] = (Finaccess(), Multiva(), Compass())
REGISTRO: dict[str, Adaptador] = {a.clave: a for a in PROPIOS}
_con_cnbv = {a.clave_cnbv for a in PROPIOS}
for _cfg in cargar_config():
    if _cfg.clave in REGISTRO or _cfg.clave_cnbv in _con_cnbv:
        raise ValueError(f"config/operadoras_cnbv.toml: {_cfg.clave}/{_cfg.clave_cnbv} ya tiene adaptador propio")
    REGISTRO[_cfg.clave] = AdaptadorCnbv(_cfg)


def adaptador(clave: str) -> Adaptador:
    try:
        return REGISTRO[clave]
    except KeyError:
        raise SystemExit(f"Operadora desconocida '{clave}'. Disponibles: {', '.join(sorted(REGISTRO))}")
