# AgentOS

**A self-hosted hub for running independent AI agents as isolated processes** — each agent with its own directory, memory, model, tools and network channels, managed from one place.

[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-active%20development-orange)

AgentOS is not a chatbot. It's the layer that **creates, launches, monitors and stops** your agents. Each agent runs as its own process, in the folder you choose, with its own SQLite memory, its own LLM provider, its own sandboxed toolset, and its own port. The Hub only registers and supervises them — it never centralizes their data.

> Personal project, in active development. Built and run daily by the author; two production agents currently run on it (a personal assistant and a legal-tech assistant).

---

## Architecture

```
                    ┌──────────────────────────────┐
                    │  Hub  (FastAPI, port 8234)    │
                    │  create · launch · monitor    │
                    │  health-check + auto-restart  │
                    └───────────────┬──────────────┘
          ┌───────────────┬─────────┴───────┬───────────────┐
          ▼               ▼                 ▼               ▼
   ┌────────────┐  ┌────────────┐    ┌────────────┐  ┌────────────┐
   │  Agent A   │  │  Agent B   │    │  Agent C   │      ...
   │  :9001     │  │  :9002     │    │  :9003     │
   │  own dir   │  │  own dir   │    │  own dir   │
   │  memory.db │  │  memory.db │    │  memory.db │
   │  config    │  │  config    │    │  config    │
   │  tools/    │  │  tools/    │    │  tools/    │
   │  Ollama    │  │  OpenAI    │    │  Anthropic │
   └────────────┘  └────────────┘    └────────────┘
```

Each agent is spawned from `hub/templates/` (LLM adapter, engine, tools, security sandbox, memory, RAG). The Hub reconciles state on restart: agents whose processes are gone are marked offline, and `auto_restart` ones are brought back.

---

## Features

- **Multi-LLM, per agent** — Ollama (local models), OpenAI, Anthropic, Google. API keys can be global (inherited) or per-agent.
- **Per-agent RAG** — local knowledge base per agent (ChromaDB + sentence-transformers), used transparently by the agent's tools.
- **MCP interoperability** — agents can expose/consume tools over the Model Context Protocol to couple with host programs.
- **Network channels, per agent** — WhatsApp (Node sidecar) and Telegram (long-polling, no sidecar), enabled individually.
- **Sandboxed tools** — filesystem and shell tools are restricted to the agent's own directory; path traversal outside the sandbox is blocked.
- **Export / import** — package an agent as a `.tar.gz` (secrets stripped) and restore it elsewhere.
- **Health checking** — periodic checks with configurable interval/timeout and optional auto-restart.
- **Hub auth** — optional bearer token on the Hub API; CORS locked to the known UI origins.

---

## Quick start

Requires **Python 3.11+**. Node.js 18+ is optional (only for the WhatsApp channel). Ollama is optional (only for local models).

```bash
git clone https://github.com/r2aistente-cyber/AgentOS.git
cd AgentOS

# macOS / Linux
./install.sh          # sets up the venv, installs deps, creates ~/AgentOS/, seeds a first agent
./Iniciar-R2Hub.sh    # starts the Hub (:8234), the frontend (:5500) and the desktop window

# Windows
install.bat
Iniciar-R2Hub.bat
```

The Hub API is then at `http://localhost:8234`, the UI at `http://localhost:5500` (also shown in a native pywebview window). Agents live wherever you place them, not inside the repo.

Configuration is two-level: `config.yaml` for the Hub, and a `config.yaml` inside each agent's own directory (personality, provider, tools, channels, sandbox). See [SETUP.md](SETUP.md).

---

## Tests

```bash
pytest -q
```

~300 automated tests covering the Hub API, the agent manager, the engine, the tool sandbox, RAG, export/import and the template. See [pytest.ini](pytest.ini).

---

## Project layout

| Path | What |
|---|---|
| `hub/` | The Hub — FastAPI app, agent manager, process supervision, health checker, exporter/importer, MCP, channel managers |
| `hub/api/` | REST endpoints (`agents`, `admin`, `fs`) |
| `hub/templates/` | The agent blueprint copied into every new agent (engine, LLM adapters, tools, security, memory, RAG, channels) |
| `frontend/` | Vite + React UI (the live one) |
| `desktop_shell.py` | pywebview window that hosts the UI |
| `tests/` | Test suite |
| `docs/` | Project site (GitHub Pages) |
| `desktop/` | Early Tauri prototype — **not** the current UI |

---

## Tech stack

Python · FastAPI · Uvicorn · Pydantic · SQLite (aiosqlite) · ChromaDB · sentence-transformers · MCP · React · Vite · pywebview · Node (WhatsApp sidecar)

---

## Status & scope

- Designed for **single-machine or trusted-LAN** use. Set `hub.token` to require auth on the Hub API.
- A packaged desktop installer is **planned, not shipped** — the `desktop/` Tauri app is an early prototype; the current way to run AgentOS is the scripts above.
- The design docs ([CONCEPTO.md](CONCEPTO.md), [DESIGN.md](DESIGN.md), [APP.md](APP.md), [EXPORT.md](EXPORT.md)) describe both what exists and where it's headed — this README is the accurate picture of the current state.

## License

[MIT](LICENSE) © 2026 Javier Enrique Castaño Roldán
