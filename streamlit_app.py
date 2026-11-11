"""Radar de operadoras de fondos · plataforma (Streamlit).

  streamlit run streamlit_app.py

Lee el histórico de data/radar.sqlite (lo actualiza la tarea programada de GitHub
Actions, ver .github/workflows/actualizar.yml). Los parámetros de la barra lateral
solo cambian esta sesión; para fijarlos, editar config/parametros.toml.
"""
from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from radar.config import cargar_parametros, ruta_db
from radar.core.modelo import POR_CONFIRMAR
from radar.render import plantillas as T
from radar.render.html import LOGO_PUNTO, render_comparativo, render_operadora
from radar.store.db import Store
from radar import vistas as V

# Identidad de Punto Casa de Bolsa (puntocasadebolsa.mx): morado, ámbar y verde de su sitio,
# Ubuntu en títulos y logotipo, Open Sans en el texto.
PRIMARIO, ACENTO, SECUNDARIO = "#522D6D", "#00857D", "#919AA2"
AMBAR, VERDE, MORADO_CLARO = "#FFB400", "#0FCB97", "#9A72B8"
SERIES = [PRIMARIO, ACENTO, AMBAR, VERDE, MORADO_CLARO, SECUNDARIO, "#3C444D", "#2F6DB5", "#C2185B", "#7A8B2E"]

st.set_page_config(page_title=f"{T.MARCA_NOMBRE} · Radar de operadoras", page_icon="📊", layout="wide")

px.defaults.color_discrete_sequence = SERIES
px.defaults.template = "plotly_white"

ESTILO_PUNTO = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=Ubuntu:wght@400;500;700&display=swap');
html, body, .stApp, p, li, label, input, textarea, button {{ font-family: 'Open Sans', sans-serif; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
h1, h2, h3, h4 {{ font-family: 'Ubuntu', 'Open Sans', sans-serif !important; color: {PRIMARIO} !important; }}
.punto-franja {{ background: #5B296E; color: #FFFFFF; border-radius: 10px; padding: 14px 22px;
  display: flex; align-items: center; gap: 18px; margin: 0 0 18px; }}
.punto-franja .logo svg {{ display: block; height: 44px; width: auto; }}
.punto-franja .area {{ border-left: 1px solid rgba(255,255,255,.55); padding-left: 18px;
  font-family: 'Ubuntu', sans-serif; font-size: 15px; }}
.punto-franja .area small {{ display: block; font-family: 'Open Sans', sans-serif; font-size: 12px; opacity: .85; }}
.punto-pie {{ margin-top: 32px; padding-top: 10px; border-top: 1px solid #E2E8F0; font-size: 12px; color: #6B737C; }}
[data-testid="stSidebar"] {{ background: #F7F5F8; }}
[data-testid="stMetricValue"] {{ color: {PRIMARIO}; font-family: 'Ubuntu', sans-serif; }}
</style>
"""
st.markdown(ESTILO_PUNTO, unsafe_allow_html=True)


def franja_punto():
    st.markdown(
        f'<div class="punto-franja"><div class="logo">{LOGO_PUNTO}</div>'
        f'<div class="area">{T.MARCA_AREA}<small>Herramienta interna · no es material para clientes</small></div></div>',
        unsafe_allow_html=True)


def pie_punto():
    st.markdown(f'<div class="punto-pie">{T.MARCA_NOMBRE} · Mesa de Capitales. Fuentes: CNBV (R1, R7), carteras, '
                'DICI y prospectos de cada operadora. Las cifras marcadas (e) son supuestos; ver Metodología.</div>',
                unsafe_allow_html=True)


# ------------------------------------------------------------------ datos
def _mtime() -> float:
    try:
        return os.path.getmtime(ruta_db())
    except OSError:
        return 0.0


@st.cache_data(show_spinner="Calculando métricas…")
def _universo(mtime: float, local: float, sic: float, captura: float, techo: float):
    prm = replace(cargar_parametros(), comision_local_pb=local, comision_sic_pb=sic,
                  captura_objetivo=captura, multiplicador_techo=techo)
    store = Store(ruta_db())
    try:
        return V.cargar(store, prm), prm
    finally:
        store.cerrar()


def _store() -> Store:
    return Store(ruta_db())


def parametros_sidebar():
    base = cargar_parametros()
    st.sidebar.header("Parámetros")
    local = st.sidebar.number_input("Comisión local (pb)", 0.0, 100.0, float(base.comision_local_pb), 0.5)
    sic = st.sidebar.number_input("Comisión SIC (pb)", 0.0, 100.0, float(base.comision_sic_pb), 0.5)
    captura = st.sidebar.slider("Captura objetivo", 0.0, 1.0, float(base.captura_objetivo), 0.01, format="%.2f")
    techo = st.sidebar.slider("Techo de rotación (× piso) (e)", 1.0, 3.0, float(base.multiplicador_techo), 0.1)
    st.sidebar.caption("Solo afectan esta sesión. Para fijarlos: config/parametros.toml.")
    mt = _mtime()
    st.sidebar.caption(f"Base de datos: {datetime.fromtimestamp(mt):%Y-%m-%d %H:%M}" if mt else "Sin base de datos")
    return _universo(mt, local, sic, captura, techo)


def mdp(x: float | None) -> str:
    return "—" if x is None else f"{x:,.1f}"


COL_PCT = st.column_config.NumberColumn(format="percent")
COL_MDP = st.column_config.NumberColumn(format="%,.1f")


# ------------------------------------------------------------------ páginas
def pagina_comparativo():
    u, prm = parametros_sidebar()
    st.title("Radar de operadoras · comparativo")
    if not u.metricas:
        st.warning("No hay operadoras con cifras. Corre `python -m radar actualizar`.")
        return
    df = V.comparativo(u, prm)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Operadoras con cifras", f"{len(u.metricas)} de {len(u.metricas) + len(u.sin_datos)}")
    c2.metric("Tier 1", int((df["Tier"] == "Tier 1").sum()))
    c3.metric("RV total (mdp)", f"{df['RV (mdp)'].sum():,.0f}")
    c4.metric("Sin casa de bolsa hermana", int((df["Casa de bolsa hermana"] == "No").sum()))

    f1, f2 = st.columns(2)
    solo_ind = f1.toggle("Solo sin casa de bolsa hermana", value=False)
    min_rv = f2.number_input("RV mínima (mdp)", 0.0, value=0.0, step=100.0)
    vista = df[(df["RV (mdp)"] >= min_rv) & ((df["Casa de bolsa hermana"] == "No") | (not solo_ind))]
    st.dataframe(
        vista.drop(columns=["clave"]), hide_index=True, use_container_width=True,
        column_config={
            "% RV": COL_PCT, "% RV en directo": COL_PCT, "Rotación medida (% expos.)": COL_PCT, "Activos netos (mdp)": COL_MDP, "RV (mdp)": COL_MDP,
            "Bolsa mín. (mdp)": COL_MDP, "Bolsa máx. (mdp)": COL_MDP,
            "Ingreso esperado máx. (mdp) (e)": st.column_config.NumberColumn(format="%,.2f"),
            "Rotación media": st.column_config.NumberColumn(format="%.2fx"),
            "Calificación": st.column_config.ProgressColumn(min_value=1, max_value=5, format="%.2f"),
        },
    )
    st.caption("Tier 1 ≥ 4.0 · Tier 2 de 3.0 a 3.9 · Tier 3 < 3.0. Con casa de bolsa hermana: independencia = 1 "
               "y no puede ser Tier 1 (veto). Fuente CNBV: cortes con ~45 días de rezago; sin DICI el régimen queda "
               "[POR CONFIRMAR]. «CNBV R7/R1 + DICI»: cartera de la CNBV con régimen, comisiones y distribuidoras "
               "del DICI de la operadora.")

    st.subheader(T.TITULO_DISPERSION)
    pts = V.puntos_dispersion(u, prm)
    if len(pts):
        fig = px.scatter(pts, x="Exposición RV (mdp)", y="% RV", size="Bolsa (mdp)", color="Operadora",
                         hover_data=["Fondo", "Bolsa (mdp)"], log_x=True, size_max=45,
                         color_discrete_sequence=SERIES, height=520)
        fig.update_layout(yaxis_range=[-5, 105], legend_title_text="", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(T.NOTA_BURBUJA)

    with st.expander("Operadoras sin cifras"):
        st.dataframe(pd.DataFrame([{"Operadora": k, "Motivo": v} for k, v in sorted(u.sin_datos.items())]),
                     hide_index=True, use_container_width=True)
    st.download_button("Descargar comparativo (HTML)",
                       render_comparativo(list(u.metricas.values()), prm, [max(m.corte for m in u.metricas.values()).isoformat()]),
                       file_name="comparativo.html", mime="text/html")


def _selector_operadora(u):
    nombres = {m.nombre: k for k, m in sorted(u.metricas.items(), key=lambda kv: kv[1].nombre)}
    if not nombres:
        st.warning("No hay operadoras con cifras.")
        st.stop()
    elegido = st.selectbox("Operadora", list(nombres), index=0)
    return nombres[elegido]


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _noticias(emisora: str, nombre: str):
    from radar.noticias import noticias

    return noticias(emisora, nombre)


def seccion_que_enviarle(m):
    """Qué research, noticias e ideas mandarle a la operadora, según lo que tiene y lo que operó."""
    from radar.core.contenido import plan_contenido
    from radar.noticias import consulta, url_busqueda

    plan = plan_contenido(m)
    st.subheader("Qué enviarle")
    st.caption("Sugerencias a partir de su cartera: qué emisoras pesan más, qué compró o vendió entre los dos "
               "últimos cortes y cómo reparte su renta variable y su renta fija. Reglas fijas, ver Metodología.")
    for p in plan.perfil:
        st.markdown(f"- {p}")

    if plan.temas:
        cols = st.columns(2)
        for i, t in enumerate(plan.temas):
            with cols[i % 2].container(border=True):
                st.markdown(f"**{t.titulo}**")
                st.markdown(f"<span style='color:#6B737C'>Por qué:</span> {t.por_que}", unsafe_allow_html=True)
                st.markdown(f"<span style='color:#6B737C'>Qué enviar:</span> {t.que_enviar}", unsafe_allow_html=True)

    st.markdown("**Emisoras clave**")
    df = pd.DataFrame([{
        "Emisora": e.emisora, "Nombre": e.nombre, "Sector": e.sector, "Mercado": e.mercado,
        "Monto (mdp)": e.monto / 1e6, "Peso en su RV": e.peso_rv, "Fondos": e.fondos,
        "Movimiento": e.movimiento, "Cambio en títulos": e.cambio_titulos,
        "Compra / venta est. (mdp)": e.monto_movimiento / 1e6,
        "Noticias": url_busqueda(consulta(e.emisora, e.nombre)),
    } for e in plan.emisoras])
    if len(df):
        st.dataframe(df, hide_index=True, use_container_width=True, column_config={
            "Monto (mdp)": COL_MDP, "Compra / venta est. (mdp)": COL_MDP, "Cambio en títulos": COL_PCT,
            "Peso en su RV": st.column_config.ProgressColumn(format="percent", min_value=0,
                                                             max_value=float(df["Peso en su RV"].max() or 1)),
            "Noticias": st.column_config.LinkColumn("Noticias", display_text="Ver noticias")})
    if plan.salidas:
        st.markdown("**Vendió por completo**")
        st.dataframe(pd.DataFrame([{"Emisora": e.emisora, "Nombre": e.nombre, "Sector": e.sector,
                                    "Valor en el corte anterior (mdp)": -e.monto_movimiento / 1e6}
                                   for e in plan.salidas]),
                     hide_index=True, use_container_width=True,
                     column_config={"Valor en el corte anterior (mdp)": COL_MDP})

    con_noticias = [e for e in plan.emisoras if e.mercado in ("México", "SIC")
                    and not e.nombre.startswith("[") and not e.sector.startswith("ETF")][:6]
    if con_noticias:
        st.markdown("**Noticias recientes de sus principales emisoras** (últimos 14 días)")
        for tab, e in zip(st.tabs([e.emisora for e in con_noticias]), con_noticias):
            with tab:
                st.markdown(f"**{e.nombre}** · {e.sector} · {e.peso_rv:.1%} de su renta variable")
                notas = _noticias(e.emisora, e.nombre)
                for n in notas:
                    fecha = n.fecha.strftime("%d-%b") if n.fecha else ""
                    st.markdown(f"- [{n.titulo}]({n.liga}) <span style='color:#6B737C;font-size:12px'>"
                                f"{n.fuente} · {fecha}</span>", unsafe_allow_html=True)
                if not notas:
                    st.caption("Sin noticias recientes o servicio no disponible.")
                st.markdown(f"[Más noticias]({url_busqueda(consulta(e.emisora, e.nombre))})")
        st.caption("Encabezados de Google Noticias; verificar la nota original antes de enviarla.")

    st.download_button("Descargar plan de contenido (Markdown)", plan.markdown(m.nombre),
                       file_name=f"que_enviarle_{m.clave}_{m.corte.isoformat()}.md", mime="text/markdown")


def pagina_operadora():
    u, prm = parametros_sidebar()
    op = _selector_operadora(u)
    m = u.metricas[op]
    hermana = m.perfil.casa_de_bolsa_hermana if m.perfil else None
    st.title(T.TITULO_OPERADORA.format(operadora=m.nombre))
    st.caption(f"Corte {m.corte.isoformat()} · Fuente: {V.fuente_de(op)} · Casa de bolsa hermana: "
               f"{'Sí' if hermana else ('No' if hermana is False else POR_CONFIRMAR)}")

    an = m.activo_neto
    cols = st.columns(6)
    vals = [str(len(m.fondos)), mdp(an / 1e6), str(len(m.fondos_con_rv)),
            mdp(m.exposicion_rv / 1e6), mdp(m.monto_rf / 1e6), mdp(m.monto_efe / 1e6)]
    subs = [T.SUB_FONDOS.format(n=len(m.excluidos_fdf)), T.SUB_MDP, T.SUB_FONDOS_RV.format(n=len(m.fondos)),
            f"{m.exposicion_rv / an:.1%}" if an else "", f"{m.monto_rf / an:.1%}" if an else "",
            f"{m.monto_efe / an:.1%}" if an else ""]
    for c, (_, et), v, s in zip(cols, T.INDICADORES, vals, subs):
        c.metric(et, v, s, delta_color="off")

    d1, d2 = st.columns(2)
    n_tipo = {t: sum(1 for f in m.fondos if f.tipo_fondo == t) for t in ("RV", "RF")}
    a_tipo = {t: sum(f.activo_neto for f in m.fondos if f.tipo_fondo == t) / 1e6 for t in ("RV", "RF")}
    for col, titulo, datos in ((d1, T.TITULO_DONA_FONDOS, n_tipo), (d2, T.TITULO_DONA_ACTIVOS, a_tipo)):
        fig = go.Figure(go.Pie(labels=[T.TIPO_FONDO[t] for t in datos], values=list(datos.values()), hole=0.6,
                               marker_colors=[PRIMARIO, ACENTO], textinfo="percent", sort=False))
        fig.update_layout(title=titulo, height=300, margin=dict(l=10, r=10, t=40, b=10))
        col.plotly_chart(fig, use_container_width=True)

    st.subheader(T.TITULO_TABLA_FONDOS)
    st.dataframe(V.tabla_fondos(m), hide_index=True, use_container_width=True, column_config={
        "% RV": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "% RF": COL_PCT, "% Efectivo": COL_PCT, "Activos netos (mdp)": COL_MDP, "RV (mdp)": COL_MDP,
        "RF (mdp)": COL_MDP, "Máx. RV régimen": COL_PCT, "Headroom (mdp)": COL_MDP})

    t1, t2 = st.columns(2)
    for col, titulo, df in ((t1, T.TITULO_TOP_RV, V.top_rv(m)), (t2, T.TITULO_TOP_RF, V.top_rf(m))):
        col.subheader(titulo)
        if len(df):
            col.dataframe(df, hide_index=True, use_container_width=True, column_config={
                "Monto (mdp)": COL_MDP,
                "Peso en la clase": st.column_config.ProgressColumn(format="percent", min_value=0,
                                                                     max_value=float(df["Peso en la clase"].max()))})
        else:
            col.info(T.SIN_POSICIONES)

    q = m.calificacion(prm)
    lo, hi = m.bolsa_banda(prm)
    st.subheader("Calificación y bolsa")
    k = st.columns(4)
    k[0].metric("Calificación", f"{q.total:.2f}", q.tier + (" · veto" if q.veto else ""), delta_color="off")
    k[1].metric("Bolsa de comisión (mdp)", f"{lo / 1e6:,.1f}–{hi / 1e6:,.1f}")
    rot, medida = m.rotacion_ponderada()
    k[2].metric("Rotación media", f"{rot:.2f}x", "medida" if medida else "supuesta (e)", delta_color="off")
    k[3].metric("Headroom RV (mdp)", mdp(m.headroom / 1e6))

    seccion_que_enviarle(m)

    html = render_operadora(m, prm)
    st.download_button("Descargar one-pager (HTML)", html, file_name=f"{op}_{m.corte.isoformat()}.html", mime="text/html")
    with st.expander("Metodología, supuestos, huecos y fuentes (pie del one-pager)"):
        st.components.v1.html(html, height=900, scrolling=True)


def pagina_fondo():
    u, prm = parametros_sidebar()
    op = _selector_operadora(u)
    m = u.metricas[op]
    fondos = {f.clave: f for f in m.fondos + m.excluidos_fdf}
    clave = st.selectbox("Fondo", sorted(fondos))
    f = fondos[clave]
    st.title(f"{f.clave} · {f.nombre_corto or f.nombre_legal or ''}")
    st.caption(f"{f.categoria_regulatoria} · corte {f.fecha_corte.isoformat()} · {f.cartera.procedencia.cita()}"
               + (" · fondo de fondos (excluido de cifras)" if f.es_fondo_de_fondos else ""))
    c = st.columns(5)
    c[0].metric("Activo neto (mdp)", mdp(f.activo_neto / 1e6), "estimado (e)" if f.activo_neto_estimado else "publicado",
                delta_color="off")
    c[1].metric("% RV", f"{f.pct_rv:.1%}")
    c[2].metric("Régimen RV", "—" if f.rv_max is None else f"{(f.rv_min or 0):.0%}–{f.rv_max:.0%}")
    c[3].metric("Rotación (piso–techo)", f"{f.rotacion.minimo:.2f}x–{f.rotacion.maximo:.2f}x",
                "medida" if f.rotacion.medida else "supuesta (e)", delta_color="off")
    c[4].metric("Bolsa (mdp)", f"{f.bolsa_banda(prm)[0] / 1e6:,.2f}–{f.bolsa_banda(prm)[1] / 1e6:,.2f}")

    st.subheader("Posiciones")
    st.dataframe(V.posiciones(f), hide_index=True, use_container_width=True,
                 column_config={"Valor (mdp)": st.column_config.NumberColumn(format="%,.2f"), "% cartera": COL_PCT,
                                "Títulos": st.column_config.NumberColumn(format="%,.0f")})
    st.subheader("Rotación observada por tramo (piso)")
    tr = V.tramos_rotacion(f)
    st.dataframe(tr, hide_index=True, use_container_width=True) if len(tr) else st.info(
        "Sin dos cortes comparables: se usa la banda supuesta (e).")
    h = V.historia(f)
    if len(h) > 1:
        st.subheader("Historia")
        st.line_chart(h.set_index("Corte")[["Activo neto (mdp)"]])
    if f.dici:
        st.subheader("DICI")
        st.dataframe(pd.DataFrame([{"Serie": s.serie, "Posibles adquirentes": s.posibles_adquirentes,
                                    "Monto mínimo": s.monto_minimo, "Comisión de administración": s.comision_administracion,
                                    "Costo total": s.costo_total} for s in f.dici.series]),
                     hide_index=True, use_container_width=True,
                     column_config={"Comisión de administración": st.column_config.NumberColumn(format="percent"),
                                    "Costo total": st.column_config.NumberColumn(format="percent")})
        st.caption(f"Liquidez: {f.dici.liquidez or '—'} · Liquidación: {f.dici.plazo_liquidacion or '—'} · "
                   f"Límite de recompra: {f.dici.limite_recompra or '—'} · Índice: {f.dici.indice_referencia or '—'}")
    for n in f.discrepancias:
        st.warning(f"‡ {n}")
    for n in f.notas:
        st.caption(n)


def pagina_estado():
    st.title("Estado de los datos")
    store = _store()
    try:
        est = V.estado(store)
        if len(est):
            ok = (est["Estado"] == "OK").sum()
            st.metric("Operadoras procesadas sin error", f"{ok} de {len(est)}")
            st.dataframe(est.drop(columns=["clave"]), hide_index=True, use_container_width=True)
        st.subheader("ETFs pendientes de clasificar")
        st.caption("Regla dura: un ETF se clasifica por su subyacente y nunca se adivina. Mientras una operadora tenga "
                   "ETFs fuera de radar/core/datos/etfs.csv, sus cifras no se calculan.")
        pend = V.etfs_pendientes(store)
        if len(pend):
            st.dataframe(pend, hide_index=True, use_container_width=True, column_config={"Monto (mdp)": COL_MDP})
            st.download_button("Descargar CSV", pend.to_csv(index=False).encode("utf-8"), "etfs_pendientes.csv", "text/csv")
        else:
            st.success("Sin ETFs pendientes.")
        st.subheader("Documentos en el histórico")
        st.dataframe(V.documentos(store), hide_index=True, use_container_width=True)
        st.subheader("Conciliaciones entre fuentes")
        conc = V.conciliaciones(store)
        if len(conc):
            st.dataframe(conc, hide_index=True, use_container_width=True,
                         column_config={"Diferencia": COL_PCT, "Monto A (mdp)": COL_MDP, "Monto B (mdp)": COL_MDP})
    finally:
        store.cerrar()


def pagina_metodologia():
    st.title(T.TITULO_METODOLOGIA)
    prm = cargar_parametros()
    from radar.core.clasificacion import version_diccionario_etfs

    for par in T.METODOLOGIA:
        st.markdown(par.format(version_etfs=version_diccionario_etfs(), tol=f"{prm.tolerancia_cuadre:.1%}",
                               n_cortes=prm.cortes_para_cifra, max_meses=f"{prm.max_meses_par:g}",
                               umbral=f"{prm.umbral_discrepancia:.0%}"))
    from radar.core import contenido as C

    st.subheader("Qué enviarle (página Operadora)")
    st.markdown(
        f"- **Emisoras clave:** las 15 con más monto en su renta variable (acciones México, SIC y ETFs), con su peso, "
        f"cuántos fondos la tienen y su movimiento entre los dos últimos cortes, medido en **títulos** (sin efecto "
        f"precio): Nueva, Aumentó o Redujo (±{C.UMBRAL_MOVIMIENTO:.0%}), Estable o Salida. Si un corte agrupa ese tipo "
        "de valor en un renglón sin emisora, se marca «Sin desglose» y no cuenta como compra ni venta.\n"
        f"- **Temas:** México si pesa ≥ {C.UMBRAL_MEXICO:.0%} de su RV; SIC ≥ {C.UMBRAL_SIC:.0%}; ETFs ≥ {C.UMBRAL_ETF:.0%}; "
        f"un sector ≥ {C.UMBRAL_SECTOR:.0%} de su RV con sector conocido; FIBRAs ≥ {C.UMBRAL_FIBRAS:.0%}; compras y "
        f"ventas recientes; renta fija por segmento (≥ {C.UMBRAL_SEGMENTO_RF:.0%} de su RF) cuando la RF pesa ≥ "
        f"{C.UMBRAL_RF:.0%} de sus activos; espacio de régimen ≥ {C.UMBRAL_HEADROOM:.0%} de su RV; casa de bolsa hermana.\n"
        "- **Sectores y nombres:** catálogo propio en radar/core/datos/emisoras.csv (solo emisoras inequívocas); ETFs "
        "con la descripción del diccionario de ETFs. Lo demás sale «Sin sector» / [POR CONFIRMAR].\n"
        "- **Noticias:** encabezados de Google Noticias (últimos 14 días) buscados por nombre de la emisora y términos "
        "bursátiles; se consultan en vivo y no entran al one-pager.")

    st.subheader("Notas de la calificación")
    for n in T.NOTAS_COMPARATIVO:
        st.markdown("- " + n.format(t1=f"{prm.tier1_min:.1f}", t2=f"{prm.tier2_min:.1f}",
                                    t1_menos=f"{prm.tier1_min - 0.1:.1f}",
                                    esc_bolsa=" / ".join(f"{x / 1e6:,.0f}" for x in prm.bolsa_cortes),
                                    esc_rot=" / ".join(f"{x:g}" for x in prm.rotacion_cortes),
                                    esc_head=" / ".join(f"{x:.0%}" for x in prm.headroom_cortes)))


paginas = st.navigation([
    st.Page(pagina_comparativo, title="Comparativo", icon="📊", default=True),
    st.Page(pagina_operadora, title="Operadora", icon="🏦", url_path="operadora"),
    st.Page(pagina_fondo, title="Fondo", icon="📄", url_path="fondo"),
    st.Page(pagina_estado, title="Estado de los datos", icon="🩺", url_path="estado"),
    st.Page(pagina_metodologia, title="Metodología", icon="📐", url_path="metodologia"),
])
st.sidebar.markdown(f"**{T.MARCA_NOMBRE}**  \nMesa de Capitales")
franja_punto()
paginas.run()
pie_punto()
