"""Cliente HTTP conservador: User-Agent de navegador, rate limit, reintentos con
backoff y caché en disco (válida el mismo día calendario)."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class ErrorDescarga(RuntimeError):
    pass


@dataclass(frozen=True)
class Respuesta:
    url: str
    status: int
    content_type: str
    contenido: bytes
    desde_cache: bool

    @property
    def texto(self) -> str:
        return self.contenido.decode("utf-8", errors="replace")

    @property
    def es_pdf(self) -> bool:
        return self.contenido[:5] == b"%PDF-"


class Cliente:
    def __init__(
        self,
        dir_cache: Path,
        req_por_seg: float = 1.5,
        timeout: float = 45,
        reintentos: int = 4,
        refrescar: bool = False,
    ) -> None:
        self.dir_cache = dir_cache
        self.dir_cache.mkdir(parents=True, exist_ok=True)
        self.intervalo = 1.0 / req_por_seg
        self.timeout = timeout
        self.reintentos = reintentos
        self.refrescar = refrescar
        self._ultimo = 0.0
        self._sesion = requests.Session()
        self._sesion.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/pdf,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
            }
        )

    def _rutas(self, url: str) -> tuple[Path, Path]:
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return self.dir_cache / f"{h}.bin", self.dir_cache / f"{h}.json"

    def get(self, url: str) -> Respuesta:
        cuerpo, meta = self._rutas(url)
        hoy = date.today().isoformat()
        if not self.refrescar and cuerpo.exists() and meta.exists():
            m = json.loads(meta.read_text(encoding="utf-8"))
            if m.get("fecha") == hoy:
                return Respuesta(url, m["status"], m["content_type"], cuerpo.read_bytes(), True)

        ultimo_error: Exception | None = None
        for intento in range(self.reintentos):
            espera = self.intervalo - (time.monotonic() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            try:
                r = self._sesion.get(url, timeout=self.timeout, allow_redirects=True)
                self._ultimo = time.monotonic()
                if r.status_code in (429, 500, 502, 503, 504):
                    raise ErrorDescarga(f"HTTP {r.status_code}")
                resp = Respuesta(url, r.status_code, r.headers.get("Content-Type", ""), r.content, False)
                if r.status_code == 200:
                    cuerpo.write_bytes(r.content)
                    meta.write_text(
                        json.dumps(
                            {"url": url, "fecha": hoy, "status": r.status_code, "content_type": resp.content_type},
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                return resp
            except (requests.RequestException, ErrorDescarga) as e:
                self._ultimo = time.monotonic()
                ultimo_error = e
                time.sleep(2**intento)
        raise ErrorDescarga(f"No se pudo descargar {url}: {ultimo_error}")

    def post_json(self, url: str, datos: dict, encabezados: dict | None = None) -> dict:
        """POST con cuerpo JSON y respuesta JSON (APIs públicas que usa la propia página,
        sin sesión ni login). Mismo rate limit, reintentos y caché del día que `get`."""
        cuerpo_req = json.dumps(datos, sort_keys=True, ensure_ascii=False)
        cuerpo, meta = self._rutas(url + "\n" + cuerpo_req)
        hoy = date.today().isoformat()
        if not self.refrescar and cuerpo.exists() and meta.exists():
            if json.loads(meta.read_text(encoding="utf-8")).get("fecha") == hoy:
                return json.loads(cuerpo.read_bytes())
        ultimo_error: Exception | None = None
        for intento in range(self.reintentos):
            espera = self.intervalo - (time.monotonic() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            try:
                r = self._sesion.post(url, json=datos, headers=encabezados or {}, timeout=self.timeout)
                self._ultimo = time.monotonic()
                if r.status_code in (429, 500, 502, 503, 504):
                    raise ErrorDescarga(f"HTTP {r.status_code}")
                if r.status_code != 200:
                    raise ErrorDescarga(f"HTTP {r.status_code} en {url}")
                res = r.json()
                cuerpo.write_bytes(r.content)
                meta.write_text(json.dumps({"url": url, "fecha": hoy, "status": 200}, ensure_ascii=False),
                                encoding="utf-8")
                return res
            except (requests.RequestException, ValueError, ErrorDescarga) as e:
                self._ultimo = time.monotonic()
                ultimo_error = e
                if "HTTP 4" in str(e):
                    break
                time.sleep(2**intento)
        raise ErrorDescarga(f"No se pudo consultar {url}: {ultimo_error}")
