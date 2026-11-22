"""Pruebas de tools/base_tools/medios_tools.py (ingesta, ligeras, registro). Uso: python pruebas_medios.py
Usa carpetas temporales; no toca la carpeta de medios real. Las pruebas de FFmpeg se omiten si no está instalado."""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_config as config  # noqa: E402
from tools.base_tools import medios_tools as m  # noqa: E402
from tools import registry  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="pruebas_medios_"))
FUENTE = TMP / "disco_externo"
RAIZ = TMP / "Medios"
m._raiz = lambda: RAIZ
_get = config.get
_FIJOS = {"medios.fuentes_permitidas": [str(FUENTE)], "medios.sync.destino": "ID-DE-PRUEBA",
          "medios.sync.carpeta": "medios-ligeras", "medios.auto_ligeras": False}
config.get = lambda k, d=None: _FIJOS[k] if k in _FIJOS else _get(k, d)

resultados = []


def prueba(f):
    try:
        f()
        resultados.append((f.__name__, True, ""))
    except Exception:
        resultados.append((f.__name__, False, traceback.format_exc(limit=3)))
    return f


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def esperar(jid, t=300):
    ini = time.time()
    while m._JOBS[jid]["estado"] == "en curso":
        assert time.time() - ini < t, "el trabajo no terminó"
        time.sleep(0.1)
    return m._JOBS[jid]


def lanzar(fn, *a, **k):
    msg = fn(*a, **k)
    jid = re.search(r"trabajo (\w{8})", msg).group(1)
    return esperar(jid)


def archivos_de(carpeta):
    return sorted(p for p in Path(carpeta).rglob("*") if p.is_file())


def preparar():
    shutil.rmtree(FUENTE, ignore_errors=True)
    shutil.rmtree(RAIZ, ignore_errors=True)
    (FUENTE / "DCIM").mkdir(parents=True)
    for i in (1, 2, 3):
        (FUENTE / "DCIM" / f"C000{i}.MP4").write_bytes(os.urandom(300_000) + bytes([i]))
    (FUENTE / "DCIM" / "SIN_ELEGIR.MP4").write_bytes(os.urandom(1000))


def elegidos(*n):
    return [str(FUENTE / "DCIM" / f"C000{i}.MP4") for i in n]


@prueba
def nombres_invalidos_se_rechazan():
    for malo in ("..", "a/b", "a\\b", "CON", "x:y", "fin.", "", "  ", "a" * 81, "nul.txt"):
        try:
            m._limpio(malo, "proyecto")
        except ValueError:
            continue
        raise AssertionError(f"aceptó '{malo}'")
    assert m._limpio("Corto Final 2026", "proyecto") == "Corto Final 2026"


@prueba
def origen_solo_disco_externo():
    preparar()
    assert m._fuente_permitida(FUENTE / "DCIM")[0]
    assert not m._fuente_permitida(RAIZ / "originales")[0]
    assert not m._fuente_permitida(Path("/etc/passwd") if os.name != "nt" else Path("C:\\Windows\\win.ini"))[0]


@prueba
def plan_no_copia_nada():
    preparar()
    antes = archivos_de(TMP)
    plan = m.plan_ingesta("Corto", "Esc1", elegidos(1, 2))
    assert "No se ha copiado nada" in plan and "2 archivo" in plan
    assert archivos_de(TMP) == antes and not RAIZ.exists()


@prueba
def ingesta_copia_solo_lo_elegido_y_verifica():
    preparar()
    antes = {p.name: sha(p) for p in archivos_de(FUENTE)}
    j = lanzar(m.ingerir_archivos, "Corto", "Esc1", elegidos(1, 2))
    assert j["estado"] == "terminado" and j["hecho"] == 2 and not j["errores"], j
    dest = RAIZ / "originales" / "Corto" / "Esc1"
    assert sorted(p.name for p in dest.iterdir()) == ["C0001.MP4", "C0002.MP4"]        # C0003 y SIN_ELEGIR no se copian
    for n in ("C0001.MP4", "C0002.MP4"):
        assert sha(dest / n) == antes[n]
    assert {p.name: sha(p) for p in archivos_de(FUENTE)} == antes                       # origen intacto
    assert not list(dest.glob("*.part"))
    d = m._cargar("Corto")
    assert [c["nombre"] for c in d["clips"]] == ["C0001.MP4", "C0002.MP4"]
    assert all(c["estado"] == "copiado" and c["sha256"] == antes[c["nombre"]] for c in d["clips"])


@prueba
def repetir_es_idempotente():
    j = lanzar(m.ingerir_archivos, "Corto", "Esc1", elegidos(1, 2))
    assert j["ya_estaban"] == 2 and not j["errores"], j
    assert len(m._cargar("Corto")["clips"]) == 2


@prueba
def nombre_repetido_con_otro_contenido_no_sobrescribe():
    dest = RAIZ / "originales" / "Corto" / "Esc1"
    original = sha(dest / "C0001.MP4")
    otra = FUENTE / "otra_tarjeta"
    otra.mkdir()
    (otra / "C0001.MP4").write_bytes(os.urandom(5000))
    j = lanzar(m.ingerir_archivos, "Corto", "Esc1", [str(otra / "C0001.MP4")])
    assert j["estado"] == "terminado" and j["notas"], j
    assert sha(dest / "C0001.MP4") == original                                          # el original no se tocó
    nuevos = [p.name for p in dest.iterdir() if p.name.startswith("C0001_")]
    assert len(nuevos) == 1 and sha(dest / nuevos[0]) == sha(otra / "C0001.MP4")
    assert len(m._cargar("Corto")["clips"]) == 3


@prueba
def seleccion_invalida_no_copia_nada():
    preparar()
    for malos, motivo in (([str(FUENTE / "DCIM")], "archivo"), ([str(FUENTE / "no_existe.mp4")], "archivo"),
                          ([], "lista"), ([str(RAIZ / "x.mp4")], "carpeta de medios")):
        try:
            m.ingerir_archivos("Z", "E", malos)
        except ValueError as e:
            assert motivo in str(e), str(e)
            continue
        raise AssertionError(f"aceptó {malos}")
    assert not RAIZ.exists()


@prueba
def fallo_parcial_se_informa_y_continua():
    preparar()
    real = m._copiar_verificado

    def falla_en_2(src, dst):
        if src.name == "C0002.MP4":
            raise IOError("disco desconectado (simulado)")
        return real(src, dst)
    m._copiar_verificado = falla_en_2
    try:
        j = lanzar(m.ingerir_archivos, "Parcial", "E", elegidos(1, 2, 3))
    finally:
        m._copiar_verificado = real
    assert j["estado"] == "terminado con errores" and j["hecho"] == 2, j
    assert any("C0002" in e and "simulado" in e for e in j["errores"])
    nombres = [c["nombre"] for c in m._cargar("Parcial")["clips"]]
    assert nombres == ["C0001.MP4", "C0003.MP4"]                                        # el fallido NO figura como copiado


@prueba
def copia_corrupta_se_detecta_y_no_queda_rastro():
    preparar()
    real = m._sha256
    m._sha256 = lambda p: "0" * 64 if str(p).endswith(".part") else real(p)
    try:
        j = lanzar(m.ingerir_archivos, "Corrupto", "E", elegidos(1))
    finally:
        m._sha256 = real
    assert j["estado"] == "terminado con errores" and "no coincide" in j["errores"][0], j
    dest = RAIZ / "originales" / "Corrupto" / "E"
    assert not list(dest.iterdir())                                                      # ni .part ni destino
    assert m._cargar("Corrupto")["clips"] == []


@prueba
def no_hay_dos_operaciones_a_la_vez_en_un_proyecto():
    preparar()
    m._proyectos_ocupados.add("Ocupado")
    try:
        m.ingerir_archivos("Ocupado", "E", elegidos(1))
    except RuntimeError as e:
        assert "en curso" in str(e)
    else:
        raise AssertionError("permitió dos operaciones simultáneas")
    finally:
        m._proyectos_ocupados.discard("Ocupado")


@prueba
def confirmacion_requerida_solo_en_lo_que_escribe():
    assert registry.get("ingerir_archivos").requires_confirm is True
    for n in ("plan_ingesta", "explorar_disco", "listar_unidades", "estado_proyecto", "clips_proyecto"):
        assert registry.get(n).requires_confirm is False, n


@prueba
def explorar_lista_sin_modificar():
    preparar()
    out = m.explorar_disco(str(FUENTE / "DCIM"))
    assert "4 elementos" in out and "C0001.MP4" in out
    try:
        m.explorar_disco(str(RAIZ))
    except ValueError:
        pass
    else:
        raise AssertionError("dejó explorar la carpeta de medios")


@prueba
def estado_y_listado():
    preparar()
    lanzar(m.ingerir_archivos, "Corto", "Esc1", elegidos(1, 2, 3))
    assert "Corto" in m.listar_proyectos()
    e = m.estado_proyecto("Corto")
    assert "3 clips" in e and "Esc1" in e
    assert "C0001.MP4" in m.clips_proyecto("Corto", "Esc1")


@prueba
def escaneo_de_syncthing_se_pide_con_la_carpeta_del_proyecto():
    llamadas = []
    real = m._syncthing
    m._syncthing = lambda metodo, camino: llamadas.append((metodo, camino))
    try:
        assert m._pedir_escaneo("Mi Corto") == ""
    finally:
        m._syncthing = real
    assert llamadas == [("POST", "/rest/db/scan?folder=medios-ligeras&sub=Mi%20Corto")], llamadas


@prueba
def si_syncthing_falla_se_avisa_y_no_se_rompe():
    real = m._syncthing

    def cae(metodo, camino):
        raise RuntimeError("sin syncthing")
    m._syncthing = cae
    try:
        aviso = m._pedir_escaneo("X")
        estado = m._estado_sync()
    finally:
        m._syncthing = real
    assert "no pude pedir el escaneo" in aviso and "no pude consultar" in estado


@prueba
def veredicto_listo_lo_calcula_el_codigo():
    preparar()
    lanzar(m.ingerir_archivos, "Ver", "E", elegidos(1, 2))
    real = m._estado_sync
    try:
        m._estado_sync = lambda: "Sincronización con terminus: completa (100%)."
        assert "LISTO PARA EDITAR: NO" in m.estado_proyecto("Ver") and "faltan copias ligeras" in m.estado_proyecto("Ver")
        def todas(d):
            for c in d["clips"]:
                c["estado"] = "ligera_lista"
        m._mutar("Ver", todas)
        assert "LISTO PARA EDITAR: SI" in m.estado_proyecto("Ver")
        m._estado_sync = lambda: "Sincronización con terminus: 40%, faltan 5 MB."
        assert "NO (las ligeras aún no terminaron de llegar" in m.estado_proyecto("Ver")
        m._estado_sync = lambda: "Sincronización: no pude consultar Syncthing (X)."
        assert "no pude comprobar la sincronización" in m.estado_proyecto("Ver")
    finally:
        m._estado_sync = real
    m._mutar("Vacio", lambda d: None)
    assert "LISTO PARA EDITAR: NO (el proyecto no tiene clips)" in m.estado_proyecto("Vacio")


def hay_ffmpeg():
    try:
        m._ffbin("ffmpeg"), m._ffbin("ffprobe")
        return True
    except RuntimeError:
        return False


if hay_ffmpeg():
    def clip_de_prueba(ruta, seg=2, fps=25, extra=()):
        subprocess.run([m._ffbin("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size=1280x720:rate={fps}:duration={seg}",
                        "-f", "lavfi", "-i", f"sine=frequency=440:duration={seg}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", *extra, str(ruta)], check=True)

    @prueba
    def ingesta_encadena_las_ligeras_sola():
        preparar()
        v = FUENTE / "video"
        v.mkdir()
        clip_de_prueba(v / "Z001.MP4", 2, 24)
        _FIJOS["medios.auto_ligeras"] = True
        pedidos = []
        real_sync = m._syncthing
        m._syncthing = lambda metodo, camino: pedidos.append(camino)
        try:
            j = lanzar(m.ingerir_archivos, "Auto", "E1", [str(v / "Z001.MP4")])
            assert any("automáticamente" in n for n in j["notas"]), j
            ini = time.time()
            while time.time() - ini < 120:
                c = m._cargar("Auto")["clips"][0]
                if c["estado"] == "ligera_lista":
                    break
                time.sleep(0.3)
        finally:
            _FIJOS["medios.auto_ligeras"] = False
            m._syncthing = real_sync
        assert c["estado"] == "ligera_lista", c
        assert (RAIZ / "ligeras/Auto/E1/Z001.MP4").exists()
        time.sleep(0.5)
        assert any("sub=Auto" in p for p in pedidos), pedidos            # y pidió el escaneo a Syncthing

    @prueba
    def ligera_mismos_fotogramas_y_nombre():
        preparar()
        v = FUENTE / "video"
        v.mkdir()
        clip_de_prueba(v / "A001.MP4", 3, 25)
        clip_de_prueba(v / "B002.mov", 2, 30)
        lanzar(m.ingerir_archivos, "Lig", "E1", [str(v / "A001.MP4"), str(v / "B002.mov")])
        pedidos = []
        real_sync = m._syncthing
        m._syncthing = lambda metodo, camino: pedidos.append((metodo, camino))
        try:
            j = lanzar(m.generar_ligeras, "Lig")
        finally:
            m._syncthing = real_sync
        assert j["estado"] == "terminado" and j["hecho"] == 2 and not j["errores"], j
        assert pedidos == [("POST", "/rest/db/scan?folder=medios-ligeras&sub=Lig")], pedidos   # una vez, al terminar
        for n in ("A001.MP4", "B002.mov"):
            o, l = RAIZ / "originales/Lig/E1" / n, RAIZ / "ligeras/Lig/E1" / n          # misma ruta relativa y nombre
            a, b = m._sonda(o), m._sonda(l)
            assert a["nb_read_frames"] == b["nb_read_frames"] and a["r_frame_rate"] == b["r_frame_rate"], (a, b)
            assert int(b["height"]) == 360 and int(a["height"]) == 720
        assert all(c["estado"] == "ligera_lista" for c in m._cargar("Lig")["clips"])
        assert not list((RAIZ / "ligeras").rglob("*.part"))

    @prueba
    def ligera_no_soportada_queda_pendiente_sin_disfrazar():
        v = FUENTE / "video"
        (v / "raro.mxf").write_bytes(os.urandom(2000))
        lanzar(m.ingerir_archivos, "Lig", "E1", [str(v / "raro.mxf")])
        j = lanzar(m.generar_ligeras, "Lig")
        assert j["estado"] == "terminado con errores" and any("raro.mxf" in e for e in j["errores"]), j
        c = next(c for c in m._cargar("Lig")["clips"] if c["nombre"] == "raro.mxf")
        assert c["estado"] == "copiado" and c["nota_ligera"]                            # NO figura como ligera_lista
        assert not (RAIZ / "ligeras/Lig/E1/raro.mxf").exists()

    @prueba
    def ligera_de_archivo_corrupto_falla_limpio():
        v = FUENTE / "video"
        (v / "roto.mp4").write_bytes(os.urandom(5000))
        lanzar(m.ingerir_archivos, "Lig", "E1", [str(v / "roto.mp4")])
        j = lanzar(m.generar_ligeras, "Lig")
        assert any("roto.mp4" in e for e in j["errores"]), j
        assert not (RAIZ / "ligeras/Lig/E1/roto.mp4").exists()
        assert not list((RAIZ / "ligeras").rglob("*.part"))
else:
    resultados.append(("(pruebas de FFmpeg)", True, "OMITIDAS: FFmpeg no está instalado aquí"))

ok = sum(1 for _, o, _ in resultados if o)
for n, o, d in resultados:
    print(("OK    " if o else "FALLA ") + n + (f"  {d}" if d and (not o or d.startswith("OMIT")) else ""))
print(f"\n{ok}/{len(resultados)} pruebas")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0 if ok == len(resultados) else 1)
