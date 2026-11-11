"""Orquestación: descubrir -> descargar (fechado) -> parsear -> validar -> store -> métricas."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

from radar.adapters import adaptador
from radar.adapters.base import DocARevisar, ErrorParseo
from radar.config import Parametros, dir_datos
from radar.core.clasificacion import clasificar_cartera
from radar.core.metricas import MetricasOperadora, dici_para, metricas_fondo
from radar.core.modelo import ADMINISTRADO, Cartera, Documento, FondoDescubierto, Procedencia
from radar.adapters.cnbv_generico import AdaptadorCnbvConDici
from radar.fuentes import cnbv
from radar.core.validacion import validar_cuadre
from radar.red import Cliente, ErrorDescarga
from radar.store.db import Store


class ErrorCorte(ValueError):
    pass


class EtfsPendientes(ValueError):
    """La operadora tiene ETFs sin clasificar: no se calculan sus cifras (no se adivina)."""

    def __init__(self, operadora: str, pendientes: dict[str, float]):
        self.pendientes = pendientes
        lista = ", ".join(f"{k} ({v / 1e6:,.1f} mdp)" for k, v in sorted(pendientes.items(), key=lambda x: -x[1])[:15])
        super().__init__(
            f"{operadora}: {len(pendientes)} ETF sin clasificar en radar/core/datos/etfs.csv "
            f"({sum(pendientes.values()) / 1e6:,.1f} mdp): {lista}{' …' if len(pendientes) > 15 else ''}"
        )


def etfs_sin_clasificar(c: Cartera) -> dict[str, float]:
    from radar.core.clasificacion import canonica, diccionario_etfs
    from radar.core.modelo import Categoria as Cat

    d = diccionario_etfs()
    out: dict[str, float] = {}
    for p in c.posiciones:
        if p.categoria in (Cat.ETF_EXTRANJERO, Cat.ETF_LOCAL) and not p.es_agregado and canonica(p.emisora) not in d:
            out[canonica(p.emisora)] = out.get(canonica(p.emisora), 0.0) + p.valor_razonable
    return out


def cliente(refrescar: bool = False) -> Cliente:
    return Cliente(dir_datos() / "cache" / "http", refrescar=refrescar)


def _seguro(nombre: str) -> str:
    return re.sub(r"[^A-Za-z0-9._+-]+", "_", nombre)


def descubrir(operadora: str, cli: Cliente) -> tuple[list[FondoDescubierto], list[DocARevisar]]:
    return adaptador(operadora).descubrir(cli)


def descargar(operadora: str, store: Store, cli: Cliente, log=print) -> list[str]:
    """Descarga todo lo descubierto y lo registra fechado por su contenido (sha256)."""
    ad = adaptador(operadora)
    if isinstance(ad, AdaptadorCnbvConDici):
        # Híbrido: el universo es el de la CNBV; aquí solo se bajan DICI y prospectos. Los DICI
        # cambian ~1 vez al mes y son cientos de MB: se revisan cada DIAS_REVISION_DICI días.
        marca = dir_datos() / "cache" / "revision_dici" / f"{operadora}.txt"
        if not cli.refrescar and marca.exists() and _dici_al_dia(operadora, store):
            previa = json.loads(marca.read_text(encoding="utf-8"))
            ultima = date.fromisoformat(previa["fecha"])
            if (date.today() - ultima).days < DIAS_REVISION_DICI:
                log(f"  DICI revisados el {ultima}; siguiente revisión en "
                    f"{DIAS_REVISION_DICI - (date.today() - ultima).days} día(s)")
                return list(previa.get("avisos", []))  # mismos avisos: el estado no cambia en falso
        marca.parent.mkdir(parents=True, exist_ok=True)
        try:
            fondos, docs = ad.descubrir(cli, claves_cnbv(operadora, ad.clave_cnbv, store))
        except (ErrorDescarga, ErrorParseo, KeyError, ValueError) as e:
            # El DICI complementa a la CNBV: si el sitio falla, se avisa y se sigue con R7/R1.
            return [f"No se pudieron listar los DICI ({type(e).__name__}: {e})"]
    else:
        fondos, docs = ad.descubrir(cli)
        store.guardar_universo(operadora, fondos)
    avisos: list[str] = []
    faltan: dict[str, list[str]] = {}
    hoy = date.today()
    for d in docs:
        r, motivo = None, "sin URL publicada"
        especial = ad.bajar(cli, d) if isinstance(ad, AdaptadorCnbvConDici) else None
        for url in () if especial is not None else [u for u in d.urls if u]:
            try:
                x = cli.get(url)
            except ErrorDescarga as e:
                motivo = f"sin respuesta ({e})"
                continue
            if x.status == 200 and x.es_pdf:
                r = x
                break
            motivo = f"HTTP {x.status} / no es PDF"
        if especial is not None:
            r = especial if especial.es_pdf else None
            motivo = "la API no devolvió un PDF"
        if r is None:
            if d.opcional:
                faltan.setdefault(d.tipo, []).append(d.fondo_clave or "-")
            else:
                avisos.append(f"{d.fondo_clave or '-'} {d.tipo}: {motivo} ({' | '.join(d.urls)})")
            continue
        sha = hashlib.sha256(r.contenido).hexdigest()
        rel = Path("raw") / operadora / f"{sha[:12]}_{_seguro(d.nombre_archivo)}"
        ruta = dir_datos() / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if not ruta.exists():
            ruta.write_bytes(r.contenido)
        try:
            fecha = ad.fecha_documento(d.tipo, ruta)
        except ErrorParseo as e:
            avisos.append(f"{d.fondo_clave} {d.tipo}: fecha ilegible ({e})")
            fecha = None
        store.guardar_documento(Documento(sha, operadora, d.fondo_clave, d.tipo, d.url, rel.as_posix(),
                                          fecha, hoy, len(r.contenido)))
        log(f"  {d.fondo_clave or '-':8s} {d.tipo:18s} {fecha or 's/f'}  {d.nombre_archivo}")
    for tipo, claves in sorted(faltan.items()):
        if tipo == "dici":  # un prospecto faltante solo deja el régimen [POR CONFIRMAR]
            avisos.append(f"Sin DICI publicado ({len(claves)} de {sum(1 for d in docs if d.tipo == tipo)}): "
                          + ", ".join(sorted(claves)))
    if isinstance(ad, AdaptadorCnbvConDici):
        marca.write_text(json.dumps({"fecha": hoy.isoformat(), "avisos": avisos}, ensure_ascii=False),
                         encoding="utf-8")
    return avisos


#: Cada cuántos días se vuelven a revisar los DICI y prospectos de las operadoras híbridas.
DIAS_REVISION_DICI = 7


def _dici_al_dia(operadora: str, store: Store) -> bool:
    """El DICI más reciente de cada fondo sigue en disco (si se perdió, hay que volver a bajar)."""
    ultimos: dict[str, Documento] = {}
    for d in store.documentos(operadora):
        if d.tipo == "dici" and (d.fondo_clave not in ultimos or _ultimo([ultimos[d.fondo_clave], d]) is d):
            ultimos[d.fondo_clave] = d
    return bool(ultimos) and all((dir_datos() / d.archivo).exists() for d in ultimos.values())


def claves_cnbv(operadora: str, cve: str | None, store: Store) -> list[str]:
    """Fondos de la operadora: los del universo guardado más los del R7 más reciente."""
    r7 = _ultimo(store.documentos(cnbv.OPERADORA, "cnbv_r7"))
    claves: set[str] = {f.clave for f in store.universo(operadora)}
    if r7 is not None and cve:
        alias = alias_fondos(operadora)
        claves |= {alias.get(k, k) for k in (cnbv._texto(f.datos.get("fondo")) for f in _minfo(r7)
                                           if cnbv._texto(f.datos.get("operadora")) == cve)}
    return sorted(claves - {""})


def descargar_cnbv(store: Store, cli: Cliente, log=print) -> list[str]:
    """Descarga los R1/R7 vigentes de la CNBV (fuente transversal) y los guarda fechados."""
    avisos: list[str] = []
    hoy = date.today()
    for tipo, url in cnbv.urls_vigentes(hoy):
        try:
            r = cli.get(url)
        except Exception as e:  # noqa: BLE001 - un archivo caído no detiene a los demás
            avisos.append(f"CNBV {tipo}: no se pudo descargar ({type(e).__name__}) {url}")
            continue
        if r.status != 200 or r.contenido[:2] != b"PK":
            avisos.append(f"CNBV {tipo}: HTTP {r.status} / no es libro de Excel ({url})")
            continue
        sha = cnbv.sha(r.contenido)
        nombre = url.rsplit("/", 1)[1]
        rel = Path("raw") / cnbv.OPERADORA / f"{sha[:12]}_{nombre}"
        ruta = dir_datos() / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if not ruta.exists():
            ruta.write_bytes(r.contenido)
        fecha = cnbv.fecha_documento(tipo, ruta)
        n_ops = len({cnbv._texto(f.datos.get("operadora")) for f in _minfo_ruta(ruta, sha)})
        if n_ops < 10:
            avisos.append(f"CNBV {nombre}: solo trae {n_ops} operadora(s) (archivo parcial); "
                          "las demás no tienen corte para ese periodo")
        store.guardar_documento(Documento(sha, cnbv.OPERADORA, None, tipo, url, rel.as_posix(), fecha, hoy,
                                          len(r.contenido)))
        log(f"  CNBV     {tipo:18s} {fecha or 's/f'}  {nombre}")
    return avisos


_MINFO: dict[str, list] = {}


def _minfo_ruta(ruta: Path, clave: str) -> list:
    if clave not in _MINFO:
        _MINFO[clave] = cnbv.leer_minfo(ruta)
    return _MINFO[clave]


def _minfo(d: Documento) -> list:
    if d.doc_id not in _MINFO:
        _MINFO[d.doc_id] = cnbv.leer_minfo(dir_datos() / d.archivo)
    return _MINFO[d.doc_id]


def alias_fondos(operadora: str) -> dict[str, str]:
    import tomllib

    from radar.config import RAIZ

    ruta = RAIZ / "config" / "alias_fondos.toml"
    if not ruta.exists():
        return {}
    return dict(tomllib.loads(ruta.read_text(encoding="utf-8")).get(operadora, {}))


def _aplicar_alias(c: Cartera, alias: dict[str, str]) -> Cartera:
    c.fondo_clave = alias.get(c.fondo_clave, c.fondo_clave)
    for p in c.posiciones:
        if p.fondo_subyacente:
            p.fondo_subyacente = alias.get(p.fondo_subyacente, p.fondo_subyacente)
            p.emisora = alias.get(p.emisora, p.emisora)
    return c


def _posible_alias(c: Cartera, propias: dict[str, Cartera]) -> tuple[str, float] | None:
    """Fondo de la operadora con >= 90 % de traslape de instrumentos (mín. 3)."""
    k = {p.clave_instrumento for p in c.posiciones if not p.es_agregado and p.clase != "EFE"}
    if len(k) < 3:
        return None
    mejor = None
    for clave, o in propias.items():
        ko = {p.clave_instrumento for p in o.posiciones if not p.es_agregado and p.clase != "EFE"}
        t = len(k & ko) / len(k)
        if t >= 0.9 and (mejor is None or t > mejor[1]):
            mejor = (clave, t)
    return mejor


def _dif(a: float, b: float) -> float:
    return (a - b) / b if b else 0.0


def _ingestar_r1(operadora: str, cve: str, store: Store) -> dict[tuple[int, int], date]:
    fechas: dict[tuple[int, int], date] = {}
    alias = alias_fondos(operadora)
    for d in store.documentos(cnbv.OPERADORA, "cnbv_r1"):
        for an in cnbv.activos_r1(_minfo(d), cve, d):
            store.guardar_activo_neto(operadora, alias.get(an.fondo, an.fondo), an.fecha, an.activo_neto, an.procedencia)
            fechas[(an.fecha.year, an.fecha.month)] = max(an.fecha, fechas.get((an.fecha.year, an.fecha.month), an.fecha))
    return fechas


def _aplicar_activo_oficial(c: Cartera, store: Store) -> None:
    """Activo neto oficial (CNBV R1) del mismo día ±3: sustituye al estimado; si la
    operadora sí publica activo neto, queda la conciliación."""
    of = store.activo_neto_oficial(c.operadora, c.fondo_clave, c.fecha_corte)
    if of is None:
        return
    an, proc = of
    store.guardar_conciliacion(
        c.operadora, c.fondo_clave, c.fecha_corte,
        "activo neto (R7)" if c.tipo_doc == "cnbv_r7" else "activo neto (cartera de la operadora)",
        (_FUENTE[c.tipo_doc], c.activo_neto if not c.activo_neto_estimado else c.total_cartera, c.procedencia.cita()),
        ("CNBV R1 activo neto", an, proc.cita()),
    )
    if c.activo_neto_estimado:
        c.activo_neto = an
        c.activo_neto_estimado = False
        c.notas = [n for n in c.notas if "Activo neto no publicado" not in n]
        c.notas.append(f"Activo neto oficial CNBV R1: {proc.cita()}.")


_FUENTE = {"cartera_mensual": "Cartera de la operadora", "cartera_diaria": "Cartera de la operadora",
           "cnbv_r7": "CNBV R7 suma de posiciones"}


def _ingestar_r7(operadora: str, cve: str, store: Store, fechas: dict[tuple[int, int], date], log) -> None:
    previas = {c.fondo_clave: c for c in store.carteras(operadora) if c.tipo_doc in ("cartera_mensual", "cartera_diaria")}
    universo = {f.clave: f for f in store.universo(operadora)}
    nuevos: list[FondoDescubierto] = []
    alias = alias_fondos(operadora)
    carteras_r7 = [_aplicar_alias(c, alias) for d in store.documentos(cnbv.OPERADORA, "cnbv_r7")
                   for c in cnbv.carteras_r7(_minfo(d), operadora, cve, d, fechas)]
    pendientes: dict[str, float] = {}
    for c in carteras_r7:
        for k, v in etfs_sin_clasificar(c).items():
            pendientes[k] = pendientes.get(k, 0.0) + v
    if pendientes:
        raise EtfsPendientes(operadora, pendientes)
    for c in carteras_r7:
        clasificar_cartera(c)
        ref = previas.get(c.fondo_clave)
        if ref is not None:
            c.nombre_legal, c.categoria, c.nombre_corto, c.tipo_fondo = (
                ref.nombre_legal, ref.categoria, ref.nombre_corto, ref.tipo_fondo)
        if c.fondo_clave not in universo:
            nota = "Solo en CNBV: no aparece en el sitio de la operadora"
            if previas and (pa := _posible_alias(c, previas)):
                nota += f" (¿alias de {pa[0]}? traslape {pa[1]:.0%}; ver config/alias_fondos.toml)"
                log(f"  AVISO posible alias {c.fondo_clave} -> {pa[0]} ({pa[1]:.0%})")
            nuevos.append(FondoDescubierto(c.fondo_clave, "", ADMINISTRADO, {}, nota))
        _aplicar_activo_oficial(c, store)
        mismo_mes = store.mensual_del_mes(operadora, c.fondo_clave, c.fecha_corte)
        if mismo_mes:
            op = next(x for x in store.carteras(operadora, date.fromisoformat(mismo_mes)))
            store.guardar_conciliacion(
                operadora, c.fondo_clave, op.fecha_corte, "total de cartera",
                ("Cartera de la operadora", op.total_cartera, op.procedencia.cita()),
                ("CNBV R7 suma de posiciones", c.total_cartera, c.procedencia.cita()),
            )
            log(f"  CNBV R7 {c.fondo_clave:8s} {c.fecha_corte} concilia contra la cartera de la operadora")
            continue
        if store.guardar_cartera(c):
            log(f"  CNBV R7 {c.fondo_clave:8s} {c.fecha_corte} {len(c.posiciones):3d} posiciones")
    if nuevos:
        store.guardar_universo(operadora, nuevos)


def _referencia_r7(ad, operadora: str, c: Cartera, store: Store) -> Cartera | None:
    """R7 más reciente del mismo fondo con fecha <= corte (desglosa lo que la
    operadora agrupa). Solo se usa para inferir el subyacente de agregados de ETFs."""
    if not ad.clave_cnbv or not any(p.es_agregado for p in c.posiciones):
        return None
    mejor = None
    for d in store.documentos(cnbv.OPERADORA, "cnbv_r7"):
        for r in cnbv.carteras_r7(_minfo(d), operadora, ad.clave_cnbv, d):
            if r.fondo_clave == c.fondo_clave and r.fecha_corte <= c.fecha_corte and (
                    mejor is None or r.fecha_corte > mejor.fecha_corte):
                mejor = r
    return mejor


def _ultimo(docs: list[Documento]) -> Documento | None:
    return max(docs, key=lambda d: (d.fecha_doc or date.min, d.descargado, d.doc_id)) if docs else None


def parsear(operadora: str, store: Store, prm: Parametros, log=print) -> list[str]:
    """Re-parsea TODOS los documentos guardados. Falla si una cartera no cuadra."""
    avisos: list[str] = []
    ad = adaptador(operadora)
    docs = store.documentos(operadora)
    nombres = {f.clave: f.nombre_comercial for f in store.universo(operadora)}
    ultimas: dict[str, Cartera] = {}
    if ad.clave_cnbv:
        store.borrar_derivados_cnbv(operadora)
    fechas_r1 = _ingestar_r1(operadora, ad.clave_cnbv, store) if ad.clave_cnbv else {}
    for d in docs:
        if not d.tipo.startswith("cartera"):
            continue
        try:
            c = ad.parsear_cartera(dir_datos() / d.archivo, d)
        except ErrorParseo as e:
            raise ErrorParseo(f"{operadora}/{d.fondo_clave} {d.archivo}: {e}") from e
        validar_cuadre(c, prm.tolerancia_cuadre)
        clasificar_cartera(c, _referencia_r7(ad, operadora, c, store))
        c.nombre_corto = nombres.get(c.fondo_clave, "") or c.nombre_corto
        _aplicar_activo_oficial(c, store)
        store.guardar_cartera(c)
        if c.fondo_clave not in ultimas or c.fecha_corte > ultimas[c.fondo_clave].fecha_corte:
            ultimas[c.fondo_clave] = c
        log(f"  cartera {c.fondo_clave:8s} {c.fecha_corte} {len(c.posiciones):3d} posiciones  cuadra")

    confirmar = getattr(ad, "confirmar_universo", None)
    if confirmar:
        gen = _ultimo([d for d in docs if d.tipo == "prospecto_generico"])
        if gen is None:
            raise ErrorParseo(f"{operadora}: falta el prospecto genérico para confirmar el universo")
        store.guardar_universo(operadora, confirmar(store.universo(operadora), ultimas, dir_datos() / gen.archivo))

    if ad.clave_cnbv:
        _ingestar_r7(operadora, ad.clave_cnbv, store, fechas_r1, log)

    for d in docs:
        if d.tipo != "dici":
            continue
        p = _ultimo([x for x in docs if x.tipo == "prospecto" and x.fondo_clave == d.fondo_clave])
        if p is not None and not (dir_datos() / p.archivo).exists():
            p = None
        if not (dir_datos() / d.archivo).exists():
            # Los DICI de las híbridas no se versionan: en un clon nuevo se conserva lo ya
            # parseado en el store y el PDF vuelve a bajar en el siguiente fetch.
            avisos.append(f"DICI {d.fondo_clave}: falta el archivo {d.archivo} (se conserva lo guardado)")
            continue
        try:
            dici = ad.parsear_dici(dir_datos() / d.archivo, d, (dir_datos() / p.archivo, p) if p else None)
        except ErrorParseo as e:
            if isinstance(ad, AdaptadorCnbvConDici):
                # En un híbrido el DICI complementa la cartera de la CNBV: se avisa y se sigue.
                avisos.append(f"DICI {d.fondo_clave} ({Path(d.archivo).name}): {e}")
                log(f"  AVISO DICI {d.fondo_clave}: {e}")
                continue
            raise ErrorParseo(f"{operadora}/{d.fondo_clave} {d.archivo}: {e}") from e
        if not dici.fondo_clave:
            dici.fondo_clave = d.fondo_clave or ""
        store.guardar_dici(dici)
        log(f"  dici    {dici.fondo_clave:8s} {dici.fecha_doc} {len(dici.series)} series")
    store.guardar_perfil(ad.perfil(store.dicis(operadora)))
    return avisos


def corte_a_lo_mas(store: Store, operadora: str, fecha: str) -> date:
    """Último corte mensual <= fecha (para comparar operadoras que publican con
    distinto rezago)."""
    lim = date.fromisoformat(fecha)
    cortes = [c for c in store.cortes(operadora, solo_mensuales=True) if c <= lim]
    if not cortes:
        raise ErrorCorte(f"{operadora}: no hay cortes mensuales hasta {lim}")
    return cortes[-1]


def resolver_corte(store: Store, operadora: str, corte: str) -> date:
    cortes = store.cortes(operadora, solo_mensuales=True)
    if not cortes:
        raise ErrorCorte(f"{operadora}: no hay cortes mensuales en el store; corre primero 'fetch'")
    if corte == "latest":
        return cortes[-1]
    pedido = date.fromisoformat(corte)
    mismos = [c for c in cortes if (c.year, c.month) == (pedido.year, pedido.month) and c <= pedido]
    if not mismos:
        raise ErrorCorte(
            f"{operadora}: no hay corte para {pedido}. Disponibles: {', '.join(c.isoformat() for c in cortes)}"
        )
    return mismos[-1]


def construir_metricas(operadora: str, corte: date, store: Store, prm: Parametros) -> MetricasOperadora:
    ad = adaptador(operadora)
    universo = {f.clave: f for f in store.universo(operadora)}
    todas = store.carteras(operadora)
    dicis = store.dicis(operadora)
    por_fondo: dict[str, list[Cartera]] = {}
    for c in todas:
        por_fondo.setdefault(c.fondo_clave, []).append(c)

    def al_corte(clave: str, f: date) -> Cartera | None:
        cand = [c for c in por_fondo.get(clave, []) if c.fecha_corte <= f]
        return max(cand, key=lambda c: c.fecha_corte) if cand else None

    hermanas = {k: c for k in por_fondo if (c := al_corte(k, corte)) is not None}
    fondos, fdf = [], []
    for clave in sorted(por_fondo):
        u = universo.get(clave)
        if u is not None and u.estatus != ADMINISTRADO:
            continue
        del_mes = [x for x in por_fondo[clave]
                   if x.tipo_doc in ("cartera_mensual", "cnbv_r7")
                   and (x.fecha_corte.year, x.fecha_corte.month) == (corte.year, corte.month)]
        c = min(del_mes, key=lambda x: x.tipo_doc != "cartera_mensual") if del_mes else None
        if c is None:
            continue
        m = metricas_fondo(c, hermanas, por_fondo[clave], dici_para(dicis, clave, corte), prm,
                           store.conciliaciones(operadora, clave))
        (fdf if m.es_fondo_de_fondos else fondos).append(m)

    con_corte = {f.clave for f in fondos + fdf}
    sin_cartera = []
    for clave in sorted(set(por_fondo) | {k for k, u in universo.items() if u.estatus == ADMINISTRADO}):
        u = universo.get(clave)
        if clave in con_corte or (u is not None and u.estatus != ADMINISTRADO):
            continue
        ult = max((c.fecha_corte for c in por_fondo.get(clave, [])), default=None)
        partes = [x.strip().rstrip(".") for x in ((u.nota if u else ""), (f"último corte disponible {ult.isoformat()}" if ult else "")) if x]
        sin_cartera.append((clave, "; ".join(partes)))

    # Calibración del activo neto estimado: total de cartera vs activo neto oficial
    # en el último corte en que la CNBV publicó ambos.
    calib = None
    pares = [k for k in store.conciliaciones(operadora)
             if k["concepto"] == "activo neto (R7)" and k["monto_b"]
             and k["fecha"] <= corte.isoformat()]
    if pares:
        f_ult = max(k["fecha"] for k in pares)
        difs = [(k["monto_a"] - k["monto_b"]) / k["monto_b"] for k in pares if k["fecha"] == f_ult]
        calib = (date.fromisoformat(f_ult), min(difs), max(difs))

    no_disp = sorted((f.clave, f.estatus + (f": {f.nota}" if f.nota else ""))
                     for f in universo.values() if f.estatus != ADMINISTRADO)
    cortes = store.cortes(operadora, solo_mensuales=True)
    previos = [c for c in cortes if c < corte]
    previo = previos[-1] if previos else None
    an_previo = an_comparable = None
    if previo:
        # Momentum con los MISMOS fondos en ambos cortes (si no, entra o sale un fondo
        # completo y se confunde con flujo).
        previas = {c.fondo_clave: c for c in todas if c.fecha_corte == previo}
        comunes = [f for f in fondos if f.clave in previas]
        if comunes:
            an_previo = sum(previas[f.clave].activo_neto for f in comunes) or None
            an_comparable = sum(f.activo_neto for f in comunes) or None
    return MetricasOperadora(operadora, ad.nombre, corte, store.perfil(operadora), fondos, fdf,
                             no_disp, previo, an_previo, an_comparable, sin_cartera=sin_cartera, calibracion=calib)
