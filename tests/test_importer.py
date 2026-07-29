"""Tests de hub/importer.py — no existía cobertura para este módulo
(auditoría 2026-07-28, hardening previo a usar export/import para migrar
una instalación real de un despacho a otra máquina). Cubre el hallazgo
principal (extracción de tar sin protección contra path traversal /
symlinks — el paquete puede venir de otra máquina o de un archivo subido
a mano, no es un origen confiable por default) más el resto del
comportamiento de reescritura que no tenía ningún test."""
from __future__ import annotations

import io
import tarfile

import pytest
import yaml

from hub import exporter, importer


def _make_agent_dir(tmp_path, extra_config: dict | None = None):
    agent_dir = tmp_path / "origen" / "agente-test"
    agent_dir.mkdir(parents=True)

    config = {
        "agent": {"name": "agente-test", "port": 9000, "install_path": str(agent_dir)},
        "security": {"level": 2, "token": "token-secreto-real"},
        "knowledge": [str(agent_dir / "data" / "knowledge")],
    }
    if extra_config:
        config.update(extra_config)
    (agent_dir / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (agent_dir / "engine.py").write_text("VERSION = 1\n", encoding="utf-8")
    data_dir = agent_dir / "data" / "knowledge"
    data_dir.mkdir(parents=True)
    (data_dir / "principios.yaml").write_text("contenido: real", encoding="utf-8")

    return agent_dir


def _package(tmp_path, extra_config: dict | None = None) -> bytes:
    agent_dir = _make_agent_dir(tmp_path, extra_config)
    return exporter.export_agent("agente-test", agent_dir)


def _tamper(pkg: bytes, mutate) -> bytes:
    """Reconstruye el .tar.gz aplicando `mutate(tar_in, tar_out)` — para
    los tests que necesitan un paquete manipulado a mano (traversal,
    symlinks) que export_agent() nunca produciría por su cuenta."""
    out = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(pkg), mode="r:gz") as tar_in, \
         tarfile.open(fileobj=out, mode="w:gz") as tar_out:
        mutate(tar_in, tar_out)
    out.seek(0)
    return out.read()


def _add_evil_member(tar_out: tarfile.TarFile, name: str, content: bytes = b"pwned") -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(content)
    tar_out.addfile(info, io.BytesIO(content))


def test_rechaza_manifest_no_agentos_v1(tmp_path):
    pkg = _package(tmp_path)

    def mutate(tar_in, tar_out):
        for member in tar_in.getmembers():
            if member.name == "manifest.json":
                _add_evil_member(tar_out, "manifest.json", b'{"format": "otra-cosa"}')
            elif member.isfile():
                tar_out.addfile(member, tar_in.extractfile(member))
            else:
                tar_out.addfile(member)

    tampered = _tamper(pkg, mutate)
    dest = tmp_path / "destino"
    dest.mkdir()

    with pytest.raises(ValueError, match="agentos-v1"):
        importer.import_agent(tampered, dest, assign_port=9100, existing_names=set())


def test_rechaza_manifest_faltante(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz"):
        pass  # tar vacío, sin manifest.json
    dest = tmp_path / "destino"
    dest.mkdir()

    with pytest.raises(ValueError, match="manifest.json"):
        importer.import_agent(buf.getvalue(), dest, assign_port=9100, existing_names=set())


def test_rechaza_path_traversal_con_dotdot(tmp_path):
    pkg = _package(tmp_path)

    def mutate(tar_in, tar_out):
        for member in tar_in.getmembers():
            if member.isfile():
                tar_out.addfile(member, tar_in.extractfile(member))
            else:
                tar_out.addfile(member)
        _add_evil_member(tar_out, "agent/../../fuera_del_agente.txt")

    tampered = _tamper(pkg, mutate)
    dest = tmp_path / "destino"
    dest.mkdir()

    with pytest.raises(ValueError, match="traversal"):
        importer.import_agent(tampered, dest, assign_port=9100, existing_names=set())

    # No debe haber escrito nada fuera del directorio destino intentado.
    assert not (tmp_path / "fuera_del_agente.txt").exists()
    assert not (dest / "fuera_del_agente.txt").exists()


def test_rechaza_path_absoluta_dentro_del_prefijo(tmp_path):
    """`agent/` + una ruta absoluta no se concatena en pathlib -- reemplaza
    por completo al directorio destino. Mismo bug de fondo que el ../,
    vector de ataque distinto."""
    pkg = _package(tmp_path)
    objetivo = str(tmp_path / "otro_lugar" / "evil.txt")
    # tarfile normaliza nombres con "/" -- forzamos uno que sobreviva la
    # normalización interna usando una ruta con drive letter en Windows
    # o una absoluta POSIX, según corresponda, dentro del campo `name`.
    nombre_absoluto = "agent/" + objetivo.replace("\\", "/")

    def mutate(tar_in, tar_out):
        for member in tar_in.getmembers():
            if member.isfile():
                tar_out.addfile(member, tar_in.extractfile(member))
            else:
                tar_out.addfile(member)
        _add_evil_member(tar_out, nombre_absoluto)

    tampered = _tamper(pkg, mutate)
    dest = tmp_path / "destino"
    dest.mkdir()

    with pytest.raises(ValueError):
        importer.import_agent(tampered, dest, assign_port=9100, existing_names=set())
    assert not (tmp_path / "otro_lugar").exists()


def test_rechaza_symlink(tmp_path):
    pkg = _package(tmp_path)

    def mutate(tar_in, tar_out):
        for member in tar_in.getmembers():
            if member.isfile():
                tar_out.addfile(member, tar_in.extractfile(member))
            else:
                tar_out.addfile(member)
        link = tarfile.TarInfo(name="agent/link_malicioso")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tar_out.addfile(link)

    tampered = _tamper(pkg, mutate)
    dest = tmp_path / "destino"
    dest.mkdir()

    with pytest.raises(ValueError, match="symlink"):
        importer.import_agent(tampered, dest, assign_port=9100, existing_names=set())


def test_colision_de_nombre_agrega_sufijo(tmp_path):
    pkg = _package(tmp_path)
    dest = tmp_path / "destino"
    dest.mkdir()

    name, _, _ = importer.import_agent(pkg, dest, assign_port=9100, existing_names=set())
    assert name == "agente-test"

    name2, agent_dir2, _ = importer.import_agent(pkg, dest, assign_port=9101, existing_names={name})
    assert name2 == "agente-test-2"
    assert agent_dir2 == dest / "agente-test-2"


def test_reescribe_port_install_path_workspace(tmp_path):
    pkg = _package(tmp_path)
    dest = tmp_path / "destino"
    dest.mkdir()

    name, agent_dir, cfg = importer.import_agent(pkg, dest, assign_port=9200, existing_names=set())

    assert cfg["agent"]["port"] == 9200
    assert cfg["agent"]["install_path"] == str(agent_dir)
    assert cfg["agent"]["workspace"] == str(agent_dir / "workspace")
    assert cfg["agent"]["status"] == "offline"


def test_token_de_seguridad_es_nuevo_y_no_vacio(tmp_path):
    """El token original nunca viaja (exporter lo elimina, ver test_exporter.py) —
    lo que importa acá es que el importado siempre tenga uno propio."""
    pkg = _package(tmp_path)
    dest = tmp_path / "destino"
    dest.mkdir()

    _, _, cfg = importer.import_agent(pkg, dest, assign_port=9300, existing_names=set())

    token = cfg["security"]["token"]
    assert token
    assert token != "token-secreto-real"


def test_knowledge_path_inexistente_se_reapunta_a_data_knowledge(tmp_path):
    pkg = _package(tmp_path, extra_config={"knowledge": ["/ruta/que/no/existe/en/este/equipo"]})
    dest = tmp_path / "destino"
    dest.mkdir()

    _, agent_dir, cfg = importer.import_agent(pkg, dest, assign_port=9400, existing_names=set())

    assert cfg["knowledge"] == [str(agent_dir / "data" / "knowledge")]


def test_knowledge_path_existente_se_conserva(tmp_path):
    """Comportamiento actual documentado explícitamente: si el path
    'coincidentemente' existe en la máquina destino (poco probable pero
    posible), se deja tal cual -- no hay lógica adicional que lo valide
    más allá de existencia."""
    ruta_que_sí_existe = tmp_path  # cualquier dir real sirve
    pkg = _package(tmp_path, extra_config={"knowledge": [str(ruta_que_sí_existe)]})
    dest = tmp_path / "destino"
    dest.mkdir()

    _, _, cfg = importer.import_agent(pkg, dest, assign_port=9500, existing_names=set())

    assert cfg["knowledge"] == [str(ruta_que_sí_existe)]


def test_run_scripts_tienen_el_puerto_asignado(tmp_path):
    pkg = _package(tmp_path)
    dest = tmp_path / "destino"
    dest.mkdir()

    _, agent_dir, _ = importer.import_agent(pkg, dest, assign_port=9600, existing_names=set())

    assert "9600" in (agent_dir / "run.sh").read_text(encoding="utf-8")
    assert "9600" in (agent_dir / "run.bat").read_text(encoding="utf-8")


def test_falla_si_el_directorio_destino_ya_existe(tmp_path):
    pkg = _package(tmp_path)
    dest = tmp_path / "destino"
    dest.mkdir()

    importer.import_agent(pkg, dest, assign_port=9700, existing_names=set())
    # Mismo nombre Y mismo destino no debería pisar lo que ya está --
    # existing_names vacío simula no habérselo pasado al Hub (no debería
    # pasar en producción, pero el import no debe confiar solo en eso).
    with pytest.raises(FileExistsError):
        importer.import_agent(pkg, dest, assign_port=9701, existing_names=set())
