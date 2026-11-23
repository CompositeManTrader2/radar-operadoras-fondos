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
    from radar.adapters.cnbv_generico import AdaptadorCnbv, AdaptadorCnbvConDici

    a = REGISTRO[clave]
    if isinstance(a, AdaptadorCnbvConDici):
        return "CNBV R7/R1 + DICI"
    return "CNBV R7/R1" if isinstance(a, AdaptadorCnbv) else "Operadora + CNBV"


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


# ------------------------------------------------------------------ vigencia (qué tan actualizado está)
FUENTE_CARTERA = {
    "cnbv_r7": "CNBV · Reporte R7 (cartera)",
    "cartera_mensual": "Cartera mensual de la operadora",
    "cartera_diaria": "Cartera semanal de la operadora",
}


def _meses(a, b) -> int:
    return (b.year - a.year) * 12 + b.month - a.month


def estado_vigencia(rezago: int) -> tuple[str, str]:
    """(texto, clase de insignia) según los meses de atraso contra el corte más reciente."""
    if rezago <= 0:
        return "Al día", "ok"
    return (f"Rezagado {rezago} mes" + ("es" if rezago > 1 else ""), "alerta")


def vigencia_fondos(store: Store, m: MetricasOperadora, hoy=None) -> list[dict]:
    """Por fondo: corte, documento de origen con sus fechas (registrado en la fuente y registrado
    en el radar), activo neto oficial o estimado, DICI y atraso contra el corte más reciente de la
    operadora."""
    from datetime import date

    hoy = hoy or date.today()
    fila = store.cx.execute("SELECT max(fecha_corte) FROM carteras WHERE operadora=?", (m.clave,)).fetchone()
    ultimo = date.fromisoformat(fila[0]) if fila and fila[0] else m.corte
    docs: dict[str, object] = {}

    def doc(doc_id):
        if doc_id and doc_id not in docs:
            docs[doc_id] = store.documento(doc_id)
        return docs.get(doc_id) if doc_id else None

    out = []
    for f in sorted(m.fondos + m.excluidos_fdf, key=lambda x: (-x.activo_neto, x.clave)):
        c = f.cartera
        dc = doc(c.procedencia.doc_id)
        an = None if f.activo_neto_estimado else store.activo_neto_oficial(m.clave, f.clave, f.fecha_corte)
        dan = doc(an[1].doc_id) if an else None
        dd = doc(f.dici.procedencia.doc_id) if f.dici else None
        rezago = max(0, _meses(f.fecha_corte, ultimo))
        estado, clase = estado_vigencia(rezago)
        out.append({
            "clave": f.clave, "nombre": f.nombre_corto or f.nombre_legal or f.categoria_regulatoria or "",
            "categoria": f.categoria_regulatoria, "activo_neto": f.activo_neto, "estimado": f.activo_neto_estimado,
            "pct_rv": f.pct_rv, "pct_rf": f.pct_rf, "pct_efe": f.pct_efe, "fondo_de_fondos": f.es_fondo_de_fondos,
            "corte": f.fecha_corte, "dias_corte": (hoy - f.fecha_corte).days, "ultimo_operadora": ultimo,
            "rezago": rezago, "estado": estado, "clase": clase,
            "fuente": FUENTE_CARTERA.get(c.tipo_doc, c.tipo_doc), "archivo": c.procedencia.archivo,
            "publicado": getattr(dc, "publicado", None), "registrado": getattr(dc, "descargado", None),
            "url": getattr(dc, "url", ""),
            "an_fuente": (f"CNBV R1 al {an[1].fecha_doc:%d/%m/%Y}" if an else "Estimado (e): suma de la cartera"),
            "an_registrado": getattr(dan, "descargado", None),
            "dici_fecha": f.dici.fecha_doc if f.dici else None, "dici_registrado": getattr(dd, "descargado", None),
        })
    # Administrados sin cartera en el corte: se muestra su última cartera guardada y el atraso.
    for clave, motivo in m.sin_cartera:
        r = store.cx.execute(
            "SELECT fecha_corte, tipo_doc, doc_id, archivo, activo_neto, nombre_corto, categoria FROM carteras "
            "WHERE operadora=? AND fondo_clave=? ORDER BY fecha_corte DESC LIMIT 1", (m.clave, clave)).fetchone()
        corte = date.fromisoformat(r[0]) if r else None
        rezago = max(1, _meses(corte, ultimo)) if corte else None
        dc = doc(r[2]) if r else None
        di = store.cx.execute("SELECT max(fecha_doc) FROM dicis WHERE operadora=? AND fondo_clave=?",
                              (m.clave, clave)).fetchone()
        out.append({
            "clave": clave, "nombre": (r[5] if r else "") or "", "categoria": (r[6] if r else "") or "",
            "activo_neto": (r[4] or 0.0) if r else 0.0, "estimado": False, "pct_rv": None, "pct_rf": None,
            "pct_efe": None, "fondo_de_fondos": False, "corte": corte,
            "dias_corte": (hoy - corte).days if corte else None, "ultimo_operadora": ultimo, "rezago": rezago,
            "estado": (f"Sin cartera al {ultimo:%d/%m/%Y}" if corte else "Sin cartera"), "clase": "alerta",
            "fuente": FUENTE_CARTERA.get(r[1], r[1]) if r else "—", "archivo": r[3] if r else "",
            "publicado": getattr(dc, "publicado", None), "registrado": getattr(dc, "descargado", None),
            "url": getattr(dc, "url", ""), "an_fuente": f"de la cartera del {corte:%d/%m/%Y}" if corte else "—",
            "an_registrado": None, "dici_fecha": date.fromisoformat(di[0]) if di and di[0] else None,
            "dici_registrado": None, "sin_cartera": True, "motivo": motivo,
        })
    return out


def documentos_fondo(store: Store, operadora: str, f: MetricasFondo) -> pd.DataFrame:
    """Cada documento del que salen las cifras del fondo, con sus fechas."""
    from datetime import date

    filas = []

    def agrega(uso: str, proc, nota: str = ""):
        d = store.documento(proc.doc_id) if proc else None
        filas.append({
            "Dato": uso, "Documento": (d.archivo.rsplit("/", 1)[-1] if d else (proc.archivo if proc else "—")),
            "Fecha del dato": proc.fecha_doc if proc else None,
            "Registrado en la fuente": d.publicado if d else None,
            "Registrado en el radar": d.descargado if d else None,
            "Días desde el registro": (date.today() - d.descargado).days if d else None,
            "Liga": d.url if d and d.url.startswith("http") else None, "Nota": nota})

    agrega(f"Cartera ({FUENTE_CARTERA.get(f.cartera.tipo_doc, f.cartera.tipo_doc)})", f.cartera.procedencia,
           f"Página/fila {f.cartera.procedencia.pagina}")
    an = None if f.activo_neto_estimado else store.activo_neto_oficial(operadora, f.clave, f.fecha_corte)
    if an:
        agrega("Activo neto (CNBV R1)", an[1])
    else:
        filas.append({"Dato": "Activo neto", "Documento": "—", "Fecha del dato": f.fecha_corte,
                      "Registrado en la fuente": None, "Registrado en el radar": None, "Días desde el registro": None,
                      "Liga": None, "Nota": "Estimado (e): suma de la cartera; la CNBV aún no publica el R1 del mes"})
    if f.dici:
        agrega("DICI (comisiones y series)", f.dici.procedencia)
        if f.dici.fuente_regimen:
            agrega("Régimen de inversión (prospecto)", f.dici.fuente_regimen,
                   f"Página {f.dici.fuente_regimen.pagina}")
    df = pd.DataFrame(filas)
    for col in ("Fecha del dato", "Registrado en la fuente", "Registrado en el radar"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["Días desde el registro"] = pd.to_numeric(df["Días desde el registro"], errors="coerce").astype("Int64")
    df["Nota"] = df["Nota"].fillna("")
    return df
