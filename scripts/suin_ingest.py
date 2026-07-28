"""Ingesta de normas desde SUIN-Juriscol (https://www.suin-juriscol.gov.co) hacia
knowledge/<area>/ para que el agente r2-legal las indexe (RAG).

Dos pasos:
  1. catalogo(): consulta el dataset abierto de datos.gov.co (Socrata, id
     `fiev-nid6`) para saber qué normas existen — metadatos (tipo, número, año,
     sector, vigencia, materia), NO el texto.
  2. descargar_norma(ruta): trae el HTML público de la norma en
     suin-juriscol.gov.co y extrae su texto legible. El sitio no tiene un
     endpoint de descarga real: su botón "Descargar en Word" es JS puro que
     envuelve `document.documentElement.outerHTML` como blob .doc en el propio
     navegador (ver <script>exportToWord()</script> en la página) — el texto
     completo ya está en el HTML de la página, no hay nada más que pedir.

Uso:
    python -m scripts.suin_ingest --area laboral --ruta Decretos/1874133 \
        --titulo "Código Sustantivo del Trabajo (Decreto 2663 de 1950)"

Nota de calidad: la extracción actual es texto de página completa (con algo de
ruido de navegación/cursos/índice ya filtrado por una lista de bloqueo simple,
no un parser específico del articulado) — suficiente para RAG por chunks, pero
el contenido jurídico debe ser revisado por Xavier o un abogado antes de
tratarse como autoritativo. Ver plan en C:\\Users\\xavier\\.claude\\plans\\
staged-crafting-taco.md, Pieza 2.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"

CATALOGO_URL = "https://www.datos.gov.co/resource/fiev-nid6.json"
SUIN_BASE = "https://www.suin-juriscol.gov.co"

# El certificado de suin-juriscol.gov.co no valida con el bundle de CAs
# estándar (cadena incompleta del lado del servidor — confirmado con
# `curl -k`, WebFetch falla con "unable to verify the first certificate").
# verify=False es deliberado y acotado a este dominio gubernamental conocido,
# no una práctica general para otros sitios.
_SUIN_VERIFY = False

# Ruido de navegación/marketing del sitio que no es parte del texto normativo
# (detectado a mano en una página de prueba real, Ley 9 de 1979).
_LINEAS_RUIDO = {
    "A-Z", "Diccionario", "X", "RAE", "Se abrirá en una nueva pestaña.",
    "Curso SUIN-Juriscol", "Inscripciones abiertas",
}


def catalogo(vigencia: str | None = "Vigente", materia_contains: str | None = None,
             tipo: str | None = None, limit: int = 50) -> list[dict]:
    """Consulta el catálogo estructurado (metadatos, no texto) de datos.gov.co."""
    where_parts = []
    if vigencia:
        where_parts.append(f"vigencia='{vigencia}'")
    if tipo:
        where_parts.append(f"tipo='{tipo}'")
    if materia_contains:
        where_parts.append(f"materia like '%{materia_contains}%'")

    params: dict[str, str | int] = {"$limit": limit}
    if where_parts:
        params["$where"] = " AND ".join(where_parts)

    resp = httpx.get(CATALOGO_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def descargar_norma(ruta: str | None = None, id_: str | None = None) -> str:
    """Trae `viewDocument.asp?ruta=<ruta>` (o `?id=<id_>` para normas sin
    una `ruta` amigable descubrible) y devuelve el texto legible."""
    query = f"ruta={ruta}" if ruta else f"id={id_}"
    url = f"{SUIN_BASE}/viewDocument.asp?{query}"
    with httpx.Client(verify=_SUIN_VERIFY, timeout=30, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (r2-legal-ingest)"})
        resp.raise_for_status()
        resp.encoding = resp.charset_encoding or resp.apparent_encoding or "utf-8"
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "header", "nav", "footer"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [ln for ln in text.splitlines() if ln.strip() and ln.strip() not in _LINEAS_RUIDO]
    return "\n".join(lines)


def guardar(area: str, nombre_archivo: str, titulo: str, texto: str,
            ruta: str | None = None, id_: str | None = None) -> Path:
    """Guarda en knowledge/<area>/<nombre_archivo>.md con cabecera de metadatos."""
    dest_dir = KNOWLEDGE_DIR / area
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{nombre_archivo}.md"
    query = f"ruta={ruta}" if ruta else f"id={id_}"
    header = (
        f"# {titulo}\n\n"
        f"Fuente: {SUIN_BASE}/viewDocument.asp?{query}\n"
        f"Descargado: {date.today().isoformat()}\n\n---\n\n"
    )
    dest.write_text(header + texto, encoding="utf-8")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", required=True,
                     help="civil|laboral|familia|penal|comercial|administrativo|tributario")
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--ruta", help='p. ej. "Decretos/1874133" o "Leyes/1663230"')
    grupo.add_argument("--id", dest="id_", help='p. ej. "1132325" — para normas sin ruta amigable')
    ap.add_argument("--titulo", required=True,
                     help='p. ej. "Código Sustantivo del Trabajo"')
    ap.add_argument("--nombre-archivo",
                     help="nombre de archivo sin extensión (por defecto, deriva del título)")
    args = ap.parse_args()

    nombre = args.nombre_archivo or re.sub(r"[^a-z0-9]+", "-", args.titulo.lower()).strip("-")
    texto = descargar_norma(ruta=args.ruta, id_=args.id_)
    if len(texto) < 200:
        print(f"AVISO: texto extraído sospechosamente corto ({len(texto)} caracteres) "
              "— revisar manualmente.", file=sys.stderr)
    dest = guardar(args.area, nombre, args.titulo, texto, ruta=args.ruta, id_=args.id_)
    print(f"Guardado: {dest} ({len(texto)} caracteres)")


if __name__ == "__main__":
    main()
