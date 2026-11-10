"""Portafolio de Información de la CNBV, sector 52 (fondos de inversión).

  R1  activo neto diario por fondo     .../Reporte1/052_1G_R1_<AAAA>_S<1|2>.xlsm
  R7  cartera mensual de cada fondo     .../Reporte7/052_1G_R7_<AAAA>.xlsm

Cada archivo publicado trae UN solo periodo (el último cargado; ~45 días de
rezago) y sobrescribe el mismo URL: la serie solo existe si se descarga cada mes
y se guarda fechada, igual que los PDFs de las operadoras.

Los .xlsm se leen con openpyxl en modo datos (keep_vba=False): las macros NUNCA
se ejecutan. Solo se lee la hoja MINFO.
"""
from __future__ import annotations

import calendar
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import openpyxl

from radar.core.modelo import Cartera, Categoria, Documento, Posicion, Procedencia
from radar.core.numeros import sin_acentos
from radar.core.tipos_valor import categoria_por_tv, es_derivado

BASE = "https://portafolioinfdoctos.cnbv.gob.mx/Documentacion/minfo/XLS/52"
OPERADORA = "cnbv"

INVERSION_DIRECTA = "inversion en directo"
INVERSION_REPORTO = "operacion de reporto actuando como reportador"
INVERSION_PRESTAMO = "operacion de prestamo de valores actuando como prestamista"
INVERSION_DERIVADOS = "inversiones en instrumentos financieros derivados"
INVERSION_GARANTIAS = "garantias en val por inversiones en inst financ derivados"


class ErrorCnbv(ValueError):
    pass


def urls_vigentes(hoy: date) -> list[tuple[str, str]]:
    """(tipo, url) de los archivos que pueden traer el último periodo publicado."""
    sem = 1 if hoy.month <= 6 else 2
    sem_ant = (hoy.year, 1) if sem == 2 else (hoy.year - 1, 2)
    return [
        ("cnbv_r7", f"{BASE}/Reporte7/052_1G_R7_{hoy.year}.xlsm"),
        ("cnbv_r7", f"{BASE}/Reporte7/052_1G_R7_{hoy.year - 1}.xlsm"),
        ("cnbv_r1", f"{BASE}/Reporte1/052_1G_R1_{hoy.year}_S{sem}.xlsm"),
        ("cnbv_r1", f"{BASE}/Reporte1/052_1G_R1_{sem_ant[0]}_S{sem_ant[1]}.xlsm"),
    ]


def _clave(s) -> str:
    return sin_acentos(str(s)).strip().lower()


def _texto(v) -> str:
    """Celdas como "'1ASP" o números (emisora 40156) -> texto limpio."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip().lstrip("'")


@dataclass
class FilaMinfo:
    fila: int            # número de fila en la hoja (procedencia)
    datos: dict[str, object]


def leer_minfo(ruta: Path) -> list[FilaMinfo]:
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True, keep_vba=False)
    try:
        if "MINFO" not in wb.sheetnames:
            raise ErrorCnbv(f"{ruta.name}: no tiene hoja MINFO")
        ws = wb["MINFO"]
        encabezado: list[str] | None = None
        i0 = 0
        out: list[FilaMinfo] = []
        for n, row in enumerate(ws.iter_rows(values_only=True), start=1):
            r = list(row)
            if encabezado is None:
                if "Periodo" in r:
                    i0 = r.index("Periodo")
                    encabezado = [_clave(x) for x in r[i0:] if x is not None]
                continue
            vals = r[i0:i0 + len(encabezado)]
            if not vals or vals[0] is None:
                continue
            out.append(FilaMinfo(n, dict(zip(encabezado, vals))))
        if encabezado is None:
            raise ErrorCnbv(f"{ruta.name}: no se encontró el encabezado 'Periodo' en MINFO")
        return out
    finally:
        wb.close()


def periodo_a_fecha(p) -> date:
    s = str(int(p))
    if len(s) == 8:
        return date(int(s[:4]), int(s[4:6]), int(s[6:]))
    if len(s) == 6:
        y, m = int(s[:4]), int(s[4:])
        return date(y, m, calendar.monthrange(y, m)[1])
    raise ErrorCnbv(f"Periodo ilegible: {p!r}")


def fecha_documento(tipo: str, ruta: Path) -> date | None:
    filas = leer_minfo(ruta)
    return max((periodo_a_fecha(f.datos["periodo"]) for f in filas), default=None)


def sha(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


# ------------------------------------------------------------------- R1
@dataclass(frozen=True)
class ActivoNeto:
    fondo: str
    fecha: date
    activo_neto: float
    tipo_fondo: str
    clasificacion: str
    procedencia: Procedencia


def activos_r1(filas: list[FilaMinfo], cve: str, doc: Documento) -> list[ActivoNeto]:
    out = []
    for f in filas:
        d = f.datos
        if _texto(d.get("operadora")) != cve or d.get("activo neto diario") is None:
            continue
        fecha = periodo_a_fecha(d["periodo"])
        out.append(ActivoNeto(
            fondo=_texto(d["fondo"]), fecha=fecha, activo_neto=float(d["activo neto diario"]),
            tipo_fondo=_texto(d.get("tipo fondo")), clasificacion=_texto(d.get("clasificacion")),
            procedencia=Procedencia(doc.doc_id, Path(doc.archivo).name, f.fila, fecha),
        ))
    return out


# ------------------------------------------------------------------- R7
def carteras_r7(filas: list[FilaMinfo], operadora: str, cve: str, doc: Documento,
                fecha_por_mes: dict[tuple[int, int], date] | None = None) -> list[Cartera]:
    """Una Cartera por fondo de la operadora. R7 no publica total: total_cartera =
    suma de posiciones y se concilia contra el activo neto de R1."""
    por_fondo: dict[str, list[FilaMinfo]] = {}
    for f in filas:
        if _texto(f.datos.get("operadora")) == cve:
            por_fondo.setdefault(_texto(f.datos["fondo"]), []).append(f)
    archivo = Path(doc.archivo).name
    out: list[Cartera] = []
    for fondo in sorted(por_fondo):
        rows = por_fondo[fondo]
        mes = periodo_a_fecha(rows[0].datos["periodo"])
        fecha = (fecha_por_mes or {}).get((mes.year, mes.month), mes)
        posiciones: list[Posicion] = []
        tipo_fondo = ""
        derivados = 0.0
        n_derivados = 0
        for f in rows:
            d = f.datos
            tipo_fondo = tipo_fondo or _texto(d.get("tipo de fondo"))
            valor = d.get("valor a mercado total")
            if valor is None:
                continue
            inversion = _clave(d.get("tipo de inversion", ""))
            tv = _texto(d.get("tv"))
            emisora = _texto(d.get("emisora"))
            serie = _texto(d.get("serie"))
            contexto = f"CNBV R7 {cve}/{fondo} {mes:%Y-%m} fila {f.fila}"
            if inversion == INVERSION_DERIVADOS or es_derivado(tv):
                derivados += float(valor)
                n_derivados += 1
                continue
            if inversion not in (INVERSION_DIRECTA, INVERSION_REPORTO, INVERSION_PRESTAMO, INVERSION_GARANTIAS):
                raise ErrorCnbv(
                    f"Tipo de inversión sin regla de clasificación: {d.get('tipo de inversion')!r} ({contexto})"
                )
            cat = categoria_por_tv(tv, contexto, es_reporto=(inversion == INVERSION_REPORTO))
            titulos = d.get("titulos")
            posiciones.append(Posicion(
                emisora_raw=f"{tv}_{emisora}_{serie}", tipo_valor=tv, emisora=emisora, serie=serie,
                titulos=float(titulos) if titulos is not None else None,
                valor_razonable=float(valor), pct_cartera=None,
                tipo_instrumento_raw=_texto(d.get("tipo valor")), calificacion="", divisa="",
                categoria=cat, procedencia=Procedencia(doc.doc_id, archivo, f.fila, fecha),
                fondo_subyacente=emisora if cat is Categoria.FONDO else None,
                nota="préstamo de valores (sigue en cartera)" if inversion == INVERSION_PRESTAMO else "",
            ))
        total = sum(p.valor_razonable for p in posiciones)
        for p in posiciones:
            p.pct_cartera = p.valor_razonable / total if total else None
        out.append(Cartera(
            operadora=operadora, fondo_clave=fondo, nombre_legal="", categoria="",
            fecha_corte=fecha, tipo_doc="cnbv_r7", activo_neto=total, activo_neto_estimado=True,
            total_cartera=total, posiciones=posiciones,
            procedencia=Procedencia(doc.doc_id, archivo, rows[0].fila, fecha),
            tipo_fondo="RV" if "variable" in _clave(tipo_fondo) else "RF",
            notas=["Cartera tomada del reporte R7 de la CNBV (no publica total; se concilia contra R1)."]
            + ([f"Derivados excluidos de la mezcla: {n_derivados} posición(es), valor {derivados:,.0f}."]
               if n_derivados else []),
        ))
    return out
