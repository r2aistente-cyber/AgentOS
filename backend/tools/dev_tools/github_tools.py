"""GitHub tools via API REST (sin gh CLI)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import requests

import backend.config as config
from backend.tools.registry import ToolDef, register

_API = "https://api.github.com"


def _headers() -> dict:
    token = config.get_secret("github_token")
    if not token:
        raise RuntimeError("GITHUB_TOKEN no configurado en el entorno")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def list_repos(org: str = "r2aistente-cyber") -> str:
    r = requests.get(f"{_API}/users/{org}/repos", headers=_headers(), params={"per_page": 30})
    r.raise_for_status()
    repos = r.json()
    return "\n".join(f"- {repo['name']} ({repo['visibility']})" for repo in repos)


def list_issues(repo: str, state: str = "open") -> str:
    r = requests.get(f"{_API}/repos/{repo}/issues", headers=_headers(), params={"state": state, "per_page": 20})
    r.raise_for_status()
    issues = r.json()
    if not issues:
        return f"Sin issues {state} en {repo}"
    return "\n".join(f"#{i['number']} {i['title']} [{i['state']}]" for i in issues)


def create_issue(repo: str, title: str, body: str = "") -> str:
    r = requests.post(f"{_API}/repos/{repo}/issues", headers=_headers(), json={"title": title, "body": body})
    r.raise_for_status()
    data = r.json()
    return f"Issue creado: #{data['number']} — {data['html_url']}"


def create_pr(repo: str, title: str, head: str, base: str = "main", body: str = "") -> str:
    r = requests.post(f"{_API}/repos/{repo}/pulls", headers=_headers(),
                      json={"title": title, "head": head, "base": base, "body": body})
    r.raise_for_status()
    data = r.json()
    return f"PR creado: #{data['number']} — {data['html_url']}"


def list_prs(repo: str, state: str = "open") -> str:
    r = requests.get(f"{_API}/repos/{repo}/pulls", headers=_headers(), params={"state": state, "per_page": 20})
    r.raise_for_status()
    prs = r.json()
    if not prs:
        return f"Sin PRs {state} en {repo}"
    return "\n".join(f"#{p['number']} {p['title']} [{p['state']}]" for p in prs)


def clone_repo(repo: str, dest: str = "") -> str:
    token = config.get_secret("github_token")
    if not token:
        raise RuntimeError("GITHUB_TOKEN no configurado")
    url = f"https://{token}@github.com/{repo}.git"
    target = dest or repo.split("/")[-1]
    result = subprocess.run(["git", "clone", url, target], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return f"Repo clonado en: {target}"


def commit_push(path: str, message: str, branch: str = "") -> str:
    cwd = Path(path).expanduser()
    cmds = [
        ["git", "add", "-A"],
        ["git", "commit", "-m", message],
    ]
    if branch:
        cmds.append(["git", "push", "origin", branch])
    else:
        cmds.append(["git", "push"])

    for cmd in cmds:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout:
            raise RuntimeError(f"{' '.join(cmd)}: {r.stderr}")
    return f"Commit y push exitoso: {message}"


# ─── Registro ─────────────────────────────────────────────────────────────

register(ToolDef(
    name="list_repos",
    description="Lista repositorios de GitHub del usuario/org configurado.",
    category="dev",
    min_level=3,
    parameters={
        "type": "object",
        "properties": {"org": {"type": "string", "description": "Usuario u org de GitHub", "default": "r2aistente-cyber"}},
    },
    handler=list_repos,
))

register(ToolDef(
    name="list_issues",
    description="Lista issues de un repositorio de GitHub.",
    category="dev",
    min_level=3,
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/repo, ej: r2aistente-cyber/r2-autonomous"},
            "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
        },
        "required": ["repo"],
    },
    handler=list_issues,
))

register(ToolDef(
    name="create_issue",
    description="Crea un issue en un repositorio de GitHub.",
    category="dev",
    min_level=3,
    requires_confirmation=True,
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "title": {"type": "string"},
            "body": {"type": "string", "default": ""},
        },
        "required": ["repo", "title"],
    },
    handler=create_issue,
))

register(ToolDef(
    name="create_pr",
    description="Crea un Pull Request en GitHub.",
    category="dev",
    min_level=3,
    requires_confirmation=True,
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "title": {"type": "string"},
            "head": {"type": "string", "description": "Rama origen"},
            "base": {"type": "string", "default": "main"},
            "body": {"type": "string", "default": ""},
        },
        "required": ["repo", "title", "head"],
    },
    handler=create_pr,
))

register(ToolDef(
    name="list_prs",
    description="Lista Pull Requests de un repositorio.",
    category="dev",
    min_level=3,
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
        },
        "required": ["repo"],
    },
    handler=list_prs,
))

register(ToolDef(
    name="clone_repo",
    description="Clona un repositorio de GitHub en el sandbox.",
    category="dev",
    min_level=3,
    parameters={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/repo"},
            "dest": {"type": "string", "description": "Carpeta destino (opcional)", "default": ""},
        },
        "required": ["repo"],
    },
    handler=clone_repo,
))

register(ToolDef(
    name="commit_push",
    description="Hace git add -A, commit y push en un directorio.",
    category="dev",
    min_level=3,
    requires_confirmation=True,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta del repo local"},
            "message": {"type": "string", "description": "Mensaje del commit"},
            "branch": {"type": "string", "description": "Rama destino (opcional)", "default": ""},
        },
        "required": ["path", "message"],
    },
    handler=commit_push,
))
