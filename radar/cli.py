"""Línea de comandos.

  python -m radar discover --operadora finaccess
  python -m radar fetch    --operadora finaccess --corte latest
  python -m radar parse    --operadora finaccess
  python -m radar metrics  --operadora finaccess --corte latest
  python -m radar render   --operadora finaccess --corte latest
  python -m radar compare  --cortes 2026-09-30,2026-10-31
  python -m radar actualizar                 # todo: lo que corre la tarea programada
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import date

from radar.adapters import REGISTRO
from radar.config import cargar_parametros, dir_salidas, ruta_db
from radar.pipeline import (
    ErrorCorte, cliente, construir_metricas, descargar, descargar_cnbv, descubrir, parsear, resolver_corte,
    corte_a_lo_mas,
)
from radar.store.db import Store

LF = chr(10)


def _ops(arg: str) -> list[str]:
    return sorted(REGISTRO) if arg == "todas" else [arg]


def cmd_discover(a) -> int:
    cli = cliente(a.refrescar)
    for op in _ops(a.operadora):
        fondos, docs = descubrir(op, cli)
        print(f"== {op}: {len(fondos)} fondos, {len(docs)} documentos")
        for f in fondos:
            print(f"  {f.clave:9s} {f.estatus:13s} {f.nombre_comercial}  {f.nota}")
        for d in docs:
            print(f"    {d.fondo_clave or '-':9s} {d.tipo:18s} {d.url}")
    return 0


def _ejecutar(op: str, etapa: str, fn, store: Store) -> bool:
    """Corre una etapa de UNA operadora sin tumbar a las demás; deja el estado en el store."""
    from datetime import datetime

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        avisos = fn() or []
    except Exception as e:  # noqa: BLE001 - se registra y se reporta, no se oculta
        detalle = {"pendientes": getattr(e, "pendientes", {})}
        store.guardar_estado(op, ahora, False, etapa, f"{type(e).__name__}: {e}", detalle)
        print(f"  ERROR {op} ({etapa}): {type(e).__name__}: {e}", file=sys.stderr)
        return False
    mensaje = "ok" if not avisos else f"ok con {len(avisos)} aviso(s): " + " | ".join(avisos[:5])
    store.guardar_estado(op, ahora, True, etapa, mensaje, {"avisos": avisos})
    return True


def cmd_fetch(a) -> int:
    prm = cargar_parametros()
    store = Store(ruta_db())
    cli = cliente(a.refrescar)
    rc = 0
    if not a.sin_cnbv and any(REGISTRO[op].clave_cnbv for op in _ops(a.operadora)):
        print("== fetch CNBV (R1 activo neto, R7 cartera)")
        try:
            for av in descargar_cnbv(store, cli):
                print(f"  AVISO {av}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR CNBV: {e}", file=sys.stderr)
            rc = 1
    for op in _ops(a.operadora):
        print(f"== fetch {op}")

        def etapa(op=op):
            from radar.adapters.base import ErrorParseo
            from radar.red import ErrorDescarga

            try:
                avisos = descargar(op, store, cli)
            except (ErrorDescarga, ErrorParseo) as e:
                if not REGISTRO[op].clave_cnbv:
                    raise
                # Sitio caído o inalcanzable (Finaccess no responde a IPs fuera de México): se
                # re-parsea lo ya guardado y entra la cartera de la CNBV del mes; no se pierde el mes.
                avisos = [f"Sitio de la operadora sin respuesta ({type(e).__name__}); "
                          "se usan sus documentos guardados y la cartera de la CNBV"]
            for av in avisos:
                print(f"  AVISO {av}")
            return avisos + parsear(op, store, prm)

        if not _ejecutar(op, "fetch", etapa, store):
            rc = 1
            continue
        if a.corte != "latest":
            try:
                resolver_corte(store, op, a.corte)
            except ErrorCorte as e:
                print(f"  {e}. El sitio publica solo el corte vigente; no hay archivo histórico.", file=sys.stderr)
                rc = 2
    store.cerrar()
    return rc


def cmd_parse(a) -> int:
    prm = cargar_parametros()
    store = Store(ruta_db())
    rc = 0
    for op in _ops(a.operadora):
        print(f"== parse {op}")
        if not _ejecutar(op, "parse", lambda op=op: parsear(op, store, prm), store):
            rc = 1
    store.cerrar()
    return rc


def cmd_actualizar(a) -> int:
    """Lo que corre la tarea programada: fetch de todas + one-pagers + comparativo.
    Una operadora que falla queda registrada y no detiene a las demás."""
    from radar.render.html import render_comparativo, render_operadora

    a.operadora, a.corte = "todas", "latest"
    rc = cmd_fetch(a)
    prm = cargar_parametros()
    store = Store(ruta_db())
    dir_salidas().mkdir(parents=True, exist_ok=True)
    ms = []
    for op in sorted(REGISTRO):
        try:
            corte = resolver_corte(store, op, "latest")
            m = construir_metricas(op, corte, store, prm)
        except Exception as e:  # noqa: BLE001
            print(f"  sin entregable {op}: {e}", file=sys.stderr)
            continue
        if not m.fondos:
            continue
        (dir_salidas() / f"{op}_{corte.isoformat()}.html").write_text(
            render_operadora(m, prm), encoding="utf-8", newline=LF)
        ms.append(m)
    if ms:
        hoy = date.today().isoformat()
        (dir_salidas() / "comparativo_ultimo.html").write_text(
            render_comparativo(ms, prm, [hoy]), encoding="utf-8", newline=LF)
    store.cerrar()
    print(f"== {len(ms)} operadoras con entregable; código {rc}")
    return rc


def cmd_metrics(a) -> int:
    prm = cargar_parametros()
    store = Store(ruta_db())
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["operadora", "fondo", "corte", "activo_neto", "activo_neto_estimado", "pct_rv", "pct_rf", "pct_efe",
                "exposicion_rv", "share_local", "rv_max", "headroom", "rotacion_min", "rotacion_max",
                "rotacion_medida", "bolsa_min", "bolsa_max", "fuente"])
    for op in _ops(a.operadora):
        corte = resolver_corte(store, op, a.corte)
        m = construir_metricas(op, corte, store, prm)
        for f in m.fondos:
            lo, hi = f.bolsa_banda(prm)
            w.writerow([op, f.clave, f.fecha_corte, f"{f.activo_neto:.2f}", int(f.activo_neto_estimado),
                        f"{f.pct_rv:.6f}", f"{f.pct_rf:.6f}", f"{f.pct_efe:.6f}", f"{f.exposicion_rv:.2f}",
                        f"{f.share_local:.6f}", "" if f.rv_max is None else f"{f.rv_max:.4f}",
                        "" if f.headroom is None else f"{f.headroom:.2f}", f"{f.rotacion.minimo:.4f}",
                        f"{f.rotacion.maximo:.4f}", int(f.rotacion.medida), f"{lo:.2f}", f"{hi:.2f}",
                        f.cartera.procedencia.cita()])
    store.cerrar()
    sys.stdout.write(out.getvalue())
    return 0


def cmd_render(a) -> int:
    from radar.render.html import render_operadora

    prm = cargar_parametros()
    store = Store(ruta_db())
    dir_salidas().mkdir(parents=True, exist_ok=True)
    for op in _ops(a.operadora):
        corte = resolver_corte(store, op, a.corte)
        m = construir_metricas(op, corte, store, prm)
        ruta = dir_salidas() / f"{op}_{corte.isoformat()}.html"
        ruta.write_text(render_operadora(m, prm), encoding="utf-8", newline="\n")
        print(ruta)
    store.cerrar()
    return 0


def cmd_compare(a) -> int:
    from radar.render.html import render_comparativo

    prm = cargar_parametros()
    store = Store(ruta_db())
    pedidos = [c.strip() for c in a.cortes.split(",") if c.strip()]
    objetivo = pedidos[-1]
    ms = []
    for op in sorted(REGISTRO):
        try:
            corte = corte_a_lo_mas(store, op, objetivo)
        except ErrorCorte as e:
            print(f"  {e}", file=sys.stderr)
            continue
        ms.append(construir_metricas(op, corte, store, prm))
    if not ms:
        print("Sin operadoras con el corte pedido", file=sys.stderr)
        return 2
    dir_salidas().mkdir(parents=True, exist_ok=True)
    ruta = dir_salidas() / f"comparativo_{date.fromisoformat(objetivo).isoformat()}.html"
    ruta.write_text(render_comparativo(ms, prm, pedidos), encoding="utf-8", newline="\n")
    print(ruta)
    store.cerrar()
    return 0


def cmd_estado(a) -> int:
    """Estado por operadora, determinista (sin fechas): la tarea programada lo versiona
    y solo hace commit si cambió."""
    store = Store(ruta_db())
    for e in store.estados():
        docs = store.documentos(e["operadora"])
        dicis = [d.fecha_doc for d in docs if d.tipo == "dici" and d.fecha_doc]
        # Documentos guardados (por sha256) y DICI más reciente: cambia cuando llega uno nuevo,
        # aunque el PDF no se versione (los DICI de las híbridas no entran al repositorio).
        extra = f"	{len(docs)} doc(s)" + (f", DICI al {max(dicis).isoformat()}" if dicis else "")
        print(f"{e['operadora']}	{'OK' if e['ok'] else 'PENDIENTE'}	{e['etapa']}	{e['mensaje'][:300]}{extra}")
    store.cerrar()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="radar", description="Radar de operadoras de fondos")
    sub = p.add_subparsers(dest="cmd", required=True)
    for nombre, fn in (("discover", cmd_discover), ("fetch", cmd_fetch), ("parse", cmd_parse),
                       ("metrics", cmd_metrics), ("render", cmd_render)):
        s = sub.add_parser(nombre)
        s.add_argument("--operadora", required=True, help="clave de operadora o 'todas'")
        if nombre in ("fetch", "metrics", "render"):
            s.add_argument("--corte", default="latest", help="YYYY-MM-DD o latest")
        if nombre in ("discover", "fetch"):
            s.add_argument("--refrescar", action="store_true", help="ignora la caché HTTP del día")
        if nombre == "fetch":
            s.add_argument("--sin-cnbv", action="store_true", help="no descarga R1/R7 de la CNBV")
        s.set_defaults(fn=fn)
    s = sub.add_parser("actualizar", help="fetch de todas + entregables (tarea programada)")
    s.add_argument("--refrescar", action="store_true")
    s.add_argument("--sin-cnbv", action="store_true")
    s.set_defaults(fn=cmd_actualizar)
    s = sub.add_parser("estado", help="estado por operadora (sin fechas)")
    s.set_defaults(fn=cmd_estado)
    s = sub.add_parser("compare")
    s.add_argument("--cortes", required=True, help="lista de cortes separados por coma; se compara el último")
    s.set_defaults(fn=cmd_compare)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except ErrorCorte as e:
        print(str(e), file=sys.stderr)
        return 2
