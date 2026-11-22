"""Gestión del material de video: ingesta de originales, copias ligeras y registro por proyecto.

Diseño (decidido con Xavier, 2026-11-22):
  disco externo --(solo lo que el usuario elige, con confirmación)--> <raiz>/originales/<Proyecto>/<escena>/clip
  originales --(ffmpeg)--> <raiz>/ligeras/<Proyecto>/<escena>/clip   (mismo nombre, mismos fotogramas)
  ligeras --(Syncthing, aparte)--> terminus y demás PC de edición

Reglas de seguridad (en código, no en el prompt):
  * Nunca se escribe, mueve ni borra nada en el disco de origen.
  * Nunca se sobrescribe un original: si el nombre existe con contenido distinto, se guarda con
    otro nombre (y se avisa); si existe idéntico, se omite (operación repetible).
  * Cada copia se verifica con SHA-256 releyendo lo escrito en destino antes de darla por buena.
  * Un fallo no se disfraza de éxito: el clip queda con estado de error y el resto sigue.
  * Las operaciones largas corren en segundo plano (hilo) y se consultan con estado_trabajo.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import agent_config as config
from tools.registry import ToolDef, register

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".mxf", ".avi", ".mts", ".m2ts", ".mpg", ".mpeg", ".webm", ".wmv"}
# Contenedor a usar para la copia ligera (la ruta/nombre/extensión debe ser idéntica a la del original).
_MUXER = {".mp4": "mp4", ".m4v": "mp4", ".mov": "mov", ".mkv": "matroska"}
_RESERVADOS = {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)}, *{f"LPT{i}" for i in range(1, 10)}}
_MALOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_CHUNK = 8 * 1024 * 1024
_MAX_ARCHIVOS = 200

_lock_reg = threading.Lock()
_JOBS: dict[str, dict] = {}
_proyectos_ocupados: set[str] = set()
_lock_jobs = threading.Lock()


# ── Rutas y configuración ─────────────────────────────────────────────────────

def _raiz() -> Path:
    cfg = config.get("medios.raiz")
    if cfg:
        return Path(cfg).expanduser()
    return Path("D:/Medios") if os.name == "nt" else Path.home() / "Medios"


def _orig() -> Path:
    return _raiz() / "originales"


def _lig() -> Path:
    return _raiz() / "ligeras"


def _regdir() -> Path:
    return _raiz() / "proyectos"


def _limpio(nombre: str, que: str) -> str:
    """Valida un nombre de proyecto/escena. No lo 'arregla' en silencio: lo rechaza."""
    n = (nombre or "").strip()
    if not n or n in (".", "..") or n != n.strip(". "):
        raise ValueError(f"Nombre de {que} no válido: '{nombre}'")
    if _MALOS.search(n):
        raise ValueError(f"El nombre de {que} '{nombre}' tiene caracteres no permitidos (\\ / : * ? \" < > |)")
    if n.split(".")[0].upper() in _RESERVADOS:
        raise ValueError(f"'{nombre}' es un nombre reservado de Windows; elige otro {que}")
    if len(n) > 80:
        raise ValueError(f"El nombre de {que} es demasiado largo (máx. 80)")
    return n


def _dentro(hijo: Path, padre: Path) -> bool:
    try:
        hijo.resolve().relative_to(padre.resolve())
        return True
    except (ValueError, OSError):
        return False


def _fuente_permitida(p: Path) -> tuple[bool, str]:
    """Solo se lee de discos externos/montajes, nunca del sistema ni de la propia carpeta de medios."""
    extra = [Path(x) for x in (config.get("medios.fuentes_permitidas") or [])]
    if any(_dentro(p, e) for e in extra):
        return True, ""
    if _dentro(p, _raiz()):
        return False, "esa ruta está dentro de la carpeta de medios; el origen debe ser un disco externo"
    if os.name == "nt":
        sistema = os.environ.get("SystemDrive", "C:").upper()
        unidad = (p.drive or "").upper()
        if not unidad:
            return False, "indica la ruta completa con letra de unidad (ej. E:\\DCIM)"
        if unidad == sistema:
            return False, f"la unidad {sistema} es la del sistema; usa el disco externo"
        return True, ""
    if any(_dentro(p, Path(x)) for x in ("/media", "/mnt", "/run/media")):
        return True, ""
    return False, "ruta no permitida como origen (solo discos externos)"


def _fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n} B"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


# ── Registro por proyecto ─────────────────────────────────────────────────────

def _reg_path(proy: str) -> Path:
    return _regdir() / f"{proy}.json"


def _cargar(proy: str) -> dict | None:
    p = _reg_path(proy)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _guardar(proy: str, data: dict) -> None:
    p = _reg_path(proy)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _mutar(proy: str, fn) -> dict:
    """Carga, aplica fn(data) y guarda de forma atómica y serializada."""
    with _lock_reg:
        data = _cargar(proy) or {"proyecto": proy, "creado": _ahora(), "clips": []}
        fn(data)
        _guardar(proy, data)
        return data


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _buscar_clip(data: dict, escena: str, nombre: str) -> dict | None:
    return next((c for c in data["clips"] if c["escena"] == escena and c["nombre"] == nombre), None)


# ── Unidades y exploración (solo lectura) ─────────────────────────────────────

def listar_unidades() -> str:
    """Lista los discos conectados indicando cuáles son extraíbles/externos."""
    filas = []
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        tipos = {2: "extraíble", 3: "fijo", 4: "red", 5: "CD/DVD"}
        sistema = os.environ.get("SystemDrive", "C:").upper()
        mask = k32.GetLogicalDrives()
        for i in range(26):
            if not mask & (1 << i):
                continue
            letra = f"{chr(65 + i)}:"
            t = tipos.get(k32.GetDriveTypeW(f"{letra}\\"), "otro")
            etiqueta = ctypes.create_unicode_buffer(261)
            k32.GetVolumeInformationW(f"{letra}\\", etiqueta, 261, None, None, None, None, 0)
            try:
                u = shutil.disk_usage(f"{letra}\\")
                tam = f"{_fmt_bytes(u.total)}, libres {_fmt_bytes(u.free)}"
            except OSError:
                tam = "sin acceso"
            nota = " (SISTEMA)" if letra == sistema else (" (carpeta de medios)" if letra == _raiz().drive.upper() else "")
            filas.append(f"{letra} {t}{nota} «{etiqueta.value}» {tam}")
    else:
        for base in ("/media", "/mnt", "/run/media"):
            if os.path.isdir(base):
                for d in sorted(os.listdir(base)):
                    filas.append(os.path.join(base, d))
    return "\n".join(filas) or "No se detectaron unidades."


def explorar_disco(ruta: str, recursivo: bool = False, desde: int = 0, solo_video: bool = True) -> str:
    """Lista el contenido de una carpeta de un disco externo (solo lectura)."""
    p = Path(ruta)
    ok, motivo = _fuente_permitida(p)
    if not ok:
        raise ValueError(motivo)
    if not p.is_dir():
        raise ValueError(f"No existe la carpeta: {ruta}")
    entradas = []
    iterador = p.rglob("*") if recursivo else p.iterdir()
    for e in iterador:
        try:
            if e.is_dir():
                if not recursivo:
                    entradas.append((str(e), "carpeta", 0, 0))
                continue
            if solo_video and e.suffix.lower() not in VIDEO_EXT:
                continue
            st = e.stat()
            entradas.append((str(e), "archivo", st.st_size, st.st_mtime))
        except OSError:
            continue
        if len(entradas) > 5000:
            break
    entradas.sort(key=lambda x: (x[1] != "carpeta", x[0].lower()))
    total = len(entradas)
    desde = max(0, int(desde))
    pag = entradas[desde:desde + 20]
    lineas = [f"{len(entradas)} elementos en {ruta}" + (" (recursivo)" if recursivo else "") +
              (f"; mostrando {desde + 1}-{desde + len(pag)}" if total > 20 else "")]
    for ruta_e, tipo, tam, mt in pag:
        if tipo == "carpeta":
            lineas.append(f"[carpeta] {ruta_e}")
        else:
            lineas.append(f"{ruta_e}  {_fmt_bytes(tam)}  {datetime.fromtimestamp(mt):%Y-%m-%d %H:%M}")
    if desde + 20 < total:
        lineas.append(f"... faltan {total - desde - 20}; usa desde={desde + 20}")
    return "\n".join(lineas)


# ── Proyectos ─────────────────────────────────────────────────────────────────

def crear_proyecto(proyecto: str, escenas: list | None = None) -> str:
    proy = _limpio(proyecto, "proyecto")
    escs = [_limpio(e, "escena") for e in (escenas or [])]
    for base in (_orig(), _lig()):
        for e in escs or [None]:
            (base / proy / e if e else base / proy).mkdir(parents=True, exist_ok=True)
    for sub in ("audio/guia", "audio/entregas", "exports"):
        (_raiz() / "trabajo" / proy / sub).mkdir(parents=True, exist_ok=True)
    _mutar(proy, lambda d: None)
    return f"Proyecto '{proy}' listo" + (f" con escenas: {', '.join(escs)}" if escs else "") + "."


def listar_proyectos() -> str:
    if not _regdir().exists():
        return "Aún no hay proyectos."
    filas = []
    for f in sorted(_regdir().glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            filas.append(f"{f.stem}: registro ilegible")
            continue
        c = d["clips"]
        filas.append(f"{d['proyecto']}: {len(c)} clips, {sum(1 for x in c if x.get('estado') == 'ligera_lista')} con ligera")
    return "\n".join(filas) or "Aún no hay proyectos."


# ── Plan de ingesta (solo lectura) ────────────────────────────────────────────

def _validar_seleccion(proyecto, escena, archivos) -> tuple[str, str, list[Path]]:
    proy = _limpio(proyecto, "proyecto")
    esc = _limpio(escena, "escena")
    if not archivos or not isinstance(archivos, list):
        raise ValueError("Indica la lista de archivos a copiar (rutas completas)")
    if len(archivos) > _MAX_ARCHIVOS:
        raise ValueError(f"Máximo {_MAX_ARCHIVOS} archivos por operación; divídelo en tandas")
    rutas = []
    for a in archivos:
        p = Path(a)
        ok, motivo = _fuente_permitida(p)
        if not ok:
            raise ValueError(f"{a}: {motivo}")
        if not p.is_file():
            raise ValueError(f"{a}: no es un archivo existente (indica archivos concretos, no carpetas)")
        rutas.append(p)
    if len({str(r).lower() for r in rutas}) != len(rutas):
        raise ValueError("Hay archivos repetidos en la lista")
    return proy, esc, rutas


def plan_ingesta(proyecto: str, escena: str, archivos: list) -> str:
    """Muestra qué pasaría al copiar (no copia nada). Úsala SIEMPRE antes de ingerir_archivos."""
    proy, esc, rutas = _validar_seleccion(proyecto, escena, archivos)
    destino = _orig() / proy / esc
    total = sum(r.stat().st_size for r in rutas)
    lineas, avisos = [], []
    for r in rutas:
        d = destino / r.name
        estado = "nuevo"
        if d.exists():
            estado = "ya existe con el mismo tamaño (se verificará; si es idéntico se omite)" \
                if d.stat().st_size == r.stat().st_size else "ya existe DISTINTO (se guardará con otro nombre)"
        lineas.append(f"- {r.name} ({_fmt_bytes(r.stat().st_size)}): {estado}")
    nombres = [r.name.lower() for r in rutas]
    if len(set(nombres)) != len(nombres):
        avisos.append("Hay archivos con el mismo nombre en distintas carpetas: los repetidos se guardarán con sufijo de fecha")
    try:
        libre = shutil.disk_usage(_raiz() if _raiz().exists() else _raiz().anchor).free
        if total * 1.05 > libre:
            avisos.append(f"NO CABE: se necesitan {_fmt_bytes(total)} y hay {_fmt_bytes(libre)} libres")
    except OSError:
        avisos.append("No pude comprobar el espacio libre")
    cab = (f"Plan: copiar {len(rutas)} archivo(s), {_fmt_bytes(total)}, a {destino}"
           f"{'' if _cargar(proy) else ' (el proyecto se creará)'}.")
    return "\n".join([cab, *lineas[:25], *( [f"... y {len(lineas) - 25} más"] if len(lineas) > 25 else []),
                      *[f"AVISO: {a}" for a in avisos],
                      "No se ha copiado nada. Para ejecutarlo, muestra este plan al usuario y llama ingerir_archivos."])


# ── Ingesta (escribe: requiere confirmación del usuario) ──────────────────────

def _copiar_verificado(src: Path, dst: Path) -> str:
    """Copia a dst.part calculando el hash, relee lo escrito y recién entonces renombra. Devuelve el sha256."""
    part = dst.with_name(dst.name + ".part")
    h = hashlib.sha256()
    try:
        with open(src, "rb") as fi, open(part, "wb") as fo:
            while chunk := fi.read(_CHUNK):
                h.update(chunk)
                fo.write(chunk)
            fo.flush()
            os.fsync(fo.fileno())
        if _sha256(part) != h.hexdigest():
            raise IOError("la copia no coincide con el origen (hash distinto al releer el destino)")
        if dst.exists():
            raise FileExistsError(f"{dst.name} apareció durante la copia; no se sobrescribe")
        os.replace(part, dst)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return h.hexdigest()


def _nombre_alterno(carpeta: Path, src: Path, sha: str) -> Path:
    fecha = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y%m%d")
    for sufijo in (f"_{fecha}", f"_{fecha}_{sha[:8]}"):
        cand = carpeta / f"{src.stem}{sufijo}{src.suffix}"
        if not cand.exists():
            return cand
        if _sha256(cand) == sha:
            return cand
    raise FileExistsError(f"no encontré un nombre libre para {src.name}")


def _job_ingesta(job_id: str, proy: str, esc: str, rutas: list[Path]) -> None:
    job = _JOBS[job_id]
    destino = _orig() / proy / esc
    try:
        destino.mkdir(parents=True, exist_ok=True)
        (_lig() / proy / esc).mkdir(parents=True, exist_ok=True)
        _mutar(proy, lambda d: None)
        for src in rutas:
            job["actual"] = src.name
            try:
                dst = destino / src.name
                sha, nota, ya = None, "", False
                if dst.exists():
                    sha = _sha256(src)
                    if _sha256(dst) == sha:
                        ya = True
                    else:
                        dst = _nombre_alterno(destino, src, sha)
                        nota = f"renombrado a {dst.name} (el nombre original ya existía con otro contenido)"
                        if dst.exists():           # existe idéntico con el nombre alterno
                            ya = True
                if not ya:
                    sha = _copiar_verificado(src, dst)

                def alta(d, src=src, dst=dst, sha=sha, nota=nota):
                    c = _buscar_clip(d, esc, dst.name)
                    if c is None:
                        d["clips"].append({"escena": esc, "nombre": dst.name, "nombre_original": src.name,
                                           "origen": str(src), "bytes": dst.stat().st_size, "sha256": sha,
                                           "estado": "copiado", "ingestado": _ahora(), "nota": nota})
                    else:
                        c["sha256"], c["bytes"] = sha, dst.stat().st_size
                        c["estado"] = c["estado"] if c.get("estado") == "ligera_lista" else "copiado"
                _mutar(proy, alta)
                job["hecho"] += 1
                if ya:
                    job["ya_estaban"] += 1
                if nota:
                    job["notas"].append(nota)
            except Exception as e:  # un fallo no detiene el resto, y no se disfraza
                job["errores"].append(f"{src.name}: {e}")
        job["estado"] = "terminado" if not job["errores"] else "terminado con errores"
    except Exception as e:
        job["errores"].append(str(e))
        job["estado"] = "fallido"
    finally:
        job["fin"] = _ahora()
        with _lock_jobs:
            _proyectos_ocupados.discard(proy)
    if job["hecho"] and config.get("medios.auto_ligeras", True):
        try:
            job["notas"].append(_encadenar_ligeras(proy, esc))
        except Exception as e:
            job["notas"].append(f"no pude iniciar las copias ligeras automáticas ({e}); pídelas con generar_ligeras")


def _nuevo_job(tipo: str, proy: str, total: int) -> str:
    with _lock_jobs:
        if proy in _proyectos_ocupados:
            raise RuntimeError(f"Ya hay una operación en curso para '{proy}'; consulta estado_trabajo")
        _proyectos_ocupados.add(proy)
    jid = uuid.uuid4().hex[:8]
    _JOBS[jid] = {"id": jid, "tipo": tipo, "proyecto": proy, "total": total, "hecho": 0, "ya_estaban": 0,
                  "errores": [], "notas": [], "actual": "", "estado": "en curso", "inicio": _ahora()}
    return jid


def ingerir_archivos(proyecto: str, escena: str, archivos: list) -> str:
    """Copia SOLO los archivos indicados a la carpeta de originales (en segundo plano). Pide confirmación."""
    proy, esc, rutas = _validar_seleccion(proyecto, escena, archivos)
    jid = _nuevo_job("ingesta", proy, len(rutas))
    threading.Thread(target=_job_ingesta, args=(jid, proy, esc, rutas), daemon=True).start()
    return (f"Ingesta iniciada (trabajo {jid}): {len(rutas)} archivo(s) hacia {proy}/{esc}. "
            "Consulta el avance con estado_trabajo; no se avisa sola.")


# ── Copias ligeras ────────────────────────────────────────────────────────────

def _ffbin(nombre: str) -> str:
    cfg = config.get(f"medios.{nombre}")
    if cfg and Path(cfg).exists():
        return str(cfg)
    w = shutil.which(nombre)
    if w:
        return w
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", "")
        for patron in (f"{base}/Microsoft/WinGet/Links/{nombre}.exe",
                       f"{base}/Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/bin/{nombre}.exe"):
            hits = glob.glob(patron, recursive=True)
            if hits:
                return hits[0]
    raise RuntimeError(f"No encuentro {nombre}; instala FFmpeg o indica medios.{nombre} en el config")


def _sonda(ruta: Path) -> dict:
    r = subprocess.run([_ffbin("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_frames",
                        "-show_entries", "stream=nb_read_frames,r_frame_rate,width,height,codec_name",
                        "-of", "json", str(ruta)], capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe falló: {r.stderr.strip()[-200:]}")
    s = (json.loads(r.stdout).get("streams") or [None])[0]
    if not s or not s.get("nb_read_frames"):
        raise RuntimeError("el archivo no tiene video legible")
    return s


def _hacer_ligera(src: Path, dst: Path, altura: int) -> dict:
    muxer = _MUXER.get(src.suffix.lower())
    if not muxer:
        raise RuntimeError(f"formato {src.suffix} sin soporte de copia ligera todavía (queda pendiente)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_name(dst.name + ".part")
    try:
        a = _sonda(src)
        r = subprocess.run([_ffbin("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a?",
                            "-vf", f"scale=-2:{altura}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                            "-pix_fmt", "yuv420p", "-fps_mode", "passthrough", "-c:a", "aac", "-b:a", "96k",
                            "-map_metadata", "0", "-f", muxer, str(part)],
                           capture_output=True, text=True, timeout=6 * 3600)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg falló: {r.stderr.strip()[-200:]}")
        b = _sonda(part)
        if a["nb_read_frames"] != b["nb_read_frames"] or a["r_frame_rate"] != b["r_frame_rate"]:
            raise RuntimeError(f"no coincide: original {a['nb_read_frames']} fotogramas a {a['r_frame_rate']}, "
                               f"ligera {b['nb_read_frames']} a {b['r_frame_rate']}")
        os.replace(part, dst)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return {"frames": int(a["nb_read_frames"]), "fps": a["r_frame_rate"], "alto": int(b["height"])}


def _job_ligeras(job_id: str, proy: str, pendientes: list[dict], altura: int) -> None:
    job = _JOBS[job_id]
    try:
        for c in pendientes:
            job["actual"] = c["nombre"]
            src = _orig() / proy / c["escena"] / c["nombre"]
            dst = _lig() / proy / c["escena"] / c["nombre"]
            try:
                if not src.exists():
                    raise RuntimeError("el original no está en la carpeta de originales")
                info = _hacer_ligera(src, dst, altura)

                def ok(d, c=c, info=info):
                    x = _buscar_clip(d, c["escena"], c["nombre"])
                    x["estado"], x["ligera"], x["nota_ligera"] = "ligera_lista", info, ""
                _mutar(proy, ok)
                job["hecho"] += 1
            except Exception as e:
                msg = str(e)
                job["errores"].append(f"{c['nombre']}: {msg}")

                def mal(d, c=c, msg=msg):
                    x = _buscar_clip(d, c["escena"], c["nombre"])
                    x["nota_ligera"] = msg
                _mutar(proy, mal)
        if job["hecho"]:
            aviso = _pedir_escaneo(proy)
            if aviso:
                job["notas"].append(aviso)
        job["estado"] = "terminado" if not job["errores"] else "terminado con errores"
    except Exception as e:
        job["errores"].append(str(e))
        job["estado"] = "fallido"
    finally:
        job["fin"] = _ahora()
        with _lock_jobs:
            _proyectos_ocupados.discard(proy)


def generar_ligeras(proyecto: str, escena: str = "", altura: int = 360) -> str:
    """Genera las copias ligeras de los clips copiados que aún no la tienen (en segundo plano)."""
    proy = _limpio(proyecto, "proyecto")
    d = _cargar(proy)
    if not d:
        raise ValueError(f"No existe el proyecto '{proy}'")
    altura = int(altura)
    pend = [c for c in d["clips"] if c.get("estado") == "copiado"
            and Path(c["nombre"]).suffix.lower() in VIDEO_EXT and (not escena or c["escena"] == escena)]
    if not pend:
        return "No hay clips de video pendientes de copia ligera."
    _ffbin("ffmpeg"), _ffbin("ffprobe")            # falla pronto si falta FFmpeg
    jid = _nuevo_job("ligeras", proy, len(pend))
    threading.Thread(target=_job_ligeras, args=(jid, proy, pend, altura), daemon=True).start()
    return f"Generando {len(pend)} copia(s) ligera(s) a {altura}p (trabajo {jid}). Consulta estado_trabajo."


def _encadenar_ligeras(proy: str, esc: str) -> str:
    """Tras una ingesta correcta, lanza solas las copias ligeras de esa escena (flujo: originales -> ligeras -> terminus)."""
    d = _cargar(proy)
    pend = [c for c in (d or {"clips": []})["clips"] if c.get("estado") == "copiado" and c["escena"] == esc
            and Path(c["nombre"]).suffix.lower() in VIDEO_EXT]
    if not pend:
        return "Sin clips de video pendientes de copia ligera."
    _ffbin("ffmpeg"), _ffbin("ffprobe")
    jid = _nuevo_job("ligeras", proy, len(pend))
    threading.Thread(target=_job_ligeras, args=(jid, proy, pend, 360), daemon=True).start()
    return f"Copias ligeras iniciadas automáticamente (trabajo {jid})."


# ── Estado ────────────────────────────────────────────────────────────────────

def estado_trabajo(trabajo: str = "") -> str:
    if trabajo:
        j = _JOBS.get(trabajo)
        if not j:
            return f"No conozco el trabajo '{trabajo}' (los trabajos se pierden si el agente se reinicia; mira estado_proyecto)."
        trabajos = [j]
    else:
        trabajos = sorted(_JOBS.values(), key=lambda x: x["inicio"])[-3:]
        if not trabajos:
            return "No hay trabajos desde que arrancó el agente."
    out = []
    for j in trabajos:
        s = f"[{j['id']}] {j['tipo']} {j['proyecto']}: {j['estado']}, {j['hecho']}/{j['total']}"
        if j["estado"] == "en curso" and j["actual"]:
            s += f" (ahora: {j['actual']})"
        if j.get("ya_estaban"):
            s += f"; {j['ya_estaban']} ya estaban idénticos"
        out.append(s)
        out += [f"  NOTA: {n}" for n in j["notas"][:5]] + [f"  ERROR: {e}" for e in j["errores"][:8]]
    return "\n".join(out)


def _syncthing_clave() -> str | None:
    ruta = (Path(os.environ.get("LOCALAPPDATA", "")) / "Syncthing" / "config.xml") if os.name == "nt" \
        else Path.home() / ".local/state/syncthing/config.xml"
    try:
        return re.search(r"<apikey>([^<]+)</apikey>", ruta.read_text(encoding="utf-8", errors="ignore")).group(1)
    except Exception:
        return None


def _syncthing(metodo: str, camino: str):
    clave = _syncthing_clave()
    if not clave:
        raise RuntimeError("no encuentro la configuración de Syncthing en este equipo")
    r = urllib.request.Request("http://127.0.0.1:8384" + camino, method=metodo, headers={"X-API-Key": clave})
    cuerpo = urllib.request.urlopen(r, timeout=8).read().decode()
    return json.loads(cuerpo) if cuerpo.strip() else None


def _pedir_escaneo(proy: str) -> str:
    """Le pide a Syncthing que escanee ya la carpeta del proyecto (el detector automático de Windows falla a veces)."""
    carpeta = config.get("medios.sync.carpeta") or "medios-ligeras"
    try:
        _syncthing("POST", f"/rest/db/scan?folder={urllib.parse.quote(carpeta)}&sub={urllib.parse.quote(proy)}")
        return ""
    except Exception as e:
        return f"no pude pedir el escaneo a Syncthing ({type(e).__name__}); se sincronizará en el próximo escaneo periódico"


def _estado_sync() -> str:
    """Avance de la carpeta de ligeras hacia el equipo de destino, vía API local de Syncthing."""
    carpeta = config.get("medios.sync.carpeta") or "medios-ligeras"
    destino = config.get("medios.sync.destino")
    try:
        if not destino:
            return "Sincronización: falta medios.sync.destino en el config"
        c = _syncthing("GET", f"/rest/db/completion?folder={carpeta}&device={destino}")
        pct, falta = c.get("completion", 0), c.get("needBytes", 0)
        return ("Sincronización con terminus: completa (100%)." if falta == 0 and pct >= 100
                else f"Sincronización con terminus: {pct:.0f}%, faltan {_fmt_bytes(falta)}.")
    except Exception as e:
        return f"Sincronización: no pude consultar Syncthing ({type(e).__name__})."


def estado_proyecto(proyecto: str) -> str:
    proy = _limpio(proyecto, "proyecto")
    d = _cargar(proy)
    if not d:
        return f"No existe el proyecto '{proy}'."
    clips = d["clips"]
    cuenta: dict[str, int] = {}
    for c in clips:
        cuenta[c.get("estado", "?")] = cuenta.get(c.get("estado", "?"), 0) + 1
    lineas = [f"Proyecto {proy}: {len(clips)} clips ({', '.join(f'{v} {k}' for k, v in cuenta.items()) or 'vacío'})"]
    por_escena: dict[str, list] = {}
    for c in clips:
        por_escena.setdefault(c["escena"], []).append(c)
    for esc, cs in por_escena.items():
        lineas.append(f"- {esc}: {len(cs)} clips")
    for c in clips:
        if c.get("nota_ligera"):
            lineas.append(f"  PENDIENTE {c['nombre']}: {c['nota_ligera']}")
        if c.get("nota"):
            lineas.append(f"  NOTA {c['nombre']}: {c['nota']}")
    sin_ligera = [f"{c['escena']}/{c['nombre']}" for c in clips
                  if Path(c["nombre"]).suffix.lower() in VIDEO_EXT and c.get("estado") != "ligera_lista"]
    sync = _estado_sync()
    sync_ok = "completa (100%)" in sync
    if not clips:
        veredicto = "LISTO PARA EDITAR: NO (el proyecto no tiene clips)"
    elif sin_ligera:
        veredicto = f"LISTO PARA EDITAR: NO (faltan copias ligeras: {', '.join(sin_ligera[:6])})"
    elif "no pude consultar" in sync or "falta medios.sync" in sync:
        veredicto = "LISTO PARA EDITAR: NO (no pude comprobar la sincronización con terminus)"
    elif not sync_ok:
        veredicto = "LISTO PARA EDITAR: NO (las ligeras aún no terminaron de llegar a terminus)"
    else:
        veredicto = "LISTO PARA EDITAR: SI (todas las copias ligeras existen y llegaron a terminus)"
    lineas.insert(1, veredicto)
    lineas.append(sync)
    return "\n".join(lineas[:40])


def clips_proyecto(proyecto: str, escena: str = "") -> str:
    proy = _limpio(proyecto, "proyecto")
    d = _cargar(proy)
    if not d:
        return f"No existe el proyecto '{proy}'."
    cs = [c for c in d["clips"] if not escena or c["escena"] == escena]
    if not cs:
        return "Sin clips."
    out = [f"{c['escena']}/{c['nombre']}  [{c['estado']}]  desde {c['origen']}" for c in cs[:30]]
    if len(cs) > 30:
        out.append(f"... y {len(cs) - 30} más")
    return "\n".join(out)


# ── Registro de tools ─────────────────────────────────────────────────────────

_S = lambda d, req=(): {"type": "object", "properties": d, "required": list(req)}  # noqa: E731
_STR = lambda t: {"type": "string", "description": t}  # noqa: E731

register(ToolDef("listar_unidades",
    "Lista los discos conectados (y cuáles son externos/extraíbles) para encontrar el disco con el material.",
    "media", _S({}), listar_unidades))
register(ToolDef("explorar_disco",
    "Lista el contenido de una carpeta de un disco externo (solo lectura). Úsala para mostrar al usuario qué clips hay "
    "y que él elija cuáles copiar. Máx. 20 resultados por página (usa `desde`).",
    "media", _S({"ruta": _STR("Ruta completa, ej. E:\\DCIM"), "recursivo": {"type": "boolean", "default": False},
                 "desde": {"type": "integer", "default": 0}, "solo_video": {"type": "boolean", "default": True}}, ["ruta"]),
    explorar_disco))
register(ToolDef("crear_proyecto",
    "Crea un proyecto de video (carpetas de originales y ligeras + registro) con escenas opcionales.",
    "media", _S({"proyecto": _STR("Nombre del proyecto"), "escenas": {"type": "array", "items": {"type": "string"}}}, ["proyecto"]),
    crear_proyecto))
register(ToolDef("listar_proyectos", "Lista los proyectos de video registrados.", "media", _S({}), listar_proyectos))
register(ToolDef("plan_ingesta",
    "Muestra qué ocurriría al copiar los archivos elegidos (no copia nada). SIEMPRE antes de ingerir_archivos; "
    "enseña el plan al usuario.",
    "media", _S({"proyecto": _STR("Proyecto"), "escena": _STR("Escena"),
                 "archivos": {"type": "array", "items": {"type": "string"}, "description": "Rutas completas de los archivos que el usuario eligió"}},
                ["proyecto", "escena", "archivos"]), plan_ingesta))
register(ToolDef("ingerir_archivos",
    "Copia SOLO los archivos que el usuario eligió al almacén de originales, con verificación por hash. Requiere que "
    "el usuario escriba 'confirmar'. Nunca la uses sin haber mostrado antes plan_ingesta y sin selección explícita.",
    "media", _S({"proyecto": _STR("Proyecto"), "escena": _STR("Escena"),
                 "archivos": {"type": "array", "items": {"type": "string"}}}, ["proyecto", "escena", "archivos"]),
    ingerir_archivos, requires_confirm=True))
register(ToolDef("generar_ligeras",
    "Genera las copias ligeras (mismo nombre, mismos fotogramas) de los clips ya copiados de un proyecto.",
    "media", _S({"proyecto": _STR("Proyecto"), "escena": _STR("Opcional: solo esa escena"),
                 "altura": {"type": "integer", "default": 360}}, ["proyecto"]), generar_ligeras))
register(ToolDef("estado_trabajo", "Avance de una ingesta o generación de ligeras en curso (o las últimas).",
    "media", _S({"trabajo": _STR("Id del trabajo; vacío = los últimos")}), estado_trabajo))
register(ToolDef("estado_proyecto",
    "Estado de un proyecto: clips por escena, copias ligeras, pendientes y avance de sincronización hacia terminus.",
    "media", _S({"proyecto": _STR("Proyecto")}, ["proyecto"]), estado_proyecto))
register(ToolDef("clips_proyecto", "Lista los clips de un proyecto (y de dónde vinieron).",
    "media", _S({"proyecto": _STR("Proyecto"), "escena": _STR("Opcional")}, ["proyecto"]), clips_proyecto))
