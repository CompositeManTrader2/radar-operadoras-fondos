"""Reconstrucción de filas de tabla a partir de coordenadas.

Las carteras y los DICI son tablas con layout de dos dimensiones. Extraer en orden
de lectura plano intercala columnas (en los DICI hay una columna por serie). Aquí
cada palabra conserva su caja; las filas se arman agrupando por coordenada Y con
tolerancia y ordenando por X. Nunca usar pypdf: pierde la estructura de tabla.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


@dataclass(frozen=True)
class Palabra:
    texto: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass
class Fila:
    pagina: int  # 1-based
    top: float
    palabras: list[Palabra] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return " ".join(p.texto for p in self.palabras)

    def entre(self, x_min: float, x_max: float) -> list[Palabra]:
        return [p for p in self.palabras if x_min <= p.x0 < x_max]

    def texto_entre(self, x_min: float, x_max: float) -> str:
        return " ".join(p.texto for p in self.entre(x_min, x_max))


def agrupar_filas(palabras: list[Palabra], pagina: int, y_tol: float = 2.5) -> list[Fila]:
    """Agrupa por Y contra el ancla de la fila (no en cadena, para no fusionar
    filas contiguas) y ordena cada fila por X."""
    filas: list[Fila] = []
    for p in sorted(palabras, key=lambda w: (w.top, w.x0)):
        if filas and p.top - filas[-1].top <= y_tol:
            filas[-1].palabras.append(p)
        else:
            filas.append(Fila(pagina=pagina, top=p.top, palabras=[p]))
    for f in filas:
        f.palabras.sort(key=lambda w: w.x0)
    return filas


def palabras_de_pagina(page, x_tolerance: float = 1.5) -> list[Palabra]:
    return [
        Palabra(w["text"], float(w["x0"]), float(w["x1"]), float(w["top"]), float(w["bottom"]))
        for w in page.extract_words(x_tolerance=x_tolerance, keep_blank_chars=False, use_text_flow=False)
    ]


@dataclass
class PaginaPdf:
    numero: int
    ancho: float
    alto: float
    palabras: list[Palabra]

    def filas(self, y_tol: float = 2.5, x_min: float = -1, x_max: float = 1e9) -> list[Fila]:
        sel = [p for p in self.palabras if x_min <= p.x0 < x_max]
        return agrupar_filas(sel, self.numero, y_tol)


def _dir_cache() -> Path | None:
    d = os.environ.get("RADAR_CACHE_PDF")
    if d is None:
        from radar.config import dir_datos
        d = str(dir_datos() / "cache" / "pdf")
    if d == "":
        return None
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _clave_cache(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _cargar_cache(base: Path | None, n: int) -> PaginaPdf | None:
    if base is None:
        return None
    f = base / f"{n}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    return PaginaPdf(n, d["w"], d["h"], [Palabra(*x) for x in d["p"]])


def _guardar_cache(base: Path | None, pg: PaginaPdf) -> None:
    if base is None:
        return
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{pg.numero}.json").write_text(
        json.dumps({"w": pg.ancho, "h": pg.alto, "p": [[p.texto, p.x0, p.x1, p.top, p.bottom] for p in pg.palabras]},
                   ensure_ascii=False),
        encoding="utf-8",
    )


def iterar_paginas(ruta: Path):
    """Generador perezoso: permite detenerse en cuanto se encuentra lo buscado
    (los prospectos pasan de 100 páginas). Cachea las palabras por página,
    indexadas por sha256 del PDF (la extracción es determinista)."""
    raiz = _dir_cache()
    base = raiz / _clave_cache(ruta) if raiz else None
    total = None
    if base is not None and (base / "n.txt").exists():
        total = int((base / "n.txt").read_text())
        hechas = []
        for n in range(1, total + 1):
            pg = _cargar_cache(base, n)
            if pg is None:
                break
            hechas.append(pg)
        else:
            yield from hechas
            return
    with pdfplumber.open(ruta) as pdf:
        if base is not None:
            base.mkdir(parents=True, exist_ok=True)
            (base / "n.txt").write_text(str(len(pdf.pages)))
        for i, pg in enumerate(pdf.pages):
            c = _cargar_cache(base, i + 1)
            if c is None:
                c = PaginaPdf(i + 1, float(pg.width), float(pg.height), palabras_de_pagina(pg))
                _guardar_cache(base, c)
            yield c
            pg.flush_cache()


def leer_pdf(ruta: Path) -> list[PaginaPdf]:
    return list(iterar_paginas(ruta))


def numeros_por_caracter(ruta: Path, pagina: int, top: float, bottom: float, x_min: float) -> list[str]:
    """Rescate para renglones donde el PDF encima texto sobre cifras (la etiqueta
    invade las columnas numéricas y pdfplumber intercala los caracteres). Toma solo
    dígitos, comas y puntos a la derecha de x_min y los agrupa por cercanía en X."""
    with pdfplumber.open(ruta) as pdf:
        chars = [c for c in pdf.pages[pagina - 1].chars
                 if top - 1.5 <= float(c["top"]) <= bottom + 1.5 and float(c["x0"]) >= x_min
                 and c["text"] in "0123456789,."]
    chars.sort(key=lambda c: float(c["x0"]))
    grupos: list[list[dict]] = []
    for c in chars:
        if grupos and float(c["x0"]) - float(grupos[-1][-1]["x1"]) <= 2.5:
            grupos[-1].append(c)
        else:
            grupos.append([c])
    return ["".join(c["text"] for c in g) for g in grupos]
