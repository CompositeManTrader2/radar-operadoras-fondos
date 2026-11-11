"""HTML autocontenido (sin librerías externas). Determinista: mismo store y mismo
corte => mismo HTML byte a byte (sin marcas de tiempo, todo ordenado)."""
from __future__ import annotations

from collections import defaultdict

from radar import __version__
from radar.config import Parametros
from radar.core.clasificacion import etfs_confianza_media, nombre_emisora_sic, version_diccionario_etfs
from radar.core.metricas import MetricasFondo, MetricasOperadora
from radar.core.modelo import CLASES_RV, POR_CONFIRMAR, RF, Categoria
from radar.render import plantillas as T
from radar.render.formato import banda, e, mdp, pct, pb, veces
from radar.render.svg import barra_apilada, barra_peso, dispersion, dona

CSS = """
:root{--primario:#522D6D;--acento:#00857D;--secundario:#919AA2;--texto:#3C444D;--fondo:#F7F5F8;
--tarjeta:#FFFFFF;--linea:#E2E8F0;--suave:#6B737C;--encabezado:#5B296E;--encabezado-texto:#FFFFFF;
--serie3:#FFB400;--serie4:#0FCB97;--serie5:#2F6DB5;--alerta:#A3461F}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--primario:#9A72B8;--acento:#2BB3A9;
--secundario:#8A939C;--texto:#E3E6EA;--fondo:#15181C;--tarjeta:#1E2228;--linea:#30363E;--suave:#A7AFB8;
--encabezado:#2A1838;--encabezado-texto:#F1ECF5;--alerta:#E08A5F}}
:root[data-theme="dark"]{--primario:#9A72B8;--acento:#2BB3A9;--secundario:#8A939C;--texto:#E3E6EA;
--fondo:#15181C;--tarjeta:#1E2228;--linea:#30363E;--suave:#A7AFB8;--encabezado:#2A1838;
--encabezado-texto:#F1ECF5;--alerta:#E08A5F}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--texto);font-family:'Open Sans',system-ui,-apple-system,'Segoe UI',sans-serif;font-size:14px;line-height:1.45}
h1,h2,h3,.marca-punto{font-family:'Ubuntu','Open Sans','Segoe UI',sans-serif}
.mono,td.num,.tick,.arco,.kpi .valor{font-family:'IBM Plex Mono',ui-monospace,'Cascadia Mono',Consolas,monospace;font-variant-numeric:tabular-nums}
.marca-punto{display:flex;align-items:center;gap:14px;margin:0 0 14px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,.25)}
.marca-punto .logo{display:flex;flex-direction:column;line-height:1}
.marca-punto .logo b{font-size:28px;font-weight:500;letter-spacing:-.5px}
.marca-punto .logo span{font-size:10.5px;letter-spacing:.3px;margin-top:2px}
.marca-punto .area{border-left:1px solid rgba(255,255,255,.55);padding-left:14px;font-size:12.5px;opacity:.92}
.num{text-align:right;white-space:nowrap}
header.franja{background:var(--encabezado);color:var(--encabezado-texto);padding:20px 24px}
header.franja h1{margin:0 0 6px;font-size:22px;font-weight:700;letter-spacing:.2px}
header.franja .meta{display:flex;flex-wrap:wrap;gap:6px 22px;font-size:12px;opacity:.92}
header.franja .meta b{font-weight:600}
main{max-width:1180px;margin:0 auto;padding:20px 16px 40px}
section{margin:0 0 22px}
h2{font-size:15px;margin:0 0 10px;font-weight:700;color:var(--primario)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.kpi{background:var(--tarjeta);border:1px solid var(--linea);border-radius:8px;padding:12px 14px}
.kpi .etiqueta{font-size:12px;color:var(--suave)}
.kpi .valor{font-size:22px;font-weight:600;margin:4px 0 2px}
.kpi .sub{font-size:11px;color:var(--suave)}
.donas{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.panel{background:var(--tarjeta);border:1px solid var(--linea);border-radius:8px;padding:14px 16px}
.dona-caja{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.arco{font-size:11px;fill:#FFFFFF;font-weight:600}
.leyenda{list-style:none;margin:0;padding:0;font-size:13px}
.leyenda li{display:flex;align-items:center;gap:8px;margin:4px 0}
.leyenda .cifra{margin-left:auto;padding-left:14px}
.leyenda.horizontal{display:flex;flex-wrap:wrap;gap:4px 18px;margin:0 0 8px}
.leyenda.horizontal li{margin:0}
.leyenda.horizontal .cifra{display:none}
.punto{width:10px;height:10px;border-radius:2px;display:inline-block;flex:none}
.tabla-scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:6px 8px;border-bottom:1px solid var(--linea);text-align:left;vertical-align:middle}
th{font-size:11.5px;color:var(--suave);font-weight:600}
th.num{text-align:right;white-space:normal}
tr.total td{font-weight:700;border-top:2px solid var(--texto)}
.tops{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
footer.pie{font-size:12px;color:var(--suave)}
footer.pie h3{font-size:12.5px;color:var(--texto);margin:14px 0 4px}
footer.pie p,footer.pie li{margin:3px 0}
footer.pie ul{margin:0;padding-left:18px}
.marca{color:var(--alerta);font-weight:700}
.rejilla{stroke:var(--linea);stroke-width:1}
.tick{font-size:10.5px;fill:var(--suave)}
.eje{font-size:11.5px;fill:var(--texto)}
.veto{color:var(--alerta);font-weight:700}
table.compacta{font-size:11.5px}
table.compacta th{font-size:10.5px;padding:5px 5px}
table.compacta td{padding:5px 5px}
td.mono,table.compacta td{white-space:nowrap}
table.compacta td:first-child{white-space:normal}
"""

COLOR_CLASE = {"rv": "--primario", "rf": "--acento", "efe": "--secundario"}
COLORES_SERIES = ("--primario", "--acento", "--serie3", "--serie4", "--serie5", "--secundario")


def _marca() -> str:
    return (f'<div class="marca-punto"><div class="logo"><b>{e(T.MARCA)}</b><span>{e(T.MARCA_SUB)}</span></div>'
            f'<div class="area">{e(T.MARCA_AREA)}</div></div>')


def _doc(titulo: str, cuerpo: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"es\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{e(T.MARCA_NOMBRE)} · {e(titulo)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n{cuerpo}\n</body>\n</html>\n"
    )


def _kpi(etiqueta: str, valor: str, sub: str) -> str:
    return (f'<div class="kpi"><div class="etiqueta">{e(etiqueta)}</div>'
            f'<div class="valor">{e(valor)}</div><div class="sub">{e(sub)}</div></div>')


def _leyenda(items: list[tuple[str, str, str]], horizontal: bool = False) -> str:
    clase = "leyenda horizontal" if horizontal else "leyenda"
    return f'<ul class="{clase}">' + "".join(
        f'<li><span class="punto" style="background:var({c})"></span>{e(t)}<span class="cifra num">{e(v)}</span></li>'
        for t, v, c in items
    ) + "</ul>"


def _rot_ponderada(fondos: list[MetricasFondo]) -> tuple[float, float]:
    con = [f for f in fondos if f.exposicion_rv > 0]
    tot = sum(f.exposicion_rv for f in con)
    if not tot:
        return 0.0, 0.0
    return (sum(f.rotacion.minimo * f.exposicion_rv for f in con) / tot,
            sum(f.rotacion.maximo * f.exposicion_rv for f in con) / tot)


def _top(fondos: list[MetricasFondo], clases: tuple[str, ...]) -> list[tuple[str, float, list[str]]]:
    agg: dict[str, float] = defaultdict(float)
    etiqueta: dict[str, str] = {}
    fuentes: dict[str, set[str]] = defaultdict(set)
    for f in fondos:
        for p in f.cartera.posiciones:
            if p.clase not in clases or p.es_agregado or p.categoria is Categoria.FONDO:
                continue
            k = p.emisora_canonica
            agg[k] += p.valor_razonable
            if p.categoria is Categoria.ACCION_SIC:
                nombre = nombre_emisora_sic(k)
                etiqueta[k] = f"{k} · {nombre}" if nombre != POR_CONFIRMAR else f"{k} {POR_CONFIRMAR}"
            else:
                etiqueta.setdefault(k, k)
            fuentes[k].add(f"{f.clave} {p.procedencia.cita()}")
    filas = sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    return [(etiqueta[k], v, sorted(fuentes[k])) for k, v in filas]


def _tabla_top(titulo: str, filas: list[tuple[str, float, list[str]]], color: str) -> str:
    h = [f'<div class="panel"><h2>{e(titulo)}</h2>']
    if not filas:
        return "".join(h) + f"<p>{e(T.SIN_POSICIONES)}</p></div>"
    mx = filas[0][1]
    cols = T.COLUMNAS_TOP
    h.append('<div class="tabla-scroll"><table><thead><tr>'
             f'<th class="num">{e(cols[0])}</th><th>{e(cols[1])}</th><th class="num">{e(cols[2])}</th>'
             f'<th>{e(cols[3])}</th></tr></thead><tbody>')
    for i, (et, v, fuentes) in enumerate(filas, 1):
        h.append(f'<tr title="{e("; ".join(fuentes))}"><td class="num">{i}</td><td>{e(et)}</td>'
                 f'<td class="num">{mdp(v)}</td><td>{barra_peso(v / mx if mx else 0, color=color)}</td></tr>')
    h.append("</tbody></table></div></div>")
    return "".join(h)


def render_operadora(m: MetricasOperadora, prm: Parametros) -> str:
    sup = prm.supuestos(m.clave, m.perfil.casa_de_bolsa_hermana if m.perfil else None)
    alta = pct(sup.probabilidad_de_alta, 0) if sup else "—"
    hermana = m.perfil.casa_de_bolsa_hermana if m.perfil else None
    txt_hermana = T.SI if hermana else (T.NO if hermana is False else POR_CONFIRMAR)
    evid = m.perfil.evidencia_casa_de_bolsa if m.perfil else ""
    out: list[str] = []

    # 1. Franja de encabezado
    out.append(
        '<header class="franja">' + _marca() +
        f'<h1>{e(T.TITULO_OPERADORA.format(operadora=m.nombre))}</h1><div class="meta">'
        f'<span><b>{e(T.ETIQUETA_CORTE)}:</b> <span class="mono">{m.corte.isoformat()}</span></span>'
        f'<span><b>{e(T.ETIQUETA_PARAMETROS)}:</b> {e(T.PARAMETROS.format(local=pb(prm.comision_local_pb), sic=pb(prm.comision_sic_pb), captura=pct(prm.captura_objetivo, 0), alta=alta))}</span>'
        f'<span title="{e(evid)}"><b>{e(T.ETIQUETA_CASA_BOLSA)}:</b> {e(txt_hermana)}</span>'
        "</div></header><main>"
    )

    # 2. Seis indicadores
    an = m.activo_neto
    vals = {
        "fondos": (str(len(m.fondos)), T.SUB_FONDOS.format(n=len(m.excluidos_fdf))),
        "activos": (mdp(an), T.SUB_MDP),
        "fondos_rv": (str(len(m.fondos_con_rv)), T.SUB_FONDOS_RV.format(n=len(m.fondos))),
        "monto_rv": (mdp(m.exposicion_rv), T.SUB_PCT_ACTIVOS.format(pct=pct(m.exposicion_rv / an if an else 0))),
        "monto_rf": (mdp(m.monto_rf), T.SUB_PCT_ACTIVOS.format(pct=pct(m.monto_rf / an if an else 0))),
        "monto_efe": (mdp(m.monto_efe), T.SUB_PCT_ACTIVOS.format(pct=pct(m.monto_efe / an if an else 0))),
    }
    out.append('<section class="kpis">' + "".join(_kpi(et, *vals[k]) for k, et in T.INDICADORES) + "</section>")

    # 3. Dos donas
    n_tipo = {t: sum(1 for f in m.fondos if f.tipo_fondo == t) for t in ("RV", "RF")}
    a_tipo = {t: sum(f.activo_neto for f in m.fondos if f.tipo_fondo == t) for t in ("RV", "RF")}
    col = {"RV": "--primario", "RF": "--acento"}
    seg1 = [(T.TIPO_FONDO[t], n_tipo[t], col[t]) for t in ("RV", "RF")]
    seg2 = [(T.TIPO_FONDO[t], a_tipo[t], col[t]) for t in ("RV", "RF")]
    out.append(
        '<section class="donas">'
        f'<div class="panel"><h2>{e(T.TITULO_DONA_FONDOS)}</h2><div class="dona-caja">{dona(seg1, T.TITULO_DONA_FONDOS)}'
        + _leyenda([(T.TIPO_FONDO[t], T.LEYENDA_FONDOS.format(n=n_tipo[t]), col[t]) for t in ("RV", "RF")])
        + "</div></div>"
        f'<div class="panel"><h2>{e(T.TITULO_DONA_ACTIVOS)}</h2><div class="dona-caja">{dona(seg2, T.TITULO_DONA_ACTIVOS)}'
        + _leyenda([(T.TIPO_FONDO[t], T.LEYENDA_ACTIVOS.format(mdp=mdp(a_tipo[t])), col[t]) for t in ("RV", "RF")])
        + "</div></div></section>"
    )

    # 4. Tabla de fondos
    c = T.COLUMNAS_FONDOS
    num = {4, 6, 7, 8, 9, 10}
    th = "".join(f'<th class="num">{e(x)}</th>' if i in num else f"<th>{e(x)}</th>" for i, x in enumerate(c))
    filas = []
    for f in sorted(m.fondos, key=lambda x: (-x.activo_neto, x.clave)):
        marca_e = f" {T.MARCA_ESTIMADO}" if f.activo_neto_estimado else ""
        marca_e += f" {T.MARCA_HERMANOS}" if f.en_hermanos else ""
        marca_d = f' <span class="marca">{T.MARCA_DISCREPANCIA}</span>' if f.discrepancias else ""
        mezcla = barra_apilada([(f.pct_rv, COLOR_CLASE["rv"]), (f.pct_rf, COLOR_CLASE["rf"]), (f.pct_efe, COLOR_CLASE["efe"])])
        filas.append(
            f'<tr title="{e(f.cartera.procedencia.cita())}"><td class="mono">{e(f.clave)}</td><td>{e(f.nombre_corto or "—")}</td>'
            f"<td>{e(T.TIPO_FONDO.get(f.tipo_fondo, f.tipo_fondo))}</td><td>{e(f.categoria_regulatoria)}</td>"
            f'<td class="num">{mdp(f.activo_neto_propio)}{marca_e}{marca_d}</td><td>{mezcla}</td>'
            f'<td class="num">{pct(f.pct_rv)}</td><td class="num">{pct(f.pct_rf)}</td><td class="num">{pct(f.pct_efe)}</td>'
            f'<td class="num">{mdp(f.exposicion_rv)}</td><td class="num">{mdp(f.monto_rf)}</td></tr>'
        )
    filas.append(
        f'<tr class="total"><td>{e(T.FILA_TOTAL)}</td><td></td><td></td><td></td><td class="num">{mdp(an)}</td>'
        + "<td>" + barra_apilada([(m.exposicion_rv / an if an else 0, COLOR_CLASE["rv"]),
                                  (m.monto_rf / an if an else 0, COLOR_CLASE["rf"]),
                                  (m.monto_efe / an if an else 0, COLOR_CLASE["efe"])]) + "</td>"
        f'<td class="num">{pct(m.exposicion_rv / an if an else 0)}</td><td class="num">{pct(m.monto_rf / an if an else 0)}</td>'
        f'<td class="num">{pct(m.monto_efe / an if an else 0)}</td><td class="num">{mdp(m.exposicion_rv)}</td>'
        f'<td class="num">{mdp(m.monto_rf)}</td></tr>'
    )
    out.append(
        f'<section class="panel"><h2>{e(T.TITULO_TABLA_FONDOS)}</h2>'
        + _leyenda([(t, "", COLOR_CLASE[k]) for k, t in T.LEYENDA_MEZCLA], horizontal=True)
        + f'<div class="tabla-scroll"><table><thead><tr>{th}</tr></thead><tbody>{"".join(filas)}</tbody></table></div></section>'
    )

    # 5. Top 20 RV y RF lado a lado
    out.append('<section class="tops">'
               + _tabla_top(T.TITULO_TOP_RV, _top(m.fondos, CLASES_RV), "--primario")
               + _tabla_top(T.TITULO_TOP_RF, _top(m.fondos, (RF,)), "--acento")
               + "</section>")

    # 6. Pie
    out.append(_pie(m, prm))
    out.append("</main>")
    return _doc(T.TITULO_OPERADORA.format(operadora=m.nombre) + f" · {m.corte.isoformat()}", "".join(out))


def _historia(f: MetricasFondo):
    return getattr(f, "historia", [])


def _pie(m: MetricasOperadora, prm: Parametros) -> str:
    p: list[str] = ['<footer class="pie panel">', f"<h3>{e(T.TITULO_METODOLOGIA)}</h3>"]
    for par in T.METODOLOGIA:
        p.append("<p>" + e(par.format(version_etfs=version_diccionario_etfs(), tol=pct(prm.tolerancia_cuadre),
                                      n_cortes=prm.cortes_para_cifra, max_meses=f"{prm.max_meses_par:g}",
                                      umbral=pct(prm.umbral_discrepancia, 0))) + "</p>")

    # Rotación y bolsa
    rlo, rhi = _rot_ponderada(m.fondos)
    ilo, ihi = m.importe_banda()
    blo, bhi = m.bolsa_banda(prm)
    con_rv = m.fondos_con_rv
    medidos = [f for f in con_rv if f.rotacion.medida]
    p.append(f"<h3>{e(T.TITULO_ROTACION)}</h3><p>" + e(T.ROTACION_RESUMEN.format(
        rot=banda(rlo, rhi), importe=banda(ilo, ihi, mdp), bolsa=banda(blo, bhi, mdp), headroom=mdp(m.headroom))) + "</p>")
    if medidos:
        cortes = sorted({(r.corte_a, r.corte_b) for f in medidos for r in f.rotacion.pares})
        txt = ", ".join(T.PAR_DE_CORTES.format(a=a.isoformat(), b=b.isoformat()) for a, b in cortes)
        p.append("<p>" + e(T.ROTACION_MEDIDA.format(n=len(medidos), total=len(con_rv), cortes=txt)) + "</p>")
    if len(medidos) < len(con_rv):
        p.append("<p>" + e(T.ROTACION_SIN_MEDIR.format(banda=banda(prm.sin_medicion_min, prm.sin_medicion_max))) + "</p>")

    # Exclusiones
    p.append(f"<h3>{e(T.TITULO_EXCLUSIONES)}</h3><p>{e(T.EXCLUSION_FDF)}</p><ul>")
    for f in sorted(m.excluidos_fdf, key=lambda x: x.clave):
        directos = [x for x in f.cartera.posiciones if x.categoria is not Categoria.FONDO]
        d = ", ".join(T.ITEM_DIRECTO.format(emisora=x.emisora_raw, monto=mdp(x.valor_razonable), clase=x.clase) for x in directos) or T.SIN_DIRECTO
        en_f = f.mezcla.en_fondos / f.total_cartera if f.total_cartera else 0
        p.append("<li>" + e(T.EXCLUSION_FDF_FONDO.format(clave=f.clave, pct_fondos=pct(en_f), directo=d)) + "</li>")
    p.append("</ul>")
    if m.no_disponibles:
        p.append(f"<p>{e(T.EXCLUSION_NO_DISPONIBLE)}</p><ul>"
                 + "".join(f"<li>{e(T.ITEM_FUERA.format(clave=k, motivo=v))}</li>" for k, v in m.no_disponibles) + "</ul>")

    # Supuestos (e)
    sup = prm.supuestos(m.clave, m.perfil.casa_de_bolsa_hermana if m.perfil else None)
    s: list[str] = []
    est = [f for f in m.fondos if f.activo_neto_estimado]
    if est:
        s.append(T.SUPUESTO_ACTIVO_NETO.format(n=len(est)))
        if m.calibracion:
            f_cal, lo_cal, hi_cal = m.calibracion
            s.append(T.SUPUESTO_CALIBRACION.format(fecha=f_cal.isoformat(), minimo=f"{lo_cal * 100:+.1f}%",
                                                   maximo=f"{hi_cal * 100:+.1f}%"))
    s.append(T.SUPUESTO_ROTACION.format(mult=f"{prm.multiplicador_techo:g}"))
    if len(medidos) < len(con_rv):
        s.append(T.SUPUESTO_SIN_MEDICION.format(banda=banda(prm.sin_medicion_min, prm.sin_medicion_max)))
    if sup:
        s.append(T.SUPUESTO_ALTA.format(alta=pct(sup.probabilidad_de_alta, 0), nota=sup.friccion_nota))
    agregados = [x for f in m.fondos for x in f.cartera.posiciones if x.es_agregado]
    if any(x.emisora == "OTROS-VALORES" for x in agregados):
        s.append(T.SUPUESTO_OTROS_VALORES)
    otros_tv = [x for x in agregados if x.emisora != "OTROS-VALORES"]
    if otros_tv:
        s.append(T.SUPUESTO_AGREGADOS.format(n=len(otros_tv), mdp=mdp(sum(x.valor_razonable for x in otros_tv))))
    for f in m.fondos:
        s.extend(n for n in f.mezcla.notas)
    if m.en_hermanos:
        s.append(T.NOTA_HERMANOS.format(mdp=mdp(m.en_hermanos)))
    if m.calificacion(prm).provisional:
        s.append(T.NOTA_PROVISIONAL)
    p.append(f"<h3>{e(T.TITULO_SUPUESTOS)}</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in s) + "</ul>")

    # Huecos
    h: list[str] = []
    sic = sorted({x.emisora_canonica for f in m.fondos for x in f.cartera.posiciones
                  if x.categoria is Categoria.ACCION_SIC and not x.es_agregado
                  and nombre_emisora_sic(x.emisora_canonica) == POR_CONFIRMAR})
    if sic:
        h.append(T.HUECO_SIC.format(claves=", ".join(sic)))
    sin_reg = sorted(f.clave for f in m.fondos if f.rv_max is None)
    if sin_reg:
        h.append(T.HUECO_REGIMEN.format(claves=", ".join(sin_reg)))
    media = sorted({x.emisora_canonica for f in m.fondos for x in f.cartera.posiciones
                    if x.categoria in (Categoria.ETF_EXTRANJERO, Categoria.ETF_LOCAL)
                    and x.emisora_canonica in etfs_confianza_media()})
    if media:
        h.append(T.HUECO_ETF_MEDIA.format(claves=", ".join(media), lista=", ".join(media)))
    if est:
        h.append(T.HUECO_ACTIVO_NETO.format(claves=", ".join(sorted(f.clave for f in est))))
    hermana = m.perfil.casa_de_bolsa_hermana if m.perfil else None
    if hermana is None:
        h.append(T.HUECO_CASA_BOLSA)
    if m.sin_cartera:
        h.append(T.HUECO_SIN_CARTERA.format(lista="; ".join(
            T.ITEM_SIN_CARTERA.format(clave=k, nota=n.strip()) if n.strip() else k for k, n in m.sin_cartera)))
    p.append(f"<h3>{e(T.TITULO_HUECOS)}</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in (h or [T.SIN_HUECOS])) + "</ul>")

    disc = [d for f in m.fondos for d in (f"{f.clave}: {x}" for x in f.discrepancias)]
    if disc:
        p.append(f"<h3>{e(T.TITULO_DISCREPANCIAS)}</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in disc) + "</ul>")

    # Fuentes
    p.append(f"<h3>{e(T.TITULO_FUENTES)}</h3><ul>")
    for f in sorted(m.fondos + m.excluidos_fdf, key=lambda x: x.clave):
        p.append("<li>" + e(T.FUENTE_FONDO.format(clave=f.clave, cita=f.cartera.procedencia.cita(),
                                                  sha=f.cartera.procedencia.doc_id[:12])) + "</li>")
        if f.dici:
            p.append("<li>" + e(T.FUENTE_DICI.format(clave=f.clave, cita=f.dici.procedencia.cita())) + "</li>")
        previos = sorted({(r.corte_a, h.procedencia.cita()) for r in f.rotacion.pares
                          for h in [next((x for x in _historia(f) if x.fecha_corte == r.corte_a), None)] if h})
        for fecha_p, cita in previos:
            p.append("<li>" + e(T.FUENTE_CORTE_PREVIO.format(clave=f.clave, fecha=fecha_p.isoformat(), cita=cita)) + "</li>")
    p.append("</ul>")
    if m.perfil:
        p.append(f"<p>{e(T.ETIQUETA_CASA_BOLSA)}: {e(m.perfil.evidencia_casa_de_bolsa)}</p>")
    p.append("<p>" + e(T.PIE_FINAL.format(version=__version__, version_plantillas=T.VERSION_PLANTILLAS)) + "</p>")
    p.append("</footer>")
    return "".join(p)


# ------------------------------------------------------------------ comparativo
def render_comparativo(ms: list[MetricasOperadora], prm: Parametros, cortes: list[str]) -> str:
    ms = sorted(ms, key=lambda m: (-m.calificacion(prm).total, m.clave))
    out = [
        '<header class="franja">' + _marca() +
        f"<h1>{e(T.TITULO_COMPARATIVO)}</h1><div class=\"meta\">"
        f"<span>{e(T.SUBTITULO_COMPARATIVO.format(cortes=', '.join(cortes)))}</span>"
        f'<span><b>{e(T.ETIQUETA_PARAMETROS)}:</b> {e(T.PARAMETROS.format(local=pb(prm.comision_local_pb), sic=pb(prm.comision_sic_pb), captura=pct(prm.captura_objetivo, 0), alta=T.ALTA_POR_OPERADORA))}</span>'
        "</div></header><main>"
    ]
    cols = T.COLUMNAS_CALIFICACION
    num = set(range(3, len(cols)))
    num.discard(10)
    th = "".join(f'<th class="num">{e(x)}</th>' if i in num else f"<th>{e(x)}</th>" for i, x in enumerate(cols))
    filas = []
    for m in ms:
        q = m.calificacion(prm)
        hermana = m.perfil.casa_de_bolsa_hermana if m.perfil else None
        txt_h = T.SI if hermana else (T.NO if hermana is False else POR_CONFIRMAR)
        lo, hi = m.bolsa_banda(prm)
        ilo, ihi = m.ingreso_esperado(prm)
        veto = f' <span class="veto">{e(T.VETO)}</span>' if q.veto else ""
        filas.append(
            f"<tr><td>{e(m.nombre)}</td><td class=\"mono\">{m.corte.isoformat()}</td>"
            f'<td title="{e(m.perfil.evidencia_casa_de_bolsa if m.perfil else "")}">{e(txt_h)}</td>'
            f'<td class="num">{q.bolsa:.1f}</td><td class="num">{q.independencia:.1f}{veto}</td>'
            f'<td class="num">{q.ajuste:.1f}</td><td class="num">{q.recurrencia:.1f}</td>'
            f'<td class="num">{q.headroom:.1f}</td><td class="num">{q.friccion:.1f}</td>'
            f'<td class="num"><b>{q.total:.2f}</b></td><td>{e(T.TIER_PROVISIONAL.format(tier=q.tier) if q.provisional else q.tier)}</td>'
            f'<td class="num">{banda(lo, hi, mdp)}</td><td class="num">{banda(ilo, ihi, lambda x: mdp(x, 2))}</td></tr>'
        )
    out.append(f'<section class="panel"><h2>{e(T.TITULO_CALIFICACION)}</h2><div class="tabla-scroll"><table class="compacta">'
               f"<thead><tr>{th}</tr></thead><tbody>{''.join(filas)}</tbody></table></div></section>")

    series = [(m.clave, COLORES_SERIES[i % len(COLORES_SERIES)]) for i, m in enumerate(sorted(ms, key=lambda x: x.clave))]
    puntos = []
    for m in ms:
        for f in m.fondos:
            if f.exposicion_rv <= 0:
                continue
            b = f.bolsa(f.rotacion.media, prm)
            puntos.append({"x": f.exposicion_rv, "y": f.pct_rv, "tam": b, "serie": m.clave,
                           "etiqueta": T.TOOLTIP_PUNTO.format(operadora=m.nombre, clave=f.clave, rv=mdp(f.exposicion_rv), pct=pct(f.pct_rv), bolsa=mdp(b, 2))})
    nombres = {m.clave: m.nombre for m in ms}
    out.append(
        f'<section class="panel"><h2>{e(T.TITULO_DISPERSION)}</h2>'
        + _leyenda([(nombres[k], "", c) for k, c in series], horizontal=True)
        + dispersion(puntos, series, T.EJE_X, T.EJE_Y)
        + f"<p class=\"pie\">{e(T.NOTA_BURBUJA)}</p></section>"
    )
    notas = [n.format(t1=f"{prm.tier1_min:.1f}", t2=f"{prm.tier2_min:.1f}", t1_menos=f"{prm.tier1_min - 0.1:.1f}",
                      esc_bolsa=" / ".join(mdp(x, 0) for x in prm.bolsa_cortes),
                      esc_rot=" / ".join(f"{x:g}" for x in prm.rotacion_cortes),
                      esc_head=" / ".join(pct(x, 0) for x in prm.headroom_cortes)) for n in T.NOTAS_COMPARATIVO]
    for m in sorted(ms, key=lambda x: x.clave):
        sup = prm.supuestos(m.clave, m.perfil.casa_de_bolsa_hermana if m.perfil else None)
        if sup:
            notas.append(T.NOTA_OPERADORA.format(operadora=m.nombre, texto=T.SUPUESTO_ALTA.format(alta=pct(sup.probabilidad_de_alta, 0), nota=sup.friccion_nota)))
        if m.perfil:
            notas.append(T.NOTA_OPERADORA.format(operadora=m.nombre, texto=f"{T.ETIQUETA_CASA_BOLSA}: {m.perfil.evidencia_casa_de_bolsa}"))
    out.append(f'<footer class="pie panel"><h3>{e(T.TITULO_NOTAS_COMPARATIVO)}</h3><ul>'
               + "".join(f"<li>{e(n)}</li>" for n in notas) + "</ul>"
               + "<p>" + e(T.PIE_FINAL.format(version=__version__, version_plantillas=T.VERSION_PLANTILLAS)) + "</p></footer>")
    out.append("</main>")
    return _doc(T.TITULO_COMPARATIVO, "".join(out))
