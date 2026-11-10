"""Formato de cartera "Publicaciones" (mismo proveedor de software en varias
operadoras: Multiva, Vinci Compass).

  <CLAVE> <DENOMINACIÓN>
  CARTERA DE VALORES AL dd MES, aaaa
  Tipo Valor | Emisora | Serie | Calif./Bursatilidad | Cant. Títulos | Valor Razonable | Participación
  DIRECTO / <subsecciones> / TOTAL INVERSIONES EN DIRECTO
  REPORTO / TOTAL REPORTO
  OTROS VALORES                 (chequeras / depósitos; se verifica contra el DICI)
  OTROS TIPO DE VALOR <TV> - …  (posiciones agrupadas sin emisora)
  TOTAL DE INVERSIONES EN VALORES
  CATEGORÍA <código>

No publica activo neto: se usa el total de la cartera (e) salvo que la CNBV (R1)
dé el oficial del mismo día.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path

from radar.adapters.base import ErrorParseo, tipo_fondo_por_denominacion
from radar.core.modelo import Cartera, Categoria, Documento, Posicion, Procedencia
from radar.core.numeros import es_entero, es_monto, fecha_es, monto, sin_acentos
from radar.core.pdffilas import Fila, PaginaPdf, leer_pdf, numeros_por_caracter
from radar.core.tipos_valor import TipoValorDesconocido, categoria_por_tv

NOTA_ACTIVO_ESTIMADO = "Activo neto no publicado en la cartera: se usa el total de la cartera de valores (e)."


def categoria(tv: str, seccion: str, contexto: str) -> Categoria:
    try:
        return categoria_por_tv(tv, contexto, es_reporto=(seccion == "REPORTO"))
    except TipoValorDesconocido as e:
        raise ErrorParseo(str(e)) from e


def fecha_cartera(pg: PaginaPdf, etiqueta: str) -> date:
    for f in pg.filas():
        m = re.search(r"CARTERA DE VALORES AL (\d{1,2}) ([A-ZÁÉÍÓÚ]+),? (\d{4})", sin_acentos(f.texto).upper())
        if m:
            return fecha_es(*m.groups())
    raise ErrorParseo(f"{etiqueta}: no se encontró 'CARTERA DE VALORES AL dd MES, aaaa'")


def _es_renglon_de_datos(f: Fila) -> bool:
    tx = [p.texto for p in f.palabras]
    return (len(tx) >= 6 and re.match(r"^-?\d+(\.\d+)?$", tx[-1]) is not None and es_monto(tx[-2])
            and not sin_acentos(f.texto).upper().startswith(("OTROS", "TOTAL")))


def _columnas_datos(paginas: list[PaginaPdf]) -> dict[str, float]:
    """X de inicio de las columnas Emisora, Serie y Calificación tomada de los
    propios renglones de datos (moda por documento): el desfase entre encabezado
    y datos cambia entre operadoras."""
    em: Counter = Counter()
    se: Counter = Counter()
    ca: Counter = Counter()
    for pg in paginas:
        for f in pg.filas():
            if not _es_renglon_de_datos(f):
                continue
            w = f.palabras
            em[round(w[1].x0)] += 1
            se[round(w[2].x0)] += 1
            if not es_monto(w[3].texto):
                ca[round(w[3].x0)] += 1
    if not em or not se:
        return {}
    out = {"EMISORA": em.most_common(1)[0][0], "SERIE": se.most_common(1)[0][0]}
    if ca:
        out["CALIF"] = ca.most_common(1)[0][0]
    return out


def parsear(ruta: Path, doc: Documento, operadora: str, etiqueta: str) -> Cartera:
    paginas = leer_pdf(ruta)
    fecha = fecha_cartera(paginas[0], etiqueta)
    datos = _columnas_datos(paginas)
    clave = nombre_legal = cat_fondo = ""
    posiciones: list[Posicion] = []
    total = None
    seccion = ""
    subseccion = ""
    cols = None
    archivo = Path(doc.archivo).name
    esperado = doc.fondo_clave or ""
    for pg in paginas:
        filas = pg.filas()
        for j, f in enumerate(filas):
            t = f.texto
            tu = sin_acentos(t).upper()
            if not clave and esperado and f.palabras and f.palabras[0].texto == esperado:
                clave = esperado
                nombre_legal = " ".join(p.texto for p in f.palabras[1:])
                continue
            if tu.startswith("TIPO VALOR") and "EMISORA" in tu:
                cols = {sin_acentos(p.texto).upper(): p.x0 for p in f.palabras}
                cols.update({f"DATO_{k}": v for k, v in datos.items()})
                continue
            if tu.startswith("CATEGORIA") and j + 1 < len(filas):
                cat_fondo = filas[j + 1].texto.strip()
                continue
            if cols is None:
                continue
            if tu in ("DIRECTO", "REPORTO"):
                seccion, subseccion = tu, ""
                continue
            if tu.startswith("TOTAL DE INVERSIONES EN VALORES"):
                total = monto([p.texto for p in f.palabras if es_monto(p.texto) and "," in p.texto][0])
                seccion = "FIN"
                continue
            if tu.startswith("TOTAL"):
                continue
            if seccion in ("", "FIN"):
                continue
            pos = _posicion(f, cols, seccion, subseccion, doc, fecha, clave or esperado, archivo, etiqueta, ruta)
            if pos is None:
                if not any(re.search(r"\d", p.texto) for p in f.palabras):
                    subseccion = t.strip()
                continue
            posiciones.append(pos)
    if not clave:
        raise ErrorParseo(f"{etiqueta}: {archivo} no trae el encabezado del fondo {esperado}")
    if total is None:
        raise ErrorParseo(f"{etiqueta} {clave}: no se encontró TOTAL DE INVERSIONES EN VALORES en {archivo}")
    c = Cartera(
        operadora=operadora, fondo_clave=clave, nombre_legal=nombre_legal, categoria=cat_fondo,
        fecha_corte=fecha, tipo_doc=doc.tipo, activo_neto=total, activo_neto_estimado=True,
        total_cartera=total, posiciones=posiciones, procedencia=Procedencia(doc.doc_id, archivo, 1, fecha),
        tipo_fondo=tipo_fondo_por_denominacion(nombre_legal),
    )
    c.notas.append(NOTA_ACTIVO_ESTIMADO)
    return c


def _posicion(f: Fila, cols: dict[str, float], seccion: str, subseccion: str, doc: Documento,
              fecha: date, clave: str, archivo: str, etiqueta: str, ruta: Path) -> Posicion | None:
    w = f.palabras
    tx = [p.texto for p in w]
    tu = sin_acentos(f.texto).upper()
    if len(tx) < 3 or not re.match(r"^-?\d+(\.\d+)?$", tx[-1]):
        return None
    agregado = tu.startswith("OTROS TIPO DE VALOR")
    if not es_monto(tx[-2]) and not agregado:
        return None
    pct_cartera = float(tx[-1]) / 100
    valor = monto(tx[-2]) if es_monto(tx[-2]) else 0.0
    titulos = monto(tx[-3]) if len(tx) >= 4 and es_entero(tx[-3]) else None
    proc = Procedencia(doc.doc_id, archivo, f.pagina, fecha)
    contexto = f"{etiqueta} {clave} {fecha} '{f.texto}'"
    if tu.startswith("OTROS TIPO DE VALOR"):
        m = re.match(r"OTROS TIPO DE VALOR\s+(\S+)\s+-\s+(.*?)\s+[\d,]+\s+[\d,.]+\s+[\d.]+$", tu)
        if not m:
            # El PDF encima la etiqueta sobre las cifras: rescate por carácter.
            m2 = re.match(r"OTROS TIPO DE VALOR\s+(\S+)\s+-\s+(.*)$", tu)
            nums = numeros_por_caracter(ruta, f.pagina, min(p.top for p in w), max(p.bottom for p in w),
                                        cols.get("CANT.", 345) + 20)
            if not m2 or len(nums) < 3 or not es_monto(nums[-2]) or not es_entero(nums[-3]):
                raise ErrorParseo(f"Renglón agregado ilegible ({contexto})")
            titulos, valor, pct_txt = monto(nums[-3]), monto(nums[-2]), nums[-1]
            if abs(float(pct_txt) / 100 - pct_cartera) > 0.0001:
                raise ErrorParseo(f"Rescate por carácter inconsistente ({contexto}): {nums}")
            etiq = re.sub(r"[\d,]", "", m2.group(2)).strip()
            return Posicion(
                emisora_raw=f"OTROS TIPO DE VALOR {m2.group(1)}", tipo_valor=m2.group(1), emisora=f"OTROS-{m2.group(1)}",
                serie="", titulos=titulos, valor_razonable=valor, pct_cartera=pct_cartera,
                tipo_instrumento_raw=etiq, calificacion="", divisa="",
                categoria=categoria(m2.group(1), seccion, contexto), procedencia=proc, es_agregado=True,
                nota="Renglón agregado sin emisora; cifras rescatadas por carácter (texto encimado en el PDF)",
            )
        tv = m.group(1)
        return Posicion(
            emisora_raw=" ".join(tx[:-3]), tipo_valor=tv, emisora=f"OTROS-{tv}", serie="",
            titulos=titulos, valor_razonable=valor, pct_cartera=pct_cartera,
            tipo_instrumento_raw=m.group(2).strip(), calificacion="", divisa="",
            categoria=categoria(tv, seccion, contexto), procedencia=proc, es_agregado=True,
            nota="Renglón agregado por la operadora: sin emisora identificable",
        )
    if tu.startswith("OTROS VALORES"):
        return Posicion(
            emisora_raw="OTROS VALORES", tipo_valor="", emisora="OTROS-VALORES", serie="",
            titulos=titulos, valor_razonable=valor, pct_cartera=pct_cartera,
            tipo_instrumento_raw="OTROS VALORES", calificacion="", divisa="",
            categoria=Categoria.DEPOSITO, procedencia=proc, es_agregado=True,
            nota="Chequeras/depósitos a la vista agrupados; se verifica contra el DICI",
        )
    if "DATO_EMISORA" not in cols:
        raise ErrorParseo(f"{etiqueta} {clave}: no se pudieron ubicar las columnas de datos en {archivo}")
    x_em, x_se = cols["DATO_EMISORA"] - 4, cols["DATO_SERIE"] - 4
    x_ca = cols.get("DATO_CALIF", cols.get("CALIF.", x_se + 70)) - 6
    x_ti = cols.get("CANT.", x_ca + 100) - 20
    tv = " ".join(p.texto for p in w if p.x0 < x_em)
    emisora = " ".join(p.texto for p in w if x_em <= p.x0 < x_se)
    serie = " ".join(p.texto for p in w if x_se <= p.x0 < x_ca)
    calif = " ".join(p.texto for p in w if x_ca <= p.x0 < x_ti and not es_monto(p.texto))
    if not tv or not emisora:
        raise ErrorParseo(f"Posición sin tipo de valor o emisora ({contexto})")
    cat = categoria(tv, seccion, contexto)
    return Posicion(
        emisora_raw=f"{tv} {emisora} {serie}".strip(),
        tipo_valor=tv, emisora=emisora, serie=serie,
        titulos=titulos, valor_razonable=valor, pct_cartera=pct_cartera,
        tipo_instrumento_raw=subseccion or seccion, calificacion=calif, divisa="",
        categoria=cat, procedencia=proc,
        fondo_subyacente=emisora if cat is Categoria.FONDO else None,
    )
