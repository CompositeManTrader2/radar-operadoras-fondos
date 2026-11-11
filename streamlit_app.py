"""Radar de operadoras de fondos · Punto Casa de Bolsa, Mesa de Capitales (Streamlit).

  streamlit run streamlit_app.py

Lee el histórico de data/radar.sqlite (lo actualiza la tarea programada de GitHub Actions, ver
.github/workflows/actualizar.yml). Los supuestos de comisión que se mueven en la app solo cambian
la sesión; para fijarlos, editar config/parametros.toml.
"""
from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from radar import vistas as V
from radar.config import cargar_parametros, ruta_db
from radar.core.modelo import POR_CONFIRMAR
from radar.render import plantillas as T
from radar.render.html import LOGO_PUNTO, render_comparativo, render_operadora
from radar.store.db import Store

st.set_page_config(page_title=f"{T.MARCA_NOMBRE} · Radar de operadoras", page_icon=":material/insights:",
                   layout="wide", initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ sistema visual
# Interfaz: morado institucional de Punto (puntocasadebolsa.mx), Ubuntu en títulos, Open Sans en texto.
MARCA, MARCA_2, TINTA, TEXTO, SUAVE, LINEA, FONDO = (
    "#522D6D", "#5B296E", "#24272D", "#3C444D", "#6B737C", "#E6E1EA", "#F6F5F8")
# Datos: paleta categórica derivada de la marca, validada (banda de luminosidad, croma, daltonismo
# y separación normal). El ámbar queda bajo 3:1 de contraste: siempre va con etiqueta o tabla.
SERIE_RV, SERIE_RF, SERIE_EFE, SERIE_4 = "#7A4E9E", "#00A090", "#D99A00", "#4C7BD6"
# Tiers: rampa secuencial de un solo tono (más oscuro = mejor).
COLOR_TIER = {"Tier 1": "#4B2766", "Tier 2": "#8A66AD", "Tier 3": "#C6B3D8"}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=Ubuntu:wght@400;500;700&display=swap');
html, body, .stApp, p, li, label, input, textarea, button, td, th {{ font-family: 'Open Sans', sans-serif; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
.stApp {{ background: {FONDO}; }}
header[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer,
[data-testid="stSidebarCollapsedControl"], [data-testid="stDecoration"] {{ display: none !important; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 2rem; max-width: 1320px; }}
h1, h2, h3, h4 {{ font-family: 'Ubuntu', 'Open Sans', sans-serif !important; color: {TINTA} !important; }}

/* encabezado institucional */
.pc-header {{ background: linear-gradient(90deg, #45215C 0%, {MARCA_2} 100%); color: #FFF;
  margin: 0 -1rem; padding: 18px 30px; border-radius: 0 0 16px 16px;
  display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; }}
.pc-header .izq {{ display: flex; align-items: center; gap: 20px; }}
.pc-header .logo svg {{ display: block; height: 42px; width: auto; }}
.pc-header .app {{ border-left: 1px solid rgba(255,255,255,.4); padding-left: 20px; }}
.pc-header .app b {{ display: block; font-family: 'Ubuntu', sans-serif; font-weight: 500; font-size: 17px; }}
.pc-header .app span {{ font-size: 12px; opacity: .8; }}
.pc-header .der {{ text-align: right; font-size: 12px; opacity: .9; line-height: 1.5; }}
.pc-header .der b {{ font-weight: 600; }}

/* navegación */
.st-key-pc_nav {{ background: #FFF; border: 1px solid {LINEA}; border-radius: 12px; padding: 4px 8px;
  margin: 14px 0 6px; }}
.st-key-pc_nav [data-testid="stPageLink"] a {{ border-radius: 8px; padding: 6px 14px; }}
.st-key-pc_nav [data-testid="stPageLink"] a p {{ font-weight: 600; color: {TEXTO}; font-size: 14px; }}
.st-key-pc_nav [data-testid="stPageLink"] a[aria-current="page"],
.st-key-pc_nav [data-testid="stPageLink-NavLink"][aria-current="page"] {{ background: #F1EAF6; }}
.st-key-pc_nav [data-testid="stPageLink"] a[aria-current="page"] p {{ color: {MARCA}; }}

/* título de página */
.pc-eyebrow {{ font-size: 11.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  color: {SERIE_RV}; margin: 18px 0 2px; }}
.pc-h1 {{ font-family: 'Ubuntu', sans-serif; font-size: 30px; font-weight: 500; color: {TINTA}; margin: 0; line-height: 1.2; }}
.pc-sub {{ color: {SUAVE}; font-size: 13.5px; margin: 4px 0 6px; }}

/* tarjetas de indicadores */
.pc-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(165px, 1fr)); gap: 14px; margin: 10px 0 6px; }}
.pc-kpi {{ background: #FFF; border: 1px solid {LINEA}; border-radius: 12px; padding: 15px 18px;
  box-shadow: 0 1px 2px rgba(40, 20, 60, .04); }}
.pc-kpi.principal {{ border-top: 3px solid {MARCA}; }}
.pc-kpi .et {{ font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: {SUAVE}; }}
.pc-kpi .val {{ font-family: 'Ubuntu', sans-serif; font-size: 26px; color: {TINTA}; margin-top: 6px;
  font-variant-numeric: tabular-nums; white-space: nowrap; }}
.pc-kpi .nota {{ font-size: 12px; color: {SUAVE}; margin-top: 2px; }}

/* secciones */
.pc-seccion {{ margin: 26px 0 8px; }}
.pc-seccion .t {{ font-family: 'Ubuntu', sans-serif; font-size: 18px; font-weight: 500; color: {TINTA}; }}
.pc-seccion .d {{ font-size: 13px; color: {SUAVE}; margin-top: 2px; }}

/* insignias */
.pc-badge {{ display: inline-block; padding: 2px 11px; border-radius: 999px; font-size: 12px; font-weight: 600;
  margin-right: 6px; white-space: nowrap; }}
.pc-badge.t1 {{ background: #EDE4F4; color: #4B2766; }} .pc-badge.t2 {{ background: #F3EEF7; color: #6B4A8C; }}
.pc-badge.t3 {{ background: #F0F1F3; color: #555C64; }} .pc-badge.alerta {{ background: #FBE9E3; color: #A3461F; }}
.pc-badge.ok {{ background: #E3F6EF; color: #05704F; }} .pc-badge.neutro {{ background: #F0F1F3; color: #555C64; }}

/* ficha de operadora */
.pc-ficha {{ background: #FFF; border: 1px solid {LINEA}; border-radius: 14px; padding: 18px 22px; margin: 12px 0 4px;
  display: flex; justify-content: space-between; align-items: center; gap: 18px; flex-wrap: wrap; }}
.pc-ficha .nombre {{ font-family: 'Ubuntu', sans-serif; font-size: 24px; color: {TINTA}; }}
.pc-ficha .meta {{ font-size: 13px; color: {SUAVE}; margin-top: 4px; }}
.pc-ficha .score {{ text-align: right; }}
.pc-ficha .score .n {{ font-family: 'Ubuntu', sans-serif; font-size: 38px; color: {MARCA}; line-height: 1; }}
.pc-ficha .score .de {{ font-size: 12px; color: {SUAVE}; }}

/* temas de "qué enviarle" */
.pc-tema {{ background: #FFF; border: 1px solid {LINEA}; border-left: 4px solid {SERIE_RV}; border-radius: 10px;
  padding: 14px 16px; margin-bottom: 12px; }}
.pc-tema .t {{ font-weight: 700; color: {TINTA}; margin-bottom: 6px; }}
.pc-tema .r {{ font-size: 13px; margin: 3px 0; color: {TEXTO}; }}
.pc-tema .r span {{ color: {SUAVE}; font-weight: 600; }}
.pc-lista {{ margin: 4px 0 0; padding-left: 18px; color: {TEXTO}; font-size: 14px; }}
.pc-lista li {{ margin: 3px 0; }}
.pc-nota {{ background: #FFF; border: 1px solid {LINEA}; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }}
.pc-nota a {{ color: {TINTA}; font-weight: 600; text-decoration: none; }}
.pc-nota a:hover {{ color: {MARCA}; text-decoration: underline; }}
.pc-nota .f {{ font-size: 12px; color: {SUAVE}; margin-top: 2px; }}

/* componentes de Streamlit */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINEA}; }}
.stTabs [data-baseweb="tab"] {{ padding: 10px 16px !important; }}
.stTabs [data-baseweb="tab"] p {{ font-weight: 600; font-size: 14px; color: {TEXTO}; }}
.stTabs [data-baseweb="tab"][aria-selected="true"] p {{ color: {MARCA}; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINEA}; border-radius: 10px; overflow: hidden; background: #FFF; }}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{ border-color: {LINEA}; }}
.stDownloadButton button, .stButton button, [data-testid="stPopover"] button {{ border-radius: 8px; }}
@media (max-width: 640px) {{
  .pc-header {{ padding: 14px 18px; }}
  .pc-header .logo svg {{ height: 32px; }}
  .pc-header .app span, .pc-header .der {{ display: none; }}
  .pc-header .app b {{ font-size: 15px; }}
  .pc-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
  .pc-kpi .val {{ font-size: 21px; }}
  .pc-h1 {{ font-size: 24px; }}
}}
.pc-pie {{ margin-top: 36px; padding: 14px 0 0; border-top: 1px solid {LINEA}; font-size: 12px; color: {SUAVE};
  display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


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


def _supuestos() -> dict:
    base = cargar_parametros()
    return st.session_state.setdefault("supuestos", {
        "local": float(base.comision_local_pb), "sic": float(base.comision_sic_pb),
        "captura": float(base.captura_objetivo), "techo": float(base.multiplicador_techo)})


def universo():
    s = _supuestos()
    return _universo(_mtime(), s["local"], s["sic"], s["captura"], s["techo"])


def control_supuestos():
    """Botón con los supuestos de comisión (solo cambian la sesión)."""
    s = _supuestos()
    base = cargar_parametros()
    with st.popover("Supuestos", icon=":material/tune:"):
        st.markdown("**Supuestos de comisión**")
        s["local"] = st.number_input("Comisión local (pb)", 0.0, 100.0, s["local"], 0.5, key="w_local")
        s["sic"] = st.number_input("Comisión SIC (pb)", 0.0, 100.0, s["sic"], 0.5, key="w_sic")
        s["captura"] = st.slider("Captura objetivo", 0.0, 1.0, s["captura"], 0.01, format="%.2f", key="w_captura")
        s["techo"] = st.slider("Techo de rotación (× piso) (e)", 1.0, 3.0, s["techo"], 0.1, key="w_techo")
        if st.button("Restablecer", icon=":material/restart_alt:"):
            st.session_state["supuestos"] = {
                "local": float(base.comision_local_pb), "sic": float(base.comision_sic_pb),
                "captura": float(base.captura_objetivo), "techo": float(base.multiplicador_techo)}
            for k in ("w_local", "w_sic", "w_captura", "w_techo"):
                st.session_state.pop(k, None)
            st.rerun()
        st.caption("Solo afectan esta sesión. Valores permanentes: config/parametros.toml.")


def mdp(x: float | None, dec: int = 1) -> str:
    return "—" if x is None else f"{x:,.{dec}f}"


COL_PCT = st.column_config.NumberColumn(format="percent")
COL_MDP = st.column_config.NumberColumn(format="%,.1f")


# ------------------------------------------------------------------ componentes
def encabezado():
    mt = _mtime()
    act = datetime.fromtimestamp(mt).strftime("%d/%m/%Y %H:%M") if mt else "sin base de datos"
    st.markdown(
        f'<div class="pc-header"><div class="izq"><div class="logo">{LOGO_PUNTO}</div>'
        f'<div class="app"><b>Radar de operadoras de fondos</b><span>Mesa de Capitales · uso interno</span></div></div>'
        f'<div class="der">Datos actualizados<br><b>{act}</b></div></div>', unsafe_allow_html=True)


def titulo(eyebrow: str, texto: str, sub: str = "", supuestos: bool = False):
    izq, der = st.columns([5, 1], vertical_alignment="bottom")
    izq.markdown(f'<div class="pc-eyebrow">{eyebrow}</div><div class="pc-h1">{texto}</div>'
                 + (f'<div class="pc-sub">{sub}</div>' if sub else ""), unsafe_allow_html=True)
    if supuestos:
        with der:
            control_supuestos()


def seccion(texto: str, desc: str = ""):
    st.markdown(f'<div class="pc-seccion"><div class="t">{texto}</div>'
                + (f'<div class="d">{desc}</div>' if desc else "") + "</div>", unsafe_allow_html=True)


def tarjetas(items: list[tuple[str, str, str]], principal: int | None = 0):
    html = "".join(
        f'<div class="pc-kpi{" principal" if i == principal else ""}"><div class="et">{et}</div>'
        f'<div class="val">{val}</div><div class="nota">{nota}</div></div>'
        for i, (et, val, nota) in enumerate(items))
    st.markdown(f'<div class="pc-kpis">{html}</div>', unsafe_allow_html=True)


def badge_tier(tier: str) -> str:
    clase = "t1" if tier.startswith("Tier 1") else "t2" if tier.startswith("Tier 2") else "t3"
    return f'<span class="pc-badge {clase}">{tier}</span>'


def badge(texto: str, clase: str = "neutro") -> str:
    return f'<span class="pc-badge {clase}">{texto}</span>'


def estilo(fig: go.Figure, alto: int) -> go.Figure:
    fig.update_layout(
        height=alto, margin=dict(l=8, r=16, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
        font=dict(family="Open Sans, sans-serif", size=12, color=TEXTO), showlegend=False,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINEA, font=dict(color=TINTA, size=12)))
    fig.update_xaxes(gridcolor="#EEE9F2", zeroline=False, linecolor=LINEA, tickfont=dict(color=SUAVE))
    fig.update_yaxes(gridcolor="#EEE9F2", zeroline=False, linecolor=LINEA, tickfont=dict(color=SUAVE))
    return fig


def dona(etiquetas: list[str], valores: list[float], colores: list[str], centro: str, unidad: str) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=etiquetas, values=valores, hole=0.68, sort=False, direction="clockwise",
        marker=dict(colors=colores, line=dict(color="#FFFFFF", width=2)),
        textinfo="none", hovertemplate="%{label}<br>%{value:,.1f} " + unidad + " · %{percent}<extra></extra>"))
    fig.add_annotation(text=centro, showarrow=False, font=dict(family="Ubuntu, sans-serif", size=18, color=TINTA))
    return estilo(fig, 230)


def leyenda(items: list[tuple[str, str, str]]):
    html = "".join(
        f'<div style="display:flex;align-items:center;gap:10px;margin:7px 0;font-size:14px">'
        f'<span style="width:12px;height:12px;border-radius:3px;background:{c};flex:none"></span>'
        f'<span style="color:{TEXTO}">{t}</span><span style="margin-left:auto;font-weight:600;color:{TINTA};'
        f'font-variant-numeric:tabular-nums">{v}</span></div>' for c, t, v in items)
    st.markdown(html, unsafe_allow_html=True)


def pie():
    st.markdown(
        f'<div class="pc-pie"><span>{T.MARCA_NOMBRE} · Mesa de Capitales · Herramienta interna, no es material para '
        'clientes.</span><span>Fuentes: CNBV (R1, R7), carteras, DICI y prospectos de cada operadora. '
        'Las cifras (e) son supuestos.</span></div>', unsafe_allow_html=True)


def _operadora_actual(u, etiqueta: bool = True) -> str:
    claves = sorted(u.metricas, key=lambda k: u.metricas[k].nombre)
    if not claves:
        st.warning("No hay operadoras con cifras.")
        st.stop()
    actual = st.session_state.get("op")
    if actual not in claves:
        actual = max(claves, key=lambda k: u.metricas[k].calificacion(u_prm()).total)
    elegido = st.selectbox("Operadora", claves, index=claves.index(actual),
                           format_func=lambda k: u.metricas[k].nombre, key=f"sel_op_{actual}",
                           label_visibility="visible" if etiqueta else "collapsed")
    st.session_state["op"] = elegido
    return elegido


def u_prm():
    return universo()[1]


# ------------------------------------------------------------------ páginas
def pagina_resumen():
    u, prm = universo()
    if not u.metricas:
        titulo("Radar", "Panorama de operadoras")
        st.warning("No hay operadoras con cifras. Corre `python -m radar actualizar`.")
        return
    df = V.comparativo(u, prm)
    cortes = sorted({m.corte for m in u.metricas.values()})
    titulo("Radar de operadoras", "Panorama de operadoras",
           f"{len(u.metricas)} operadoras de fondos · cortes del {cortes[0]:%d/%m/%Y} al {cortes[-1]:%d/%m/%Y} · "
           "CNBV y documentos de cada operadora", supuestos=True)

    n_t1 = int(df["Tier"].str.startswith("Tier 1").sum())
    n_t2 = int(df["Tier"].str.startswith("Tier 2").sum())
    indep = df[df["Casa de bolsa hermana"] == "No"]
    tarjetas([
        ("Operadoras analizadas", f"{len(u.metricas)}", f"{len(u.sin_datos)} sin cifras"),
        ("Tier 1 · Tier 2", f"{n_t1} · {n_t2}", "Tier 1 ≥ 4.0 · Tier 2 ≥ 3.0"),
        ("Renta variable total", f"{df['RV (mdp)'].sum():,.0f}", "millones de pesos"),
        ("Bolsa de comisión", f"{df['Bolsa mín. (mdp)'].sum():,.0f}–{df['Bolsa máx. (mdp)'].sum():,.0f}",
         "mdp al año, todas las operadoras"),
        ("Sin casa de bolsa hermana", f"{len(indep)}", "elegibles para Tier 1"),
    ])

    seccion("Calificación por operadora",
            "Ponderación de bolsa, independencia, ajuste, recurrencia, headroom y fricción (1 a 5).")
    f1, f2 = st.columns([2, 3], vertical_alignment="bottom")
    filtro = f1.segmented_control("Mostrar", ["Todas", "Sin casa de bolsa hermana", "Tier 1 y 2"],
                                  default="Todas", key="filtro_resumen", label_visibility="collapsed")
    vista = df
    if filtro == "Sin casa de bolsa hermana":
        vista = df[df["Casa de bolsa hermana"] == "No"]
    elif filtro == "Tier 1 y 2":
        vista = df[df["Tier"].str.startswith(("Tier 1", "Tier 2"))]
    f2.markdown(" ".join(badge(f"{t} · {sum(vista['Tier'].str.startswith(t))}", c)
                         for t, c in (("Tier 1", "t1"), ("Tier 2", "t2"), ("Tier 3", "t3"))),
                unsafe_allow_html=True)

    alto = 35 * len(vista) + 40
    graf, tabla = st.columns([4, 6], gap="large")
    with graf:
        g = vista.sort_values("Calificación")
        tier_base = g["Tier"].str.slice(0, 6)
        fig = go.Figure(go.Bar(
            x=g["Calificación"], y=g["Operadora"], orientation="h",
            marker=dict(color=[COLOR_TIER.get(t, COLOR_TIER["Tier 3"]) for t in tier_base], cornerradius=4),
            text=[f"{v:.2f}" for v in g["Calificación"]], textposition="outside", cliponaxis=False,
            textfont=dict(color=TEXTO, size=11),
            customdata=g[["Tier", "RV (mdp)", "Bolsa mín. (mdp)", "Bolsa máx. (mdp)"]].values,
            hovertemplate="<b>%{y}</b><br>Calificación %{x:.2f} · %{customdata[0]}<br>RV %{customdata[1]:,.0f} mdp"
                          "<br>Bolsa %{customdata[2]:,.1f}–%{customdata[3]:,.1f} mdp<extra></extra>"))
        for x in (prm.tier2_min, prm.tier1_min):
            fig.add_vline(x=x, line=dict(color="#B9A9C9", width=1, dash="dot"))
        fig.update_xaxes(range=[1, 5.4], dtick=1)
        fig.update_yaxes(tickfont=dict(color=TEXTO, size=11.5))
        fig.update_layout(bargap=0.35)
        st.plotly_chart(estilo(fig, alto), use_container_width=True, config={"displayModeBar": False})
    with tabla:
        tab = pd.DataFrame({
            "Operadora": vista["Operadora"], "Tier": vista["Tier"], "Calificación": vista["Calificación"],
            "RV (mdp)": vista["RV (mdp)"],
            "Bolsa (mdp)": [f"{a:,.1f}–{b:,.1f}" for a, b in zip(vista["Bolsa mín. (mdp)"], vista["Bolsa máx. (mdp)"])],
            "CB hermana": vista["Casa de bolsa hermana"]})
        ev = st.dataframe(
            tab, hide_index=True, use_container_width=True, on_select="rerun",
            selection_mode="single-row", key=f"ranking_{st.session_state.get('ranking_n', 0)}",
            height=alto, row_height=35,
            column_config={
                "Operadora": st.column_config.TextColumn(width="medium"),
                "Calificación": st.column_config.ProgressColumn(min_value=1, max_value=5, format="%.2f", width="small"),
                "RV (mdp)": st.column_config.NumberColumn(format="%,.0f", width="small"),
                "Bolsa (mdp)": st.column_config.TextColumn(width="small"),
                "CB hermana": st.column_config.TextColumn(width="small"),
            })
        st.caption("Selecciona un renglón para abrir la ficha de la operadora. Bolsa en mdp al año.")
        if ev and ev.selection.rows:
            st.session_state["op"] = vista.iloc[ev.selection.rows[0]]["clave"]
            # Nueva llave: al volver al Panorama la tabla aparece sin selección (si no, rebotaría).
            st.session_state["ranking_n"] = st.session_state.get("ranking_n", 0) + 1
            st.switch_page(PAGINAS["operadora"])

    seccion("Mapa de exposición", "Cada punto es un fondo: tamaño de su renta variable contra su peso en la cartera.")
    pts = V.puntos_dispersion(u, prm)
    if len(pts):
        fig = px.scatter(pts, x="Exposición RV (mdp)", y="% RV", size="Bolsa (mdp)", log_x=True, size_max=36,
                         hover_name="Operadora", hover_data={"Fondo": True, "Bolsa (mdp)": ":,.2f",
                                                             "Exposición RV (mdp)": ":,.0f", "% RV": ":.0f"})
        fig.update_traces(marker=dict(color=SERIE_RV, opacity=0.55, line=dict(color="#FFFFFF", width=1)))
        fig.update_yaxes(range=[-5, 105], title="% de renta variable")
        fig.update_xaxes(title="Exposición a renta variable (mdp, escala logarítmica)")
        st.plotly_chart(estilo(fig, 420), use_container_width=True, config={"displayModeBar": False})
        st.caption(T.NOTA_BURBUJA)

    with st.expander("Tabla completa con los seis criterios"):
        st.dataframe(df.drop(columns=["clave"]), hide_index=True, use_container_width=True, column_config={
            "% RV": COL_PCT, "% RV en directo": COL_PCT, "Rotación medida (% expos.)": COL_PCT,
            "Activos netos (mdp)": COL_MDP, "RV (mdp)": COL_MDP, "Bolsa mín. (mdp)": COL_MDP, "Bolsa máx. (mdp)": COL_MDP,
            "Ingreso esperado máx. (mdp) (e)": st.column_config.NumberColumn(format="%,.2f"),
            "Rotación media": st.column_config.NumberColumn(format="%.2fx"),
            "Calificación": st.column_config.ProgressColumn(min_value=1, max_value=5, format="%.2f")})
    if u.sin_datos:
        with st.expander(f"Operadoras sin cifras ({len(u.sin_datos)})"):
            st.dataframe(pd.DataFrame([{"Operadora": k, "Motivo": v} for k, v in sorted(u.sin_datos.items())]),
                         hide_index=True, use_container_width=True)
    st.download_button("Descargar comparativo (HTML)", icon=":material/download:",
                       data=render_comparativo(list(u.metricas.values()), prm,
                                               [max(m.corte for m in u.metricas.values()).isoformat()]),
                       file_name="comparativo.html", mime="text/html")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _noticias(emisora: str, nombre: str):
    from radar.noticias import noticias

    return noticias(emisora, nombre)


def _tab_que_enviarle(m):
    from radar.core.contenido import plan_contenido
    from radar.noticias import consulta, url_busqueda

    plan = plan_contenido(m)
    st.markdown('<div class="pc-sub">Research, noticias e ideas sugeridos a partir de su cartera: qué emisoras pesan '
                'más, qué compró o vendió entre los dos últimos cortes (en títulos, sin efecto precio) y cómo reparte '
                'su renta variable y su renta fija.</div>', unsafe_allow_html=True)
    izq, der = st.columns([2, 3], gap="large")
    with izq:
        seccion("Perfil")
        st.markdown('<ul class="pc-lista">' + "".join(f"<li>{p}</li>" for p in plan.perfil) + "</ul>",
                    unsafe_allow_html=True)
        st.download_button("Descargar plan (Markdown)", plan.markdown(m.nombre), icon=":material/description:",
                           file_name=f"que_enviarle_{m.clave}_{m.corte.isoformat()}.md", mime="text/markdown")
    with der:
        seccion("Temas y material sugerido")
        if not plan.temas:
            st.info("Sin temas sugeridos para este corte.")
        for t in plan.temas:
            st.markdown(f'<div class="pc-tema"><div class="t">{t.titulo}</div>'
                        f'<div class="r"><span>Por qué:</span> {t.por_que}</div>'
                        f'<div class="r"><span>Qué enviar:</span> {t.que_enviar}</div></div>', unsafe_allow_html=True)

    seccion("Emisoras clave", "Las de mayor peso en su renta variable y qué hizo con ellas.")
    df = pd.DataFrame([{
        "Emisora": e.emisora, "Nombre": e.nombre, "Sector": e.sector, "Mercado": e.mercado,
        "Peso en su RV": e.peso_rv, "Monto (mdp)": e.monto / 1e6, "Fondos": e.fondos, "Movimiento": e.movimiento,
        "Cambio en títulos": e.cambio_titulos, "Noticias": url_busqueda(consulta(e.emisora, e.nombre)),
    } for e in plan.emisoras])
    if len(df):
        st.dataframe(df, hide_index=True, use_container_width=True, column_config={
            "Monto (mdp)": COL_MDP, "Cambio en títulos": COL_PCT,
            "Peso en su RV": st.column_config.ProgressColumn(format="percent", min_value=0,
                                                             max_value=float(df["Peso en su RV"].max() or 1)),
            "Noticias": st.column_config.LinkColumn("Noticias", display_text="Ver noticias")})
    if plan.salidas:
        st.markdown("**Vendió por completo:** " + ", ".join(
            f"{e.emisora} ({-e.monto_movimiento / 1e6:,.1f} mdp)" for e in plan.salidas))

    con_noticias = [e for e in plan.emisoras if e.mercado in ("México", "SIC")
                    and not e.nombre.startswith("[") and not e.sector.startswith("ETF")][:6]
    if con_noticias:
        seccion("Noticias recientes", "Encabezados de los últimos 14 días de sus principales emisoras. "
                                      "Verificar la nota original antes de reenviarla.")
        for tab, e in zip(st.tabs([e.emisora for e in con_noticias]), con_noticias):
            with tab:
                notas = _noticias(e.emisora, e.nombre)
                st.markdown(f'<div class="pc-sub"><b>{e.nombre}</b> · {e.sector} · {e.peso_rv:.1%} de su renta '
                            f'variable</div>', unsafe_allow_html=True)
                for n in notas:
                    fecha = n.fecha.strftime("%d/%m/%Y") if n.fecha else ""
                    st.markdown(f'<div class="pc-nota"><a href="{n.liga}" target="_blank">{n.titulo}</a>'
                                f'<div class="f">{n.fuente} · {fecha}</div></div>', unsafe_allow_html=True)
                if not notas:
                    st.caption("Sin noticias recientes o servicio no disponible.")
                st.link_button("Más noticias", url_busqueda(consulta(e.emisora, e.nombre)), icon=":material/open_in_new:")


def pagina_operadora():
    u, prm = universo()
    titulo("Ficha de operadora", "Operadoras", "Elige una operadora o ábrela desde el Panorama.", supuestos=True)
    op = _operadora_actual(u, etiqueta=False)
    m = u.metricas[op]
    q = m.calificacion(prm)
    lo, hi = m.bolsa_banda(prm)
    hermana = m.perfil.casa_de_bolsa_hermana if m.perfil else None
    txt_h = "Sí" if hermana else ("No" if hermana is False else POR_CONFIRMAR)
    insignias = badge_tier(q.tier + (" provisional" if q.provisional else ""))
    insignias += badge("Casa de bolsa hermana: " + txt_h, "alerta" if hermana else "ok" if hermana is False else "neutro")
    if q.veto:
        insignias += badge("Veto", "alerta")
    st.markdown(
        f'<div class="pc-ficha"><div><div class="nombre">{m.nombre}</div>'
        f'<div class="meta">Corte {m.corte:%d/%m/%Y} · {V.fuente_de(op)} · {len(m.fondos)} fondos analizados</div>'
        f'<div style="margin-top:10px">{insignias}</div></div>'
        f'<div class="score"><div class="n">{q.total:.2f}</div><div class="de">calificación de 5</div></div></div>',
        unsafe_allow_html=True)

    an = m.activo_neto
    rot, medida = m.rotacion_ponderada()
    tarjetas([
        ("Activos netos", mdp(an / 1e6, 0), "millones de pesos"),
        ("Renta variable", mdp(m.exposicion_rv / 1e6, 0), f"{m.exposicion_rv / an:.1%} de los activos" if an else ""),
        ("Bolsa de comisión", f"{lo / 1e6:,.1f}–{hi / 1e6:,.1f}", "mdp al año"),
        ("Rotación media", f"{rot:.2f}x", "medida" if medida else "supuesta (e)"),
        ("Headroom RV", mdp(m.headroom / 1e6, 0), "mdp de espacio en su régimen"),
    ], principal=2)

    tabs = st.tabs(["Resumen", "Qué enviarle", "Fondos", "Posiciones", "One-pager"], key="tabs_operadora")
    with tabs[0]:
        c1, c2 = st.columns([1, 1], gap="large")
        with c1:
            seccion("Composición de los activos")
            vals = [m.exposicion_rv / 1e6, m.monto_rf / 1e6, m.monto_efe / 1e6]
            d1, d2 = st.columns([1, 1], vertical_alignment="center")
            with d1:
                st.plotly_chart(dona(["Renta variable", "Renta fija", "Efectivo y reportos"], vals,
                                     [SERIE_RV, SERIE_RF, SERIE_EFE], f"{an / 1e6:,.0f}<br>mdp", "mdp"),
                                use_container_width=True, config={"displayModeBar": False})
            with d2:
                leyenda([(SERIE_RV, "Renta variable", f"{vals[0] / sum(vals):.0%}" if sum(vals) else "—"),
                         (SERIE_RF, "Renta fija", f"{vals[1] / sum(vals):.0%}" if sum(vals) else "—"),
                         (SERIE_EFE, "Efectivo y reportos", f"{vals[2] / sum(vals):.0%}" if sum(vals) else "—")])
        with c2:
            seccion("Cómo se forma la calificación", "Puntos de 1 a 5 por criterio; entre paréntesis, su peso.")
            crit = [("Bolsa (30%)", q.bolsa), ("Independencia (25%)", q.independencia), ("Ajuste (20%)", q.ajuste),
                    ("Recurrencia (10%)", q.recurrencia), ("Headroom y momentum (10%)", q.headroom),
                    ("Fricción (5%) (e)", q.friccion)]
            fig = go.Figure(go.Bar(
                x=[v for _, v in crit][::-1], y=[c for c, _ in crit][::-1], orientation="h",
                marker=dict(color=SERIE_RV, cornerradius=4), text=[f"{v:.1f}" for _, v in crit][::-1],
                textposition="outside", cliponaxis=False, textfont=dict(color=TEXTO),
                hovertemplate="%{y}: %{x:.1f}<extra></extra>"))
            fig.update_xaxes(range=[0, 5.5], dtick=1)
            st.plotly_chart(estilo(fig, 250), use_container_width=True, config={"displayModeBar": False})
        if q.provisional:
            st.info("Calificación provisional: menos de la mitad de su renta variable tiene rotación medida. "
                    "Se vuelve definitiva con el siguiente corte mensual.", icon=":material/info:")
        if m.perfil and m.perfil.evidencia_casa_de_bolsa:
            with st.expander("Evidencia sobre casa de bolsa hermana y distribuidoras"):
                st.write(m.perfil.evidencia_casa_de_bolsa)
    with tabs[1]:
        _tab_que_enviarle(m)
    with tabs[2]:
        st.dataframe(V.tabla_fondos(m), hide_index=True, use_container_width=True, column_config={
            "% RV": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
            "% RF": COL_PCT, "% Efectivo": COL_PCT, "Activos netos (mdp)": COL_MDP, "RV (mdp)": COL_MDP,
            "RF (mdp)": COL_MDP, "Máx. RV régimen": COL_PCT, "Headroom (mdp)": COL_MDP,
            "En fondos hermanos (mdp)": COL_MDP})
        st.caption("Para ver las posiciones de un fondo, abre la página Fondo.")
    with tabs[3]:
        t1, t2 = st.columns(2, gap="large")
        for col, tit, df in ((t1, T.TITULO_TOP_RV, V.top_rv(m)), (t2, T.TITULO_TOP_RF, V.top_rf(m))):
            with col:
                seccion(tit)
                if len(df):
                    st.dataframe(df, hide_index=True, use_container_width=True, column_config={
                        "Monto (mdp)": COL_MDP,
                        "Peso en la clase": st.column_config.ProgressColumn(
                            format="percent", min_value=0, max_value=float(df["Peso en la clase"].max()))})
                else:
                    st.info(T.SIN_POSICIONES)
    with tabs[4]:
        html = render_operadora(m, prm)
        st.download_button("Descargar one-pager (HTML)", html, icon=":material/download:",
                           file_name=f"{op}_{m.corte.isoformat()}.html", mime="text/html")
        st.components.v1.html(html, height=1100, scrolling=True)


def pagina_fondo():
    u, prm = universo()
    titulo("Detalle", "Fondo", supuestos=True)
    c1, c2 = st.columns(2)
    with c1:
        op = _operadora_actual(u)
    m = u.metricas[op]
    fondos = {f.clave: f for f in m.fondos + m.excluidos_fdf}
    orden = sorted(fondos, key=lambda k: -fondos[k].activo_neto)
    clave = c2.selectbox("Fondo", orden, format_func=lambda k: f"{k} · {fondos[k].nombre_corto or fondos[k].categoria_regulatoria or ''}",
                         key=f"sel_fondo_{op}")
    f = fondos[clave]
    insignias = badge(f.categoria_regulatoria or "Sin categoría")
    if f.es_fondo_de_fondos:
        insignias += badge("Fondo de fondos · excluido de cifras", "alerta")
    insignias += badge("Rotación medida" if f.rotacion.medida else "Rotación supuesta (e)",
                       "ok" if f.rotacion.medida else "neutro")
    st.markdown(
        f'<div class="pc-ficha"><div><div class="nombre">{f.clave} · {f.nombre_corto or f.nombre_legal or ""}</div>'
        f'<div class="meta">{m.nombre} · corte {f.fecha_corte:%d/%m/%Y} · {f.cartera.procedencia.cita()}</div>'
        f'<div style="margin-top:10px">{insignias}</div></div></div>', unsafe_allow_html=True)
    lo, hi = f.bolsa_banda(prm)
    tarjetas([
        ("Activo neto", mdp(f.activo_neto / 1e6), "estimado (e)" if f.activo_neto_estimado else "publicado (mdp)"),
        ("Renta variable", f"{f.pct_rv:.1%}", f"{f.exposicion_rv / 1e6:,.1f} mdp"),
        ("Régimen RV", "—" if f.rv_max is None else f"{(f.rv_min or 0):.0%}–{f.rv_max:.0%}",
         "prospecto / DICI" if f.rv_max is not None else POR_CONFIRMAR),
        ("Rotación", f"{f.rotacion.minimo:.2f}x–{f.rotacion.maximo:.2f}x", "piso–techo anual"),
        ("Bolsa de comisión", f"{lo / 1e6:,.2f}–{hi / 1e6:,.2f}", "mdp al año"),
    ], principal=None)

    nombres = ["Posiciones", "Rotación", "DICI", "Historia"]
    tabs = st.tabs(nombres, key="tabs_fondo")
    with tabs[0]:
        st.dataframe(V.posiciones(f), hide_index=True, use_container_width=True,
                     column_config={"Valor (mdp)": st.column_config.NumberColumn(format="%,.2f"), "% cartera": COL_PCT,
                                    "Títulos": st.column_config.NumberColumn(format="%,.0f")})
    with tabs[1]:
        tr = V.tramos_rotacion(f)
        if len(tr):
            st.dataframe(tr, hide_index=True, use_container_width=True)
        else:
            st.info("Sin dos cortes comparables: se usa la banda supuesta (e).", icon=":material/info:")
    with tabs[2]:
        if f.dici:
            st.dataframe(pd.DataFrame([{"Serie": s.serie, "Posibles adquirentes": s.posibles_adquirentes,
                                        "Monto mínimo": s.monto_minimo,
                                        "Comisión de administración": s.comision_administracion,
                                        "Costo total": s.costo_total} for s in f.dici.series]),
                         hide_index=True, use_container_width=True,
                         column_config={"Comisión de administración": COL_PCT, "Costo total": COL_PCT})
            st.markdown(f'<ul class="pc-lista"><li>Liquidez: {f.dici.liquidez or "—"}</li>'
                        f'<li>Liquidación: {f.dici.plazo_liquidacion or "—"}</li>'
                        f'<li>Límite de recompra: {f.dici.limite_recompra or "—"}</li>'
                        f'<li>Índice de referencia: {f.dici.indice_referencia or "—"}</li></ul>', unsafe_allow_html=True)
        else:
            st.info("Esta operadora no tiene DICI integrado: régimen y comisiones quedan [POR CONFIRMAR].",
                    icon=":material/info:")
    with tabs[3]:
        h = V.historia(f)
        if len(h) > 1:
            fig = go.Figure(go.Scatter(x=h["Corte"], y=h["Activo neto (mdp)"], mode="lines+markers",
                                       line=dict(color=SERIE_RV, width=2), marker=dict(size=8),
                                       hovertemplate="%{x}<br>%{y:,.1f} mdp<extra></extra>"))
            fig.update_yaxes(title="Activo neto (mdp)")
            st.plotly_chart(estilo(fig, 320), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Solo hay un corte de este fondo.", icon=":material/info:")
    for n in f.discrepancias:
        st.warning(f"‡ {n}")
    if f.notas:
        with st.expander("Notas del fondo"):
            for n in f.notas:
                st.markdown(f"- {n}")


def pagina_estado():
    titulo("Operación", "Estado de los datos",
           "Resultado de la última actualización automática por operadora, documentos y conciliaciones.")
    store = Store(ruta_db())
    try:
        est = V.estado(store)
        docs = V.documentos(store)
        if len(est):
            con_aviso = est["Mensaje"].str.contains("aviso", case=False)
            ok = (est["Estado"] == "OK")
            tarjetas([
                ("Operadoras sin error", f"{int(ok.sum())} de {len(est)}", "en la última corrida"),
                ("Con avisos", f"{int((ok & con_aviso).sum())}", "datos parciales o sitio sin respuesta"),
                ("Documentos guardados", f"{int(docs['Documentos'].sum()) if len(docs) else 0:,}", "PDF y Excel fechados"),
                ("Última ejecución", est["Última ejecución"].max(), "hora de la Ciudad de México"),
            ])
        tabs = st.tabs(["Operadoras", "ETFs pendientes", "Documentos", "Conciliaciones"], key="tabs_estado")
        with tabs[0]:
            if len(est):
                est = est.copy()
                est["Estado"] = [("Error" if e != "OK" else "Con avisos" if "aviso" in msj.lower() else "OK")
                                 for e, msj in zip(est["Estado"], est["Mensaje"])]
                st.dataframe(est.drop(columns=["clave"]), hide_index=True, use_container_width=True,
                             column_config={"Mensaje": st.column_config.TextColumn(width="large")})
        with tabs[1]:
            st.caption("Regla: un ETF se clasifica por su subyacente y nunca se adivina. Mientras una operadora "
                       "tenga ETFs fuera del diccionario, sus cifras no se calculan.")
            pend = V.etfs_pendientes(store)
            if len(pend):
                st.dataframe(pend, hide_index=True, use_container_width=True, column_config={"Monto (mdp)": COL_MDP})
                st.download_button("Descargar CSV", pend.to_csv(index=False).encode("utf-8"), "etfs_pendientes.csv",
                                   "text/csv", icon=":material/download:")
            else:
                st.success("Sin ETFs pendientes.", icon=":material/check_circle:")
        with tabs[2]:
            st.dataframe(docs, hide_index=True, use_container_width=True)
        with tabs[3]:
            conc = V.conciliaciones(store)
            if len(conc):
                st.dataframe(conc, hide_index=True, use_container_width=True,
                             column_config={"Diferencia": COL_PCT, "Monto A (mdp)": COL_MDP, "Monto B (mdp)": COL_MDP})
            else:
                st.info("Sin conciliaciones registradas.")
    finally:
        store.cerrar()


def pagina_metodologia():
    from radar.core import contenido as C
    from radar.core.clasificacion import version_diccionario_etfs

    titulo("Referencia", "Metodología", "Cómo se construyen las cifras, la calificación y las sugerencias.")
    prm = cargar_parametros()
    tabs = st.tabs(["Modelo", "Calificación", "Qué enviarle", "Fuentes y actualización"], key="tabs_metodo")
    with tabs[0]:
        for par in T.METODOLOGIA:
            st.markdown(par.format(version_etfs=version_diccionario_etfs(), tol=f"{prm.tolerancia_cuadre:.1%}",
                                   n_cortes=prm.cortes_para_cifra, max_meses=f"{prm.max_meses_par:g}",
                                   umbral=f"{prm.umbral_discrepancia:.0%}"))
    with tabs[1]:
        for n in T.NOTAS_COMPARATIVO:
            st.markdown("- " + n.format(t1=f"{prm.tier1_min:.1f}", t2=f"{prm.tier2_min:.1f}",
                                        t1_menos=f"{prm.tier1_min - 0.1:.1f}",
                                        esc_bolsa=" / ".join(f"{x / 1e6:,.0f}" for x in prm.bolsa_cortes),
                                        esc_rot=" / ".join(f"{x:g}" for x in prm.rotacion_cortes),
                                        esc_head=" / ".join(f"{x:.0%}" for x in prm.headroom_cortes)))
    with tabs[2]:
        st.markdown(
            f"- **Emisoras clave:** las de más monto en su renta variable (acciones México, SIC y ETFs), con su peso, "
            f"cuántos fondos la tienen y su movimiento entre los dos últimos cortes, medido en **títulos** (sin efecto "
            f"precio): Nueva, Aumentó o Redujo (±{C.UMBRAL_MOVIMIENTO:.0%}), Estable o Salida. Si un corte agrupa ese "
            "tipo de valor en un renglón sin emisora, se marca «Sin desglose» y no cuenta como compra ni venta.\n"
            f"- **Temas:** México si pesa ≥ {C.UMBRAL_MEXICO:.0%} de su RV; SIC ≥ {C.UMBRAL_SIC:.0%}; ETFs ≥ "
            f"{C.UMBRAL_ETF:.0%}; un sector ≥ {C.UMBRAL_SECTOR:.0%} de su RV con sector conocido; FIBRAs ≥ "
            f"{C.UMBRAL_FIBRAS:.0%}; compras y ventas recientes; renta fija por segmento (≥ {C.UMBRAL_SEGMENTO_RF:.0%} "
            f"de su RF) cuando la RF pesa ≥ {C.UMBRAL_RF:.0%} de sus activos; espacio de régimen ≥ "
            f"{C.UMBRAL_HEADROOM:.0%} de su RV; casa de bolsa hermana.\n"
            "- **Sectores y nombres:** catálogo propio en radar/core/datos/emisoras.csv (solo emisoras inequívocas); "
            "ETFs con la descripción del diccionario de ETFs. Lo demás sale «Sin sector» / [POR CONFIRMAR].\n"
            "- **Noticias:** encabezados de Google Noticias (últimos 14 días) buscados por nombre de la emisora y "
            "términos bursátiles; se consultan en vivo y no entran al one-pager.")
    with tabs[3]:
        st.markdown(
            "- **CNBV:** R7 (cartera mensual de todos los fondos) y R1 (activo neto), con ~45 días de rezago.\n"
            "- **Operadoras con documentos propios:** carteras de Finaccess, Multiva y Vinci Compass; DICI y "
            "prospectos de BlackRock, SURA, Principal, Franklin Templeton, Skandia y Nafinsa.\n"
            "- **Actualización:** automática en los servidores de GitHub, lunes a viernes a las 07:17 y 15:17 "
            "(CDMX). Solo se publica una versión nueva cuando llega un documento nuevo.\n"
            "- **Supuestos (e):** comisiones, captura, probabilidad de alta y fricción en config/parametros.toml.")


# ------------------------------------------------------------------ navegación
PAGINAS = {
    "resumen": st.Page(pagina_resumen, title="Panorama", icon=":material/dashboard:", default=True),
    "operadora": st.Page(pagina_operadora, title="Operadora", icon=":material/account_balance:", url_path="operadora"),
    "fondo": st.Page(pagina_fondo, title="Fondo", icon=":material/pie_chart:", url_path="fondo"),
    "estado": st.Page(pagina_estado, title="Estado de los datos", icon=":material/monitor_heart:", url_path="estado"),
    "metodologia": st.Page(pagina_metodologia, title="Metodología", icon=":material/menu_book:", url_path="metodologia"),
}
actual = st.navigation(list(PAGINAS.values()), position="hidden")
encabezado()
with st.container(horizontal=True, key="pc_nav", gap="small"):
    for p in PAGINAS.values():
        st.page_link(p)
actual.run()
pie()
