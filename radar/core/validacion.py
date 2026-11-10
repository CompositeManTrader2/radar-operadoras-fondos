"""Criterios de aceptación que hacen fallar el pipeline."""
from __future__ import annotations

from radar.core.modelo import Cartera


class ErrorCuadre(ValueError):
    pass


def validar_cuadre(c: Cartera, tolerancia: float) -> None:
    """La suma de posiciones parseadas debe cuadrar contra el total publicado.
    Detecta posiciones omitidas por el parser."""
    suma = c.suma_posiciones
    if c.total_cartera <= 0:
        raise ErrorCuadre(f"{c.operadora}/{c.fondo_clave} {c.fecha_corte}: total de cartera no positivo")
    dif = abs(suma - c.total_cartera) / c.total_cartera
    if dif > tolerancia:
        raise ErrorCuadre(
            f"NO CUADRA {c.operadora}/{c.fondo_clave} corte {c.fecha_corte} ({c.procedencia.archivo}): "
            f"suma de {len(c.posiciones)} posiciones = {suma:,.2f} vs total publicado {c.total_cartera:,.2f} "
            f"(diferencia {dif:.4%} > {tolerancia:.1%})"
        )
