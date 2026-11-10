"""Histórico de cortes en SQLite. Clave: operadora + fondo + fecha_corte.

Cada documento descargado se guarda fechado (sha256) porque varias operadoras
sobrescriben el mismo URL cada mes: sin esto se pierde la serie.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from radar.core.modelo import (
    Cartera, Categoria, Dici, Documento, FondoDescubierto, PerfilOperadora, Posicion, Procedencia,
    SerieDici, a_dict,
)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS documentos(
  doc_id TEXT PRIMARY KEY, operadora TEXT, fondo_clave TEXT, tipo TEXT, url TEXT,
  archivo TEXT, fecha_doc TEXT, descargado TEXT, bytes INTEGER);
CREATE TABLE IF NOT EXISTS universo(
  operadora TEXT, fondo_clave TEXT, estatus TEXT, nombre_comercial TEXT, nota TEXT,
  PRIMARY KEY(operadora, fondo_clave));
CREATE TABLE IF NOT EXISTS carteras(
  operadora TEXT, fondo_clave TEXT, fecha_corte TEXT, tipo_doc TEXT, nombre_legal TEXT,
  categoria TEXT, tipo_fondo TEXT, nombre_corto TEXT, activo_neto REAL, activo_neto_estimado INTEGER,
  total_cartera REAL, doc_id TEXT, archivo TEXT, pagina INTEGER, notas TEXT,
  PRIMARY KEY(operadora, fondo_clave, fecha_corte));
CREATE TABLE IF NOT EXISTS posiciones(
  operadora TEXT, fondo_clave TEXT, fecha_corte TEXT, n INTEGER,
  emisora_raw TEXT, tipo_valor TEXT, emisora TEXT, serie TEXT, emisora_canonica TEXT,
  titulos REAL, valor_razonable REAL, pct_cartera REAL, tipo_instrumento_raw TEXT,
  calificacion TEXT, divisa TEXT, categoria TEXT, clase TEXT, mercado TEXT,
  es_agregado INTEGER, nota TEXT, fondo_subyacente TEXT, doc_id TEXT, archivo TEXT, pagina INTEGER,
  PRIMARY KEY(operadora, fondo_clave, fecha_corte, n));
CREATE TABLE IF NOT EXISTS dicis(
  operadora TEXT, fondo_clave TEXT, fecha_doc TEXT, doc_id TEXT, json TEXT,
  PRIMARY KEY(operadora, fondo_clave, fecha_doc));
CREATE TABLE IF NOT EXISTS perfiles(operadora TEXT PRIMARY KEY, json TEXT);
CREATE TABLE IF NOT EXISTS estado(
  operadora TEXT PRIMARY KEY, fecha TEXT, ok INTEGER, etapa TEXT, mensaje TEXT, detalle TEXT);
CREATE TABLE IF NOT EXISTS activos_netos(
  operadora TEXT, fondo_clave TEXT, fecha TEXT, activo_neto REAL, doc_id TEXT, archivo TEXT, fila INTEGER,
  PRIMARY KEY(operadora, fondo_clave, fecha));
CREATE TABLE IF NOT EXISTS conciliaciones(
  operadora TEXT, fondo_clave TEXT, fecha TEXT, concepto TEXT,
  fuente_a TEXT, monto_a REAL, cita_a TEXT, fuente_b TEXT, monto_b REAL, cita_b TEXT,
  PRIMARY KEY(operadora, fondo_clave, fecha, concepto));
"""


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


class Store:
    def __init__(self, ruta: Path) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.cx = sqlite3.connect(ruta)
        self.cx.executescript(ESQUEMA)

    def cerrar(self) -> None:
        self.cx.commit()
        self.cx.close()

    # -------------------------------------------------------------- documentos
    def guardar_documento(self, d: Documento) -> None:
        self.cx.execute(
            "INSERT OR REPLACE INTO documentos VALUES (?,?,?,?,?,?,?,?,?)",
            (d.doc_id, d.operadora, d.fondo_clave, d.tipo, d.url, d.archivo,
             d.fecha_doc.isoformat() if d.fecha_doc else None, d.descargado.isoformat(), d.bytes),
        )
        self.cx.commit()

    def documentos(self, operadora: str, tipo: str | None = None) -> list[Documento]:
        q = "SELECT * FROM documentos WHERE operadora=?"
        args: list = [operadora]
        if tipo:
            q += " AND tipo=?"
            args.append(tipo)
        q += " ORDER BY fondo_clave, tipo, fecha_doc, descargado, doc_id"
        return [
            Documento(r[0], r[1], r[2], r[3], r[4], r[5], _d(r[6]), date.fromisoformat(r[7]), r[8])
            for r in self.cx.execute(q, args)
        ]

    # ---------------------------------------------------------------- universo
    def guardar_universo(self, operadora: str, fondos: list[FondoDescubierto]) -> None:
        for f in fondos:
            previo = self.cx.execute(
                "SELECT nombre_comercial FROM universo WHERE operadora=? AND fondo_clave=?", (operadora, f.clave)
            ).fetchone()
            nombre = f.nombre_comercial or (previo[0] if previo else "")
            self.cx.execute(
                "INSERT OR REPLACE INTO universo VALUES (?,?,?,?,?)",
                (operadora, f.clave, f.estatus, nombre, f.nota),
            )
        self.cx.commit()

    def universo(self, operadora: str) -> list[FondoDescubierto]:
        return [
            FondoDescubierto(r[0], r[2], r[1], {}, r[3])
            for r in self.cx.execute(
                "SELECT fondo_clave, estatus, nombre_comercial, nota FROM universo WHERE operadora=? ORDER BY fondo_clave",
                (operadora,),
            )
        ]

    # ---------------------------------------------------------------- carteras
    def mensual_del_mes(self, operadora: str, fondo: str, f: date, tipo: str = "cartera_mensual") -> str | None:
        r = self.cx.execute(
            "SELECT fecha_corte FROM carteras WHERE operadora=? AND fondo_clave=? AND tipo_doc=? "
            "AND substr(fecha_corte,1,7)=?", (operadora, fondo, tipo, f.isoformat()[:7]),
        ).fetchone()
        return r[0] if r else None

    def guardar_cartera(self, c: Cartera) -> bool:
        """Guarda un corte. Prioridad dentro de un mismo mes: la cartera mensual de
        la operadora manda sobre R7 de la CNBV (que entonces solo concilia), para
        no crear dos cortes del mismo mes a días de distancia."""
        f = c.fecha_corte.isoformat()
        if c.tipo_doc == "cnbv_r7" and self.mensual_del_mes(c.operadora, c.fondo_clave, c.fecha_corte):
            return False
        if c.tipo_doc == "cartera_mensual":
            otra = self.mensual_del_mes(c.operadora, c.fondo_clave, c.fecha_corte, "cnbv_r7")
            if otra:
                self.cx.execute("DELETE FROM posiciones WHERE operadora=? AND fondo_clave=? AND fecha_corte=?",
                                (c.operadora, c.fondo_clave, otra))
                self.cx.execute("DELETE FROM carteras WHERE operadora=? AND fondo_clave=? AND fecha_corte=?",
                                (c.operadora, c.fondo_clave, otra))
        previo = self.cx.execute(
            "SELECT tipo_doc FROM carteras WHERE operadora=? AND fondo_clave=? AND fecha_corte=?",
            (c.operadora, c.fondo_clave, f),
        ).fetchone()
        if previo and previo[0] == "cartera_mensual" and c.tipo_doc != "cartera_mensual":
            return False  # la mensual manda sobre otro documento con el mismo corte
        self.cx.execute("DELETE FROM posiciones WHERE operadora=? AND fondo_clave=? AND fecha_corte=?",
                        (c.operadora, c.fondo_clave, f))
        self.cx.execute(
            "INSERT OR REPLACE INTO carteras VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (c.operadora, c.fondo_clave, f, c.tipo_doc, c.nombre_legal, c.categoria, c.tipo_fondo,
             c.nombre_corto, c.activo_neto, int(c.activo_neto_estimado), c.total_cartera,
             c.procedencia.doc_id, c.procedencia.archivo, c.procedencia.pagina, json.dumps(c.notas, ensure_ascii=False)),
        )
        self.cx.executemany(
            "INSERT INTO posiciones VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (c.operadora, c.fondo_clave, f, i, p.emisora_raw, p.tipo_valor, p.emisora, p.serie,
                 p.emisora_canonica, p.titulos, p.valor_razonable, p.pct_cartera, p.tipo_instrumento_raw,
                 p.calificacion, p.divisa, p.categoria.value, p.clase, p.mercado, int(p.es_agregado), p.nota,
                 p.fondo_subyacente, p.procedencia.doc_id, p.procedencia.archivo, p.procedencia.pagina)
                for i, p in enumerate(c.posiciones)
            ],
        )
        self.cx.commit()
        return True

    def cortes(self, operadora: str, solo_mensuales: bool = False) -> list[date]:
        """solo_mensuales: cortes de fin de mes (cartera mensual de la operadora o R7 CNBV)."""
        q = "SELECT DISTINCT fecha_corte FROM carteras WHERE operadora=?"
        if solo_mensuales:
            q += " AND tipo_doc IN ('cartera_mensual','cnbv_r7')"
        return [date.fromisoformat(r[0]) for r in self.cx.execute(q + " ORDER BY fecha_corte", (operadora,))]

    def carteras(self, operadora: str, fecha_corte: date | None = None) -> list[Cartera]:
        q = "SELECT * FROM carteras WHERE operadora=?"
        args: list = [operadora]
        if fecha_corte:
            q += " AND fecha_corte=?"
            args.append(fecha_corte.isoformat())
        out = []
        for r in self.cx.execute(q + " ORDER BY fondo_clave, fecha_corte", args).fetchall():
            fc = date.fromisoformat(r[2])
            pos = [
                Posicion(
                    emisora_raw=p[4], tipo_valor=p[5], emisora=p[6], serie=p[7], titulos=p[9],
                    valor_razonable=p[10], pct_cartera=p[11], tipo_instrumento_raw=p[12], calificacion=p[13],
                    divisa=p[14], categoria=Categoria(p[15]), procedencia=Procedencia(p[21], p[22], p[23], fc),
                    es_agregado=bool(p[18]), nota=p[19], fondo_subyacente=p[20], emisora_canonica=p[8],
                    clase=p[16], mercado=p[17],
                )
                for p in self.cx.execute(
                    "SELECT * FROM posiciones WHERE operadora=? AND fondo_clave=? AND fecha_corte=? ORDER BY n",
                    (r[0], r[1], r[2]),
                )
            ]
            out.append(Cartera(
                operadora=r[0], fondo_clave=r[1], nombre_legal=r[4], categoria=r[5], fecha_corte=fc,
                tipo_doc=r[3], activo_neto=r[8], activo_neto_estimado=bool(r[9]), total_cartera=r[10],
                posiciones=pos, procedencia=Procedencia(r[11], r[12], r[13], fc), tipo_fondo=r[6],
                nombre_corto=r[7], notas=json.loads(r[14] or "[]"),
            ))
        return out

    # ------------------------------------------------------- activo neto oficial
    def guardar_activo_neto(self, operadora: str, fondo: str, fecha: date, an: float, proc: Procedencia) -> None:
        self.cx.execute("INSERT OR REPLACE INTO activos_netos VALUES (?,?,?,?,?,?,?)",
                        (operadora, fondo, fecha.isoformat(), an, proc.doc_id, proc.archivo, proc.pagina))
        self.cx.commit()

    def activo_neto_oficial(self, operadora: str, fondo: str, fecha: date, dias: int = 3) -> tuple[float, Procedencia] | None:
        """Activo neto CNBV R1 del mismo mes y a lo más `dias` de distancia."""
        mejor = None
        for r in self.cx.execute(
            "SELECT fecha, activo_neto, doc_id, archivo, fila FROM activos_netos "
            "WHERE operadora=? AND fondo_clave=? AND substr(fecha,1,7)=?",
            (operadora, fondo, fecha.isoformat()[:7]),
        ):
            f = date.fromisoformat(r[0])
            d = abs((f - fecha).days)
            if d <= dias and (mejor is None or d < mejor[0]):
                mejor = (d, r[1], Procedencia(r[2], r[3], r[4], f))
        return (mejor[1], mejor[2]) if mejor else None

    def fondos_r1(self, operadora: str) -> dict[str, date]:
        return {r[0]: date.fromisoformat(r[1]) for r in self.cx.execute(
            "SELECT fondo_clave, max(fecha) FROM activos_netos WHERE operadora=? GROUP BY fondo_clave", (operadora,))}

    # ------------------------------------------------------------------ estado
    def guardar_estado(self, operadora: str, fecha: str, ok: bool, etapa: str, mensaje: str,
                       detalle: dict | None = None) -> None:
        self.cx.execute("INSERT OR REPLACE INTO estado VALUES (?,?,?,?,?,?)",
                        (operadora, fecha, int(ok), etapa, mensaje,
                         json.dumps(detalle or {}, ensure_ascii=False, sort_keys=True)))
        self.cx.commit()

    def estados(self) -> list[dict]:
        cols = ["operadora", "fecha", "ok", "etapa", "mensaje", "detalle"]
        out = []
        for r in self.cx.execute("SELECT * FROM estado ORDER BY operadora"):
            d = dict(zip(cols, r))
            d["ok"] = bool(d["ok"])
            d["detalle"] = json.loads(d["detalle"] or "{}")
            out.append(d)
        return out

    # ----------------------------------------------------------- conciliaciones
    def guardar_conciliacion(self, operadora: str, fondo: str, fecha: date, concepto: str,
                             a: tuple[str, float, str], b: tuple[str, float, str]) -> None:
        self.cx.execute("INSERT OR REPLACE INTO conciliaciones VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (operadora, fondo, fecha.isoformat(), concepto, *a, *b))
        self.cx.commit()

    def conciliaciones(self, operadora: str, fondo: str | None = None) -> list[dict]:
        q = "SELECT * FROM conciliaciones WHERE operadora=?"
        args: list = [operadora]
        if fondo:
            q += " AND fondo_clave=?"
            args.append(fondo)
        cols = ["operadora", "fondo", "fecha", "concepto", "fuente_a", "monto_a", "cita_a", "fuente_b", "monto_b", "cita_b"]
        return [dict(zip(cols, r)) for r in self.cx.execute(q + " ORDER BY fondo_clave, fecha, concepto", args)]

    # ------------------------------------------------------------------- DICI
    def guardar_dici(self, d: Dici) -> None:
        self.cx.execute(
            "INSERT OR REPLACE INTO dicis VALUES (?,?,?,?,?)",
            (d.operadora, d.fondo_clave, d.fecha_doc.isoformat() if d.fecha_doc else "",
             d.procedencia.doc_id, json.dumps(a_dict(d), ensure_ascii=False, sort_keys=True)),
        )
        self.cx.commit()

    def dicis(self, operadora: str) -> list[Dici]:
        out = []
        for (j,) in self.cx.execute(
            "SELECT json FROM dicis WHERE operadora=? ORDER BY fondo_clave, fecha_doc", (operadora,)
        ):
            out.append(dici_desde_dict(json.loads(j)))
        return out

    # ---------------------------------------------------------------- perfiles
    def guardar_perfil(self, p: PerfilOperadora) -> None:
        self.cx.execute("INSERT OR REPLACE INTO perfiles VALUES (?,?)",
                        (p.clave, json.dumps(a_dict(p), ensure_ascii=False, sort_keys=True)))
        self.cx.commit()

    def perfil(self, operadora: str) -> PerfilOperadora | None:
        r = self.cx.execute("SELECT json FROM perfiles WHERE operadora=?", (operadora,)).fetchone()
        return PerfilOperadora(**json.loads(r[0])) if r else None


def _proc(d: dict | None) -> Procedencia | None:
    if not d:
        return None
    return Procedencia(d["doc_id"], d["archivo"], d["pagina"], _d(d["fecha_doc"]))


def dici_desde_dict(d: dict) -> Dici:
    return Dici(
        operadora=d["operadora"], fondo_clave=d["fondo_clave"], fecha_doc=_d(d["fecha_doc"]),
        categoria_regulatoria=d["categoria_regulatoria"], rv_min=d["rv_min"], rv_max=d["rv_max"],
        fuente_regimen=_proc(d["fuente_regimen"]), liquidez=d["liquidez"],
        plazo_liquidacion=d["plazo_liquidacion"], limite_recompra=d["limite_recompra"],
        indice_referencia=d["indice_referencia"], distribuidoras=d["distribuidoras"],
        series=[SerieDici(s["serie"], s["posibles_adquirentes"], s["monto_minimo"],
                          s["comision_administracion"], s["costo_total"], _proc(s["procedencia"]))
                for s in d["series"]],
        composicion_total=d["composicion_total"], procedencia=_proc(d["procedencia"]),
        notas=d["notas"], componentes_composicion=d.get("componentes_composicion", {}),
    )
