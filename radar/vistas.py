"""Tablas (pandas) que alimentan la plataforma. Sin Streamlit aquí: se pueden probar."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from radar.adapters import REGISTRO
from radar.config import Parametros
from radar.core.clasificacion import nombre_emisora_sic
from radar.core.metricas import MetricasFondo, MetricasOperadora
from radar.core.modelo import CLASES_RV, POR_CONFIRMAR, RF, Categoria
from radar.pipeline import ErrorCorte, construir_metricas, resolver_corte
from radar.store.db import Store

MDP = 1_000_000


@dataclass
class Universo:
    metricas: dict[str, MetricasOperadora]   # operadoras con cifras
    sin_datos: dict[str, str]                # operadora -> motivo


def fuente_de(clave: str) -> str:
    return "CNBV R7/R1" if getattr(REGISTRO[clave], "solo_cnbv", False) else "Operadora + CNBV"


def cargar(store: Store, prm: Parametros, corte: dict[str, str] | None = None) -> Universo:
    met, sin = {}, {}
    estados = {e["operadora"]: e for e in store.estados()}
    for op in sorted(REGISTRO):
        try:
            c = resolver_corte(store, op, (corte or {}).get(op, "latest"))
            m = construir_metricas(op, c, store, prm)
        except ErrorCorte:
            e = estados.get(op)
            sin[op] = e["mensaje"] if e and not e["ok"] else "Sin cortes en el store"
            continue
        if not m.fondos:
            sin[op] = "Sin fondos analizables en el corte"
            continue
        met[op] = m
    return Universo(met, sin)


def _hermana(m: MetricasOperadora) -> str:
    h = m.perfil.casa_de_bolsa_hermana if m.perfil else None
    return "Sí" if h else ("No" if h is False else POR_CONFIRMAR)


def comparativo(u: Universo, prm: Parametros) -> pd.DataFrame:
    filas = []
    for op, m in u.metricas.items():
        q = m.calificacion(prm)
        lo, hi = m.bolsa_banda(prm)
        ilo, ihi = m.ingreso_esperado(prm)
        rot, medida = m.rotacion_ponderada()
        filas.append({
            "Operadora": m.nombre, "clave": op, "Corte": m.corte.isoformat(), "Fuente": fuente_de(op),
            "Casa de bolsa hermana": _hermana(m),
            "Activos netos (mdp)": m.activo_neto / MDP, "RV (mdp)": m.exposicion_rv / MDP,
            "% RV": m.exposicion_rv / m.activo_neto if m.activo_neto else 0.0,
            "% RV en directo": m.pct_directo,
            "Rotación media": rot, "Rotación medida (% expos.)": m.fraccion_rotacion_medida(),
            "Bolsa mín. (mdp)": lo / MDP, "Bolsa máx. (mdp)": hi / MDP,
            "Ingreso esperado máx. (mdp) (e)": ihi / MDP,
            "Bolsa (30%)": q.bolsa, "Independencia (25%)": q.independencia, "Ajuste (20%)": q.ajuste,
            "Recurrencia (10%)": q.recurrencia, "Headroom y momentum (10%)": q.headroom,
            "Fricción (5%) (e)": q.friccion, "Calificación": q.total, "Tier": q.tier + (" (provisional)" if q.provisional else ""),
            "Veto": "Sí" if q.veto else "",
        })
    df = pd.DataFrame(filas)
    return df.sort_values(["Calificación", "RV (mdp)"], ascending=[False, False]).reset_index(drop=True) if len(df) else df


def puntos_dispersion(u: Universo, prm: Parametros) -> pd.DataFrame:
    filas = []
    for op, m in u.metricas.items():
        for f in m.fondos:
            if f.exposicion_rv <= 0:
                continue
            filas.append({"Operadora": m.nombre, "Fondo": f.clave, "Exposición RV (mdp)": f.exposicion_rv / MDP,
                          "% RV": f.pct_rv * 100, "Bolsa (mdp)": f.bolsa(f.rotacion.media, prm) / MDP})
    return pd.DataFrame(filas)


def tabla_fondos(m: MetricasOperadora) -> pd.DataFrame:
    filas = []
    for f in sorted(m.fondos, key=lambda x: (-x.activo_neto, x.clave)):
        filas.append({
            "Clave": f.clave, "Nombre corto": f.nombre_corto or "—",
            "Tipo de fondo": {"RV": "Renta variable", "RF": "Renta fija"}.get(f.tipo_fondo, f.tipo_fondo),
            "Categoría regulatoria": f.categoria_regulatoria,
            "Activos netos (mdp)": f.activo_neto_propio / MDP, "Activo neto estimado": "(e)" if f.activo_neto_estimado else "",
            "En fondos hermanos (mdp)": (f.activo_neto - f.activo_neto_propio) / MDP,
            "% RV": f.pct_rv, "% RF": f.pct_rf, "% Efectivo": f.pct_efe,
            "RV (mdp)": f.exposicion_rv / MDP, "RF (mdp)": f.monto_rf / MDP,
            "Local / SIC": f"{f.share_local:.0%} / {1 - f.share_local:.0%}" if f.exposicion_rv else "—",
            "Máx. RV régimen": f.rv_max, "Headroom (mdp)": (f.headroom or 0) / MDP if f.headroom is not None else None,
            "Rotación (piso–techo)": f"{f.rotacion.minimo:.2f}x–{f.rotacion.maximo:.2f}x" + ("" if f.rotacion.medida else " (e)"),
            "Discrepancias": len(f.discrepancias),
        })
    return pd.DataFrame(filas)


def top(m: MetricasOperadora, clases: tuple[str, ...], n: int = 20) -> pd.DataFrame:
    agg: dict[str, float] = defaultdict(float)
    nombre: dict[str, str] = {}
    fondos: dict[str, set] = defaultdict(set)
    for f in m.fondos:
        for p in f.cartera.posiciones:
            if p.clase not in clases or p.es_agregado or p.categoria is Categoria.FONDO:
                continue
            k = p.emisora_canonica
            agg[k] += p.valor_razonable
            fondos[k].add(f.clave)
            if p.categoria is Categoria.ACCION_SIC:
                nombre[k] = nombre_emisora_sic(k)
    filas = sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
    tot = sum(agg.values())
    return pd.DataFrame([{"Emisora": k, "Nombre": nombre.get(k, ""), "Monto (mdp)": v / MDP,
                          "Peso en la clase": v / tot if tot else 0, "Fondos": ", ".join(sorted(fondos[k]))}
                         for k, v in filas])


def top_rv(m: MetricasOperadora) -> pd.DataFrame:
    return top(m, CLASES_RV)


def top_rf(m: MetricasOperadora) -> pd.DataFrame:
    return top(m, (RF,))


def posiciones(f: MetricasFondo) -> pd.DataFrame:
    return pd.DataFrame([{
        "Emisora (raw)": p.emisora_raw, "Canónica": p.emisora_canonica, "Serie": p.serie, "TV": p.tipo_valor,
        "Tipo": p.tipo_instrumento_raw, "Clase": p.clase or "FONDO (transparentado)", "Mercado": p.mercado or "",
        "Títulos": p.titulos, "Valor (mdp)": p.valor_razonable / MDP,
        "% cartera": p.valor_razonable / f.total_cartera if f.total_cartera else None,
        "Agregado": "Sí" if p.es_agregado else "", "Nota": p.nota, "Fuente": p.procedencia.cita(),
    } for p in f.cartera.posiciones])


def tramos_rotacion(f: MetricasFondo) -> pd.DataFrame:
    return pd.DataFrame([{
        "Desde": r.corte_a.isoformat(), "Hasta": r.corte_b.isoformat(), "Meses": r.meses,
        "Compras (mdp)": r.compras / MDP, "Ventas (mdp)": r.ventas / MDP,
        "Exposición RV promedio (mdp)": r.base / MDP, "Piso anualizado": r.anual,
        "RV no seguible (mdp)": r.sin_titulos / MDP,
    } for r in f.rotacion.pares])


def historia(f: MetricasFondo) -> pd.DataFrame:
    from radar.core.metricas import mezcla

    filas = []
    for c in sorted(f.historia, key=lambda x: x.fecha_corte):
        mz = mezcla(c, {})
        filas.append({"Corte": c.fecha_corte.isoformat(), "Fuente": c.tipo_doc,
                      "Activo neto (mdp)": c.activo_neto / MDP, "% RV": mz.pct_rv})
    return pd.DataFrame(filas)


def estado(store: Store) -> pd.DataFrame:
    return pd.DataFrame([{
        "Operadora": REGISTRO[e["operadora"]].nombre if e["operadora"] in REGISTRO else e["operadora"],
        "clave": e["operadora"], "Fuente": fuente_de(e["operadora"]) if e["operadora"] in REGISTRO else "",
        "Última ejecución": e["fecha"], "Estado": "OK" if e["ok"] else "Pendiente / error",
        "Etapa": e["etapa"], "Mensaje": e["mensaje"],
    } for e in store.estados()])


def etfs_pendientes(store: Store) -> pd.DataFrame:
    agg: dict[str, float] = defaultdict(float)
    ops: dict[str, set] = defaultdict(set)
    for e in store.estados():
        for k, v in (e["detalle"] or {}).get("pendientes", {}).items():
            agg[k] += v
            ops[k].add(e["operadora"])
    df = pd.DataFrame([{"Ticker": k, "Monto (mdp)": v / MDP, "Operadoras": ", ".join(sorted(ops[k]))}
                       for k, v in agg.items()])
    return df.sort_values("Monto (mdp)", ascending=False).reset_index(drop=True) if len(df) else df


def conciliaciones(store: Store) -> pd.DataFrame:
    filas = []
    for op in sorted(REGISTRO):
        for k in store.conciliaciones(op):
            dif = (k["monto_a"] - k["monto_b"]) / k["monto_b"] if k["monto_b"] else None
            filas.append({"Operadora": op, "Fondo": k["fondo"], "Fecha": k["fecha"], "Concepto": k["concepto"],
                          "Fuente A": k["fuente_a"], "Monto A (mdp)": k["monto_a"] / MDP,
                          "Fuente B": k["fuente_b"], "Monto B (mdp)": k["monto_b"] / MDP, "Diferencia": dif})
    return pd.DataFrame(filas)


def documentos(store: Store) -> pd.DataFrame:
    filas = []
    for op in sorted(list(REGISTRO) + ["cnbv"]):
        docs = store.documentos(op)
        if not docs:
            continue
        filas.append({"Fuente": op, "Documentos": len(docs),
                      "Último descargado": max(d.descargado for d in docs).isoformat(),
                      "Corte más reciente": max((d.fecha_doc for d in docs if d.fecha_doc), default=None)})
    return pd.DataFrame(filas)
