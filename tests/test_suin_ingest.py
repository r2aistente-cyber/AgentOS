"""Tests de scripts/suin_ingest.py — parseo y guardado, sin red real
(los tests de red real de verdad contra suin-juriscol.gov.co / datos.gov.co
se hicieron a mano durante el desarrollo, ver Pieza 2 del plan)."""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_guardar_incluye_cabecera_de_metadatos(tmp_path):
    from scripts import suin_ingest

    with patch.object(suin_ingest, "KNOWLEDGE_DIR", tmp_path):
        dest = suin_ingest.guardar(
            area="laboral",
            nombre_archivo="codigo-sustantivo-trabajo",
            titulo="Código Sustantivo del Trabajo",
            ruta="Decretos/1874133",
            texto="Artículo 1. Objeto...",
        )

    content = dest.read_text(encoding="utf-8")
    assert dest == tmp_path / "laboral" / "codigo-sustantivo-trabajo.md"
    assert "# Código Sustantivo del Trabajo" in content
    assert "Decretos/1874133" in content
    assert "Artículo 1. Objeto..." in content


def test_guardar_crea_carpeta_del_area_si_no_existe(tmp_path):
    from scripts import suin_ingest

    with patch.object(suin_ingest, "KNOWLEDGE_DIR", tmp_path):
        suin_ingest.guardar("penal", "test", "Test", "Leyes/1", "contenido")

    assert (tmp_path / "penal").is_dir()


def test_descargar_norma_filtra_ruido_de_navegacion(monkeypatch):
    """El HTML real de SUIN-Juriscol mezcla ruido de navegación (cursos,
    diccionario RAE, etc.) con el texto normativo — se filtra por línea."""
    from scripts import suin_ingest

    html = """
    <html><body>
    <p>A-Z</p>
    <p>Diccionario</p>
    <p>Curso SUIN-Juriscol</p>
    <p>Inscripciones abiertas</p>
    <p>LEY 9 DE 1979</p>
    <p>Artículo 1. Objeto de la ley.</p>
    </body></html>
    """

    class _FakeResponse:
        charset_encoding = "utf-8"
        apparent_encoding = "utf-8"
        text = html

        def raise_for_status(self):
            pass

    class _FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, headers=None):
            return _FakeResponse()

    monkeypatch.setattr(suin_ingest.httpx, "Client", lambda **kw: _FakeClient())

    texto = suin_ingest.descargar_norma("Leyes/1564714")

    assert "A-Z" not in texto
    assert "Diccionario" not in texto
    assert "Curso SUIN-Juriscol" not in texto
    assert "Inscripciones abiertas" not in texto
    assert "LEY 9 DE 1979" in texto
    assert "Artículo 1. Objeto de la ley." in texto


def test_texto_muy_corto_no_crashea_solo_avisa(tmp_path, capsys, monkeypatch):
    """Un texto sospechosamente corto debe avisar por stderr, no fallar."""
    from scripts import suin_ingest

    monkeypatch.setattr(suin_ingest, "descargar_norma", lambda ruta: "corto")
    monkeypatch.setattr(suin_ingest, "KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["suin_ingest", "--area", "civil", "--ruta", "Leyes/1", "--titulo", "T"],
    )

    suin_ingest.main()

    captured = capsys.readouterr()
    assert "sospechosamente corto" in captured.err
    assert (tmp_path / "civil" / "t.md").exists()
