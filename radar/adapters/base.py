"""Contrato de un adaptador de operadora.

Agregar una operadora = escribir un módulo nuevo que implemente esta clase y
registrarlo en radar/adapters/__init__.py. El núcleo no se toca.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from radar.core.modelo import Cartera, Dici, Documento, FondoDescubierto, PerfilOperadora
from radar.core.numeros import es_pct, pct, sin_acentos
from radar.core.pdffilas import Fila, PaginaPdf, Palabra
from radar.red import Cliente


class ErrorParseo(ValueError):
    """El documento no tiene el formato esperado. Mejor fallar que adivinar."""


@dataclass(frozen=True)
class DocARevisar:
    fondo_clave: str | None
    tipo: str          # cartera_mensual | cartera_diaria | dici | prospecto | prospecto_generico
    url: str
    nombre_archivo: str
    #: URLs de respaldo (otra copia del mismo documento), en orden de preferencia
    alternativas: tuple[str, ...] = ()
    #: si no existe en ninguna URL no es error: se junta en un solo aviso de cobertura
    opcional: bool = False

    @property
    def urls(self) -> tuple[str, ...]:
        return (self.url, *self.alternativas)


class Adaptador(ABC):
    clave: str
    nombre: str
    clave_cnbv: str | None = None   # clave de la operadora en los reportes de la CNBV (R1, R7)

    @abstractmethod
    def perfil(self, dicis: list[Dici]) -> PerfilOperadora:
        """Declara expresamente si la operadora tiene casa de bolsa hermana,
        con la evidencia (distribuidoras del DICI)."""

    @abstractmethod
    def descubrir(self, cliente: Cliente) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
        """Fondos de la operadora (con estatus) y documentos a descargar."""

    @abstractmethod
    def fecha_documento(self, tipo: str, ruta: Path) -> date | None:
        """Fecha de corte del documento leída de su contenido (no de la URL)."""

    @abstractmethod
    def parsear_cartera(self, ruta: Path, doc: Documento) -> Cartera: ...

    @abstractmethod
    def parsear_dici(self, ruta: Path, doc: Documento, prospecto: tuple[Path, Documento] | None) -> Dici: ...

    def validar_dici_contra_cartera(self, dici: Dici, cartera: Cartera) -> list[str]:
        """Notas de verificación cruzada específicas de la operadora."""
        return []


# --- utilidades compartidas por adaptadores -------------------------------------

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", sin_acentos(s)).strip().lower()


def tipo_fondo_por_denominacion(nombre_legal: str) -> str:
    n = norm(nombre_legal)
    if "renta variable" in n:
        return "RV"
    if "deuda" in n:
        return "RF"
    raise ErrorParseo(f"No se reconoce el tipo de fondo en la denominación: {nombre_legal!r}")


def _es_encabezado_regimen(f: Fila) -> bool:
    """'PARÁMETROS MÍNIMO MÁXIMO' o 'Mínimos Máximos': renglón corto con ambas
    palabras sueltas (no la prosa 'mínimo 50% y máximo 80%')."""
    palabras = [sin_acentos(p.texto).upper().strip(".:") for p in f.palabras]
    return (
        len(palabras) <= 12
        and any(w in ("MINIMO", "MINIMOS") for w in palabras)
        and any(w in ("MAXIMO", "MAXIMOS") for w in palabras)
        and not any(es_pct(p.texto) for p in f.palabras)
    )


def regimen_desde_texto(texto: str) -> tuple[float | None, float | None]:
    """Respaldo: prosa tipo 'Por lo menos 80% ... renta variable ... máximo 100%'
    o 'entre mínimo 20% y máximo 50% en fondos de inversión de renta variable'."""
    t = re.sub(r"\s+", " ", norm(texto))
    for trozo in re.split(r"[•]|(?<=\.)\s|\s[a-f]\)\s", t):
        if "renta variable" not in trozo:
            continue
        mn = re.search(r"(?:por lo menos|minimo|al menos)\s+(?:el\s+|de\s+)?(\d+(?:\.\d+)?)\s?%", trozo)
        mx = re.search(r"maximo\s+(?:de\s+|el\s+|del\s+)?(\d+(?:\.\d+)?)\s?%", trozo)
        if mx:
            return (float(mn.group(1)) / 100 if mn else 0.0), float(mx.group(1)) / 100
    return None, None


def _es_renglon_rv(etiqueta: str) -> bool:
    """Renglón del régimen que limita renta variable: dice 'renta variable', o habla
    de acciones/títulos referenciados a acciones sin ser de deuda."""
    n = norm(etiqueta)
    return "renta variable" in n or ("acciones" in n and "deuda" not in n)


def _regimen_por_inciso(region, hdr: Fila, x_min: float) -> list[tuple[str, float, float]] | None:
    """Tabla con incisos "a. …" (BlackRock). None si no aplica o no se puede leer."""
    literales = [f for f, _, _ in region if re.match(r"^[a-z]\.\s", f.texto)]
    if len(literales) < 3:
        return None
    renglones: list[tuple[str, float, float]] = []
    # BlackRock: renglones "a. Valores ...". Las cifras van en el mismo renglón o en
    # uno propio (arriba, abajo o a media etiqueta); el mínimo en blanco o "--" es 0 %.
    # Columna (mínimo / máximo) por la X respecto del encabezado. Una tabla con más
    # de dos cifras por renglón (LifePath: una columna por año) no se puede leer.
    x_max = next(p.x0 for p in hdr.palabras if "MAXIMO" in sin_acentos(p.texto).upper())
    corte = (x_min + x_max) / 2
    textos: dict[int, list[str]] = {i: [] for i in range(len(literales))}
    cifras: dict[int, list[Palabra]] = {i: [] for i in range(len(literales))}
    j = -1
    for f, etiqueta, valores in region:
        if f in literales:
            j = literales.index(f)
            cifras[j].extend(p for p in f.palabras if p.x0 >= x_min - 15 and es_pct(p.texto))
        elif valores and not etiqueta:
            # Renglón solo de cifras: va al inciso que empieza justo debajo (<= 8 pt)
            # o, si no, al inciso en cuyo bloque cae (etiqueta larga centrada).
            abajo = [k for k, g in enumerate(literales) if 0 <= g.top - f.top <= 8]
            arriba = [k for k, g in enumerate(literales) if g.top < f.top]
            i = abajo[0] if abajo else (arriba[-1] if arriba else None)
            if i is not None:
                cifras[i].extend(p for p in f.palabras if es_pct(p.texto))
            continue
        if j >= 0 and etiqueta:
            textos[j].append(" ".join(etiqueta))
    if any(len(v) > 2 for v in cifras.values()):
        return None
    for i in range(len(literales)):
        mx_ = [p for p in cifras[i] if p.x0 >= corte]
        mn_ = [p for p in cifras[i] if p.x0 < corte]
        if len(mx_) == 1 and len(mn_) <= 1:
            renglones.append((" ".join(textos[i]), pct(mn_[0].texto) if mn_ else 0.0, pct(mx_[0].texto)))
    return renglones


def regimen_desde_tabla(paginas, max_paginas: int = 40) -> tuple[float | None, float | None, int | None, list[tuple[str, float, float]]]:
    """Lee la tabla 'PARÁMETROS / MÍNIMO / MÁXIMO' del régimen de inversión.

    Devuelve (rv_min, rv_max, página, renglones RV). rv_max = máximo de los
    máximos de renglones que hablan de renta variable (tope 100 %); rv_min = el
    mayor de sus mínimos. Si la tabla existe y no tiene renglones de RV, el fondo
    no puede tener RV: (0, 0).
    """
    it = iter(paginas)
    for pg in it:
        if pg.numero > max_paginas:
            break
        filas = pg.filas()
        hdr = next((f for f in filas if _es_encabezado_regimen(f)), None)
        if hdr is None:
            continue
        # La tabla puede seguir en la página siguiente.
        sig = next(it, None)
        if sig is not None:
            filas = filas + [Fila(f.pagina, f.top + 10_000, f.palabras) for f in sig.filas()]
        x_min = next(p.x0 for p in hdr.palabras if "MINIMO" in sin_acentos(p.texto).upper())
        # Región de la tabla: desde el encabezado hasta 5 renglones sin valores
        # seguidos o el renglón del VaR.
        region: list[tuple[Fila, list[str], list[str]]] = []
        sin_valores = 0
        for f in filas:
            if f.top <= hdr.top:
                continue
            n = norm(f.texto)
            if "valor en riesgo" in n or n.startswith(("* nota", "*nota")):
                break
            if re.fullmatch(r"\d{1,3}", n):  # número de página
                continue
            etiqueta = [p.texto for p in f.palabras if p.x0 < x_min - 15]
            valores = [p.texto for p in f.palabras if p.x0 >= x_min - 15 and es_pct(p.texto)]
            region.append((f, etiqueta, valores))
            # Un renglón solo con cifras (sin etiqueta) también es de la tabla (BlackRock).
            sin_valores = 0 if len(valores) >= 2 or (valores and not etiqueta) else sin_valores + 1
            if sin_valores > 9 and any(len(v) >= 2 for _, _, v in region):
                break
        if any(len(v) > 3 for _, _, v in region):
            continue  # una columna por año (LifePath / fecha objetivo): sin mínimo y máximo únicos
        renglones: list[tuple[str, float, float]] = []
        numerada = any(re.match(r"^\d+\)", f.texto) for f, _, _ in region)
        por_letra = [f for f, _, _ in region if re.match(r"^[a-z]\.\d+\b", f.texto)]
        if por_letra:
            # Compass "c.1 …" con valores apilados: solo si renglones y pares de cifras se
            # pueden emparejar con certeza; si no, se lee por cercanía (modo Multiva).
            pares = [v for _, _, v in region if len(v) >= 2]
            if not pares or len(pares) > len(por_letra) or len(por_letra) - len(pares) > 1:
                por_letra = []
        lit = None if por_letra or numerada else _regimen_por_inciso(region, hdr, x_min)
        if lit and any(_es_renglon_rv(r[0]) for r in lit):
            renglones = lit
        elif por_letra:
            # Compass: renglones "c.1 …", etiquetas centradas alrededor del renglón
            # numerado y valores apilados en una columna aparte, en el mismo orden.
            etiquetas: dict[int, list[tuple[float, str]]] = {i: [] for i in range(len(por_letra))}
            for f, etiqueta, _ in region:
                if not etiqueta:
                    continue
                i = min(range(len(por_letra)), key=lambda k: abs(por_letra[k].top - f.top))
                etiquetas[i].append((f.top, " ".join(etiqueta)))
            for i, v in enumerate(pares):
                txt = " ".join(t for _, t in sorted(etiquetas[i]))
                renglones.append((txt, pct(v[0]), pct(v[1])))
        elif numerada:
            # Finaccess: "8) Inversión en ... 60% 100%", etiquetas que envuelven hacia abajo.
            acumulado: list[str] = []
            for f, etiqueta, valores in region:
                if re.match(r"^\d+\)", f.texto):
                    acumulado = []
                acumulado.extend(etiqueta)
                if len(valores) >= 2:
                    renglones.append((" ".join(acumulado), pct(valores[0]), pct(valores[1])))
                    acumulado = []
        else:
            # Multiva: etiqueta centrada verticalmente en varias líneas alrededor de
            # los valores: cada línea va al renglón de valores más cercano en Y.
            con_val = [(f, v) for f, _, v in region if len(v) >= 2]
            etiquetas: dict[int, list[tuple[float, str]]] = {i: [] for i in range(len(con_val))}
            for f, etiqueta, _ in region:
                if not etiqueta or not con_val:
                    continue
                i = min(range(len(con_val)), key=lambda k: abs(con_val[k][0].top - f.top))
                etiquetas[i].append((f.top, " ".join(etiqueta)))
            for i, (f, v) in enumerate(con_val):
                txt = " ".join(t for _, t in sorted(etiquetas[i]))
                renglones.append((txt, pct(v[0]), pct(v[1])))
        rv = [r for r in renglones if _es_renglon_rv(r[0])]
        if not renglones:
            continue
        if not rv:
            return 0.0, 0.0, pg.numero, []
        return max(r[1] for r in rv), min(1.0, max(r[2] for r in rv)), pg.numero, rv
    return None, None, None, []


def unir_pct(filas: list[Fila]) -> list[Fila]:
    """Une '0.54' + '%' (palabras separadas) en '0.54%' conservando la X del número."""
    out: list[Fila] = []
    for f in filas:
        ws: list[Palabra] = []
        for p in f.palabras:
            if p.texto == "%" and ws and re.match(r"^-?\d+(\.\d+)?$", ws[-1].texto) and p.x0 - ws[-1].x1 < 25:
                q = ws.pop()
                ws.append(Palabra(q.texto + "%", q.x0, p.x1, q.top, q.bottom))
            else:
                ws.append(p)
        out.append(Fila(f.pagina, f.top, ws))
    return out


def cerca(filas: list[Fila], fila: Fila, x_min: float, x_max: float, dy: float = 8) -> str:
    """Texto en [x_min, x_max) de los renglones a ±dy de `fila` (etiquetas centradas)."""
    return " ".join(
        g.texto_entre(x_min, x_max).strip() for g in filas
        if abs(g.top - fila.top) <= dy and g.texto_entre(x_min, x_max).strip()
    )


def serie_portada(filas: list[Fila]) -> tuple[str, str, str]:
    """Bloque 'Clase y Serie | Posibles adquirientes | Montos mínimos' de la portada
    del DICI. Columnas tomadas de las X del encabezado (no fijas)."""
    hdr = next((f for f in filas if "Clase" in f.texto and "Serie" in f.texto), None)
    fin = next((f for f in filas if f.texto.startswith("Importante")), None)
    pos = next((f for f in filas if "Posibles" in f.texto), None)
    if hdr is None or fin is None or pos is None:
        raise ErrorParseo("DICI: no se encontró el bloque Clase y Serie")
    x_clase = next(p.x0 for p in hdr.palabras if p.texto == "Clase")
    x_pos = next(p.x0 for p in pos.palabras if p.texto == "Posibles")
    x_mon = next(p.x0 for p in hdr.palabras if p.texto == "Montos")
    serie = ""
    adq_l: list[str] = []
    minimo: list[str] = []
    for f in filas:
        if not (hdr.top - 3 < f.top < fin.top):
            continue
        s = f.texto_entre(x_clase - 10, x_pos - 5).strip()
        clase_serie = re.match(r"^[A-Z0-9-]{1,4}\s*/\s*([A-Z0-9-]{1,8})$", s)
        if clase_serie and not serie:  # Nafinsa: "F / PF1" = clase / serie
            serie = clase_serie.group(1)
        if s and not serie and re.match(r"^(?=[A-Z0-9-]*[A-Z])[A-Z0-9][A-Z0-9-]{0,7}$", s.split()[0]):
            serie = s.split()[0]
        a = f.texto_entre(x_pos - 5, x_mon - 4).strip()
        if a and "dquirientes" not in a and "Posibles" not in a:
            adq_l.append(a)
        m = f.texto_entre(x_mon - 4, 2000).strip()
        if m and re.search(r"\d", m) and "inversi" not in m.lower():
            minimo.append(m)
    if not serie:
        raise ErrorParseo("DICI: serie vacía en la portada")
    return serie, " ".join(adq_l), " ".join(minimo)


class InconsistenciaDici(str):
    """Nota de un DICI cuyos componentes no suman su Total mientras las demás
    columnas de la misma tabla sí cuadran: error del documento, no del parser."""


_RE_NUM = re.compile(r"^-?\d+\.\d+%?$")


def _sin_comillas(t: str) -> str:
    return t.strip("'\"‘’“”")


def _columna_comisiones(filas: list[Fila], pct_hdr: Fila, cols_pct: list[float], x_col: float,
                        contexto: str, serie: str, cols_todas: list[float] | None = None
                        ) -> tuple[list[tuple[str, float]], float, int]:
    """Valores de la columna % de una serie. Acepta '1.4987%' y también '0.46' sin signo
    (BlackRock) asignando cada número a la columna (% o $) más cercana del encabezado."""
    cols = cols_todas or cols_pct
    componentes: list[tuple[str, float]] = []
    for f in filas:
        if f.top <= pct_hdr.top:
            continue
        etiqueta = " ".join(p.texto for p in f.palabras if p.x0 < min(cols_pct) - 12 and not es_pct(p.texto)).strip()
        if norm(etiqueta).startswith(("*", "monto por cada", "pol")) or etiqueta.startswith("*"):
            break
        if not etiqueta:
            continue
        propios = [p for p in f.palabras if _RE_NUM.match(p.texto) and p.x0 >= min(cols_pct) - 30
                   and min(cols, key=lambda x: abs(x - (p.x0 + 10))) == x_col]
        if len(propios) > 1:
            raise ErrorParseo(f"{contexto}: más de un % en la columna de la serie {serie} en '{etiqueta}'")
        if norm(etiqueta).startswith("total"):
            if not propios:
                raise ErrorParseo(f"{contexto}: sin Total de comisiones para la serie {serie}")
            t = propios[0].texto
            return componentes, pct(t), (len(t.rstrip("%").split(".")[1]) if "." in t else 0)
        componentes.append((etiqueta, pct(propios[0].texto) if propios else 0.0))
    raise ErrorParseo(f"{contexto}: sin Total de comisiones para la serie {serie}")


def _cuadra(componentes: list[tuple[str, float]], total: float, decimales: int) -> bool:
    tol = max(1, len(componentes)) * 0.5 * 10 ** (-decimales) / 100 + 1e-9
    return abs(sum(v for _, v in componentes) - total) <= tol


def comisiones_del_fondo(filas: list[Fila], serie: str, inicio: str,
                         contexto: str) -> tuple[float | None, float | None, InconsistenciaDici | None]:
    """Tabla de comisiones pagadas por el fondo. Una columna por serie: cada % se
    asigna a la columna "%" más cercana del encabezado y solo cuenta en la de esta
    serie. Validación anti-intercalado: los componentes deben sumar el Total. Si no
    suman pero TODAS las demás columnas de la tabla sí, el error es del documento:
    se conserva el Total publicado y se devuelve la inconsistencia para reportarla."""
    filas = unir_pct(filas)
    ini = next((j for j, f in enumerate(filas) if inicio in norm(f.texto)), None)
    if ini is None:
        return None, None, None
    filas = filas[ini:]
    hdr = next((f for f in filas if serie in [_sin_comillas(p.texto) for p in f.palabras]), None)
    x_serie = None
    if hdr is not None:
        x_serie = next(p.x0 for p in hdr.palabras if _sin_comillas(p.texto) == serie)
    else:
        # Nafinsa: sin nombre de serie; dos columnas, la de esta serie y la "Serie más
        # representativa". Esta serie es la columna % que NO está bajo ese encabezado.
        hdr = next((f for f in filas if "serie mas representativa" in norm(f.texto)), None)
        if hdr is None:
            raise ErrorParseo(f"{contexto}: sin encabezado de serie {serie} en comisiones")
    pct_hdr = next((f for f in filas if f.top > hdr.top and "%" in [p.texto for p in f.palabras]), None)
    if pct_hdr is None:
        raise ErrorParseo(f"{contexto}: sin encabezado de columnas % en comisiones")
    cols_pct = [p.x0 for p in pct_hdr.palabras if p.texto == "%"]
    if x_serie is None:
        if len(cols_pct) != 2:
            raise ErrorParseo(f"{contexto}: sin encabezado de serie {serie} en comisiones")
        x_rep = next(p.x0 for p in hdr.palabras if norm(p.texto) == "serie")
        x_serie = max(cols_pct, key=lambda x: abs(x - x_rep))
    cols_todas = [p.x0 for p in pct_hdr.palabras if p.texto in ("%", "$")]
    x_col = min(cols_pct, key=lambda x: abs(x - x_serie))
    componentes, total, decimales = _columna_comisiones(filas, pct_hdr, cols_pct, x_col, contexto, serie, cols_todas)
    inconsistencia = None
    if not _cuadra(componentes, total, decimales):
        suma = sum(v for _, v in componentes)
        otras = [c for c in cols_pct if c != x_col]
        if otras and all(_cuadra(*_columna_comisiones(filas, pct_hdr, cols_pct, c, contexto, serie, cols_todas)) for c in otras):
            inconsistencia = InconsistenciaDici(
                f"Comisiones serie {serie}: el DICI publica un total de {total:.4%} pero sus componentes "
                f"suman {suma:.4%} ({contexto}); las demás series de la tabla sí cuadran"
            )
        else:
            raise ErrorParseo(
                f"{contexto} serie {serie}: componentes suman {suma:.4%} y el Total dice {total:.4%}: "
                "posible intercalado de columnas"
            )
    adm = next((v for e, v in componentes if norm(e) == "administracion de activos"), None)
    return adm, total, inconsistencia


def entes_prestadores(lineas: list[str]) -> list[str]:
    """Une renglones en entes: un ente termina en 'C.V.', 'Inversión.' o 'N/A'."""
    entes: list[str] = []
    actual: list[str] = []
    for l in lineas:
        actual.append(l)
        fin = norm(l)
        if fin.endswith(("c.v.", "c.v", "inversion.", "inversion", "n/a", "s.a.", "s.c.", "s.o.f.i.", "s.o.f.i")):
            entes.append(" ".join(actual))
            actual = []
    if actual:
        entes.append(" ".join(actual))
    return entes


def regimen_prospecto(ruta: Path) -> tuple[float | None, float | None, int | None, str]:
    """Régimen de RV del prospecto específico: tabla de parámetros; si no hay
    tabla, prosa del objetivo/política (primeras 15 páginas)."""
    from radar.core.pdffilas import iterar_paginas

    mn, mx, pagina, _ = regimen_desde_tabla(iterar_paginas(ruta))
    if pagina is not None:
        return mn, mx, pagina, "tabla de parámetros"
    for pg in iterar_paginas(ruta):
        if pg.numero > 15:
            break
        mn, mx = regimen_desde_texto(" ".join(f.texto for f in pg.filas()))
        if mx is not None:
            return mn, mx, pg.numero, "texto del régimen"
    return None, None, None, ""


_SUFIJO = (
    r"(?<![A-Za-zÁÉÍÓÚáéíóúñÑ])S\.\s?A\.?(?:\s*de\s*C\.\s?V\.?)?"
    r"(?:,?\s*(?:S\.O\.F\.I\.?|(?:Sociedad )?Operadora[^,;]*?de Fondos de Inversi[oó]n|"
    r"Distribuidora de Acciones de Fondos de Inversi[oó]n|Instituci[oó]n de Banca M[uú]ltiple[^,;]*?|"
    r"Grupo Financiero\s+[A-ZÁÉÍÓÚ][\w]+|Casa de Bolsa(?=\s*(?:[,;.]|$))|I\.C\.V\.?|Instituci[oó]n Calificadora de Valores))*\.?"
)
_RE_ENTE = re.compile(r"\s*(N/A|N\.A\.|No Aplica|.+?" + _SUFIJO + r")(?=[,;]?\s+|[,;]?\s*$)", re.I)


def entes_por_forma_juridica(texto: str) -> list[str]:
    """Separa una lista corrida de entes ('X, S.A. de C.V., S.O.F.I., Y, S.A. de C.V.; …')
    por su forma jurídica. 'N/A' cuenta como ente (calificadora sin calificación)."""
    texto = re.sub(r"\s+", " ", texto).strip()
    out: list[str] = []
    pos = 0
    while pos < len(texto):
        m = _RE_ENTE.match(texto, pos)
        if not m:
            break
        out.append(m.group(1).strip(" ,;"))
        pos = m.end()
        while pos < len(texto) and texto[pos] in ",; ":
            pos += 1
    if pos < len(texto):
        return []  # no se pudo separar todo: que decida el método por renglones
    return out


def distribuidoras_unicas(dicis) -> list[str]:
    """Distribuidoras de todos los DICI sin duplicados por variantes de puntuación
    ('Más Fondos S.A. de C.V. S.O.F.I.' = 'Más Fondos, S.A. de C.V., S.O.F.I.')."""
    vistos: dict[str, str] = {}
    for x in dicis:
        for d in x.distribuidoras:
            d = re.sub(r"^y\s+", "", d.strip())
            k = re.sub(r"[^a-z0-9]", "", norm(d))
            if k and (k not in vistos or len(d) > len(vistos[k])):
                vistos[k] = d
    return sorted(vistos.values(), key=norm)
