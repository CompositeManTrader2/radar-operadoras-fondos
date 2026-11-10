"""Gráficas en SVG generadas por el propio código (sin librerías externas).
Todas las coordenadas se redondean para que la salida sea determinista."""
from __future__ import annotations

import math

from radar.render.formato import e


def _r(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def dona(segmentos: list[tuple[str, float, str]], titulo: str, tam: int = 180) -> str:
    """segmentos: (etiqueta, valor, variable_css_color). % sobre el arco."""
    total = sum(v for _, v, _ in segmentos)
    c = tam / 2
    r = tam / 2 - 18
    grosor = 26
    circ = 2 * math.pi * r
    partes = [
        f'<svg class="dona" viewBox="0 0 {tam} {tam}" width="{tam}" height="{tam}" role="img" aria-label="{e(titulo)}">',
        f'<circle cx="{_r(c)}" cy="{_r(c)}" r="{_r(r)}" fill="none" stroke="var(--linea)" stroke-width="{grosor}"/>',
    ]
    acumulado = 0.0
    for etiqueta, v, color in segmentos:
        if total <= 0 or v <= 0:
            continue
        frac = v / total
        largo = frac * circ
        partes.append(
            f'<circle cx="{_r(c)}" cy="{_r(c)}" r="{_r(r)}" fill="none" stroke="var({color})" '
            f'stroke-width="{grosor}" stroke-dasharray="{_r(largo)} {_r(circ - largo)}" '
            f'stroke-dashoffset="{_r(-acumulado * circ + circ / 4)}"><title>{e(etiqueta)}</title></circle>'
        )
        if frac >= 0.04:
            ang = 2 * math.pi * (acumulado + frac / 2) - math.pi / 2
            x, y = c + r * math.cos(ang), c + r * math.sin(ang)
            partes.append(
                f'<text x="{_r(x)}" y="{_r(y)}" class="arco" text-anchor="middle" dominant-baseline="central">'
                f'{frac * 100:.0f}%</text>'
            )
        acumulado += frac
    partes.append("</svg>")
    return "".join(partes)


def barra_apilada(fracs: list[tuple[float, str]], ancho: int = 120, alto: int = 10) -> str:
    x = 0.0
    out = [f'<svg class="mezcla" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" aria-hidden="true">',
           f'<rect width="{ancho}" height="{alto}" fill="var(--linea)"/>']
    for f, color in fracs:
        w = max(0.0, f) * ancho
        if w > 0:
            out.append(f'<rect x="{_r(x)}" width="{_r(w)}" height="{alto}" fill="var({color})"/>')
        x += w
    out.append("</svg>")
    return "".join(out)


def barra_peso(frac: float, ancho: int = 110, alto: int = 8, color: str = "--primario") -> str:
    w = max(0.0, min(1.0, frac)) * ancho
    return (f'<svg class="peso" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" aria-hidden="true">'
            f'<rect width="{_r(w)}" height="{alto}" fill="var({color})"/></svg>')


def dispersion(puntos: list[dict], series: list[tuple[str, str]], eje_x: str, eje_y: str,
               ancho: int = 760, alto: int = 420) -> str:
    """puntos: {x: pesos (>0), y: fracción 0-1, tam: bolsa, serie, etiqueta}.
    Eje X logarítmico en millones de pesos."""
    ml, mr, mt, mb = 64, 20, 16, 52
    pw, ph = ancho - ml - mr, alto - mt - mb
    xs = [p["x"] / 1e6 for p in puntos if p["x"] > 0]
    lo = 10 ** math.floor(math.log10(min(xs))) if xs else 1.0
    hi = 10 ** math.ceil(math.log10(max(xs))) if xs else 10.0
    if hi <= lo:
        hi = lo * 10
    lx = lambda v: ml + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * pw
    ly = lambda f: mt + (1 - f) * ph
    tam_max = max([p["tam"] for p in puntos] + [1.0])
    out = [f'<svg class="dispersion" viewBox="0 0 {ancho} {alto}" width="100%" role="img" aria-label="{e(eje_y)}">']
    k = math.log10(lo)
    while k <= math.log10(hi) + 1e-9:
        v = 10 ** k
        x = lx(v)
        out.append(f'<line x1="{_r(x)}" y1="{mt}" x2="{_r(x)}" y2="{mt + ph}" class="rejilla"/>')
        out.append(f'<text x="{_r(x)}" y="{mt + ph + 16}" class="tick" text-anchor="middle">{v:,.0f}</text>' if v >= 1 else f'<text x="{_r(x)}" y="{mt + ph + 16}" class="tick" text-anchor="middle">{v:g}</text>')
        k += 1
    for f in (0, 0.25, 0.5, 0.75, 1.0):
        y = ly(f)
        out.append(f'<line x1="{ml}" y1="{_r(y)}" x2="{ml + pw}" y2="{_r(y)}" class="rejilla"/>')
        out.append(f'<text x="{ml - 8}" y="{_r(y)}" class="tick" text-anchor="end" dominant-baseline="central">{f * 100:.0f}%</text>')
    out.append(f'<text x="{ml + pw / 2}" y="{alto - 8}" class="eje" text-anchor="middle">{e(eje_x)}</text>')
    out.append(f'<text transform="translate(14 {mt + ph / 2}) rotate(-90)" class="eje" text-anchor="middle">{e(eje_y)}</text>')
    color = dict(series)
    for p in sorted(puntos, key=lambda q: (-q["tam"], q["etiqueta"])):
        if p["x"] <= 0:
            continue
        r = 4 + 22 * math.sqrt(p["tam"] / tam_max)
        out.append(
            f'<circle cx="{_r(lx(p["x"] / 1e6))}" cy="{_r(ly(p["y"]))}" r="{_r(r)}" fill="var({color[p["serie"]]})" '
            f'fill-opacity="0.55" stroke="var({color[p["serie"]]})"><title>{e(p["etiqueta"])}</title></circle>'
        )
    out.append("</svg>")
    return "".join(out)
