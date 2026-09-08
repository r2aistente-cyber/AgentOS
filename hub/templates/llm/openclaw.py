"""Adapter LLM que enruta a través de la suscripción de ChatGPT (Go/Plus/Pro)
reutilizando el token OAuth que OpenClaw ya guardó en su auth store.

- Endpoint: https://chatgpt.com/backend-api/codex/responses  (API "Responses" de OpenAI,
  la misma que usa Codex CLI). Requiere stream=true.
- El token vive en el sqlite de OpenClaw. La ubicación cambió con 2026.9.x:
  nuevo:  ~/.openclaw/state/openclaw.sqlite  (config_machine_state / authProfiles.store)
  viejo:  ~/.openclaw/agents/main/agent/openclaw-agent.sqlite  (auth_profile_store)
  _TokenStore detecta automáticamente cuál existe.
  OpenClaw lo mantiene fresco cuando hace sus propias llamadas; este adapter además
  lo refresca por su cuenta con el refresh_token si está por vencer, y reescribe
  el sqlite para que ambos lados queden sincronizados.

Config (config.yaml del agente):
  llm:
    provider: openclaw
    model: gpt-5.4-mini          # opcional, default gpt-5.4-mini
    openclaw_db: /ruta/al/openclaw-agent.sqlite   # opcional, default el de arriba
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall

_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
_TOKEN_URL = "https://auth.openai.com/oauth/token"
_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"  # client_id del flujo OAuth de OpenClaw/Codex
_DEFAULT_DB = "~/.openclaw/agents/main/agent/openclaw-agent.sqlite"
_DEFAULT_MODEL = "gpt-5.4-mini"
_REFRESH_MARGIN_S = 120  # refresca si vence en menos de esto


class _TokenStore:
    """Lee/refresca/reescribe el perfil OAuth de OpenAI que guarda OpenClaw.

    OpenClaw movió el auth store en 2026.9.x:
      viejo:  <agentDir>/openclaw-agent.sqlite  ->  auth_profile_store[store_key='primary'].store_json
      nuevo:  ~/.openclaw/state/openclaw.sqlite  ->  config_machine_state[state_key='authProfiles.store'].value_json
    La estructura interna del JSON ({"profiles": {...}}) es la misma en ambos.
    Se detecta automáticamente cuál existe; `openclaw_db` en el config sólo
    sirve como pista para localizar el layout viejo.
    """

    # (db_path, tabla, columna_json, columna_key, valor_key, columna_ts)
    _LAYOUTS = [
        ("~/.openclaw/state/openclaw.sqlite", "config_machine_state",
         "value_json", "state_key", "authProfiles.store", "updated_at_ms"),
    ]

    def __init__(self, db_path_hint: str) -> None:
        hint = os.path.expanduser(db_path_hint)
        self._candidates = list(self._LAYOUTS)
        if hint:
            self._candidates.append(
                (hint, "auth_profile_store", "store_json", "store_key", "primary", "updated_at")
            )
        self._active = None  # el layout que funcionó, para _save

    def _load(self) -> tuple[dict, str]:
        last_err = "ninguna ubicación de auth store encontrada"
        for lay in self._candidates:
            db, tbl, jcol, kcol, kval, _ = lay
            db = os.path.expanduser(db)
            if not os.path.exists(db):
                continue
            try:
                con = sqlite3.connect(db, timeout=10)
                try:
                    row = con.execute(
                        f"SELECT {jcol} FROM {tbl} WHERE {kcol}=?", (kval,)
                    ).fetchone()
                finally:
                    con.close()
            except sqlite3.OperationalError as e:
                last_err = str(e)
                continue
            if not row or not row[0]:
                continue
            store = json.loads(row[0])
            profiles = store.get("profiles", {})
            key = next((k for k in profiles if k.startswith("openai:")), None)
            if not key:
                continue
            self._active = lay
            return store, key
        raise RuntimeError(
            "OpenClaw no tiene un perfil de auth 'openai:' en ninguna ubicación conocida "
            f"({last_err}) — corre `openclaw models auth login --provider openai`")

    def _save(self, store: dict) -> None:
        if not self._active:
            return
        db, tbl, jcol, kcol, kval, tscol = self._active
        db = os.path.expanduser(db)
        con = sqlite3.connect(db, timeout=10)
        try:
            con.execute(
                f"UPDATE {tbl} SET {jcol}=?, {tscol}=? WHERE {kcol}=?",
                (json.dumps(store), int(time.time() * 1000), kval),
            )
            con.commit()
        finally:
            con.close()

    def _refresh(self, prof: dict) -> dict:
        rt = prof.get("refresh")
        if not rt:
            raise RuntimeError("Token de OpenAI vencido y sin refresh_token — "
                               "vuelve a correr `openclaw models auth login --provider openai`")
        r = httpx.post(_TOKEN_URL, json={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": _CLIENT_ID,
        }, timeout=30)
        r.raise_for_status()
        data = r.json()
        prof["access"] = data["access_token"]
        if data.get("refresh_token"):
            prof["refresh"] = data["refresh_token"]
        expires_in = data.get("expires_in", 3600)
        prof["expires"] = int((time.time() + expires_in) * 1000)
        return prof

    def get(self) -> tuple[str, str]:
        """Devuelve (access_token, chatgpt_account_id), refrescando si hace falta."""
        store, key = self._load()
        prof = store["profiles"][key]
        exp_ms = prof.get("expires", 0)
        if exp_ms and exp_ms / 1000 - time.time() < _REFRESH_MARGIN_S:
            prof = self._refresh(prof)
            store["profiles"][key] = prof
            self._save(store)
        acc = prof.get("accountId") or prof.get("account_id") or ""
        return prof["access"], acc


def _to_responses_input(messages: list[dict]) -> list[dict]:
    """Traduce mensajes estilo OpenAI chat -> items de la API Responses."""
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "tool":
            out.append({
                "type": "function_call_output",
                "call_id": m.get("tool_call_id", ""),
                "output": content if isinstance(content, str) else json.dumps(content),
            })
            continue
        if role == "assistant":
            if content:
                out.append({"type": "message", "role": "assistant",
                            "content": [{"type": "output_text", "text": content}]})
            for tc in m.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                args = fn.get("arguments", "")
                if not isinstance(args, str):
                    args = json.dumps(args)
                out.append({
                    "type": "function_call",
                    "call_id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "arguments": args or "{}",
                })
            continue
        # user / system / cualquier otro -> mensaje de entrada
        text = content if isinstance(content, str) else json.dumps(content)
        out.append({"type": "message", "role": role or "user",
                    "content": [{"type": "input_text", "text": text}]})
    return out


def _to_responses_tools(tools: list[dict] | None) -> list[dict]:
    if not tools:
        return []
    res = []
    for t in tools:
        fn = t.get("function", t)  # acepta formato anidado {type,function:{}} o plano
        res.append({
            "type": "function",
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return res


class OpenClawAdapter(LLMAdapter):
    def __init__(self, model: str | None = None) -> None:
        self._model = model or config.get("llm.model", _DEFAULT_MODEL) or _DEFAULT_MODEL
        self._max_tokens = config.get("llm.max_tokens", 4096)
        self._store = _TokenStore(config.get("llm.openclaw_db", _DEFAULT_DB) or _DEFAULT_DB)
        self._session_id = str(uuid.uuid4())

    def _headers(self, token: str, account_id: str) -> dict:
        h = {
            "Authorization": f"Bearer {token}",
            "OpenAI-Beta": "responses=experimental",
            "originator": "codex_cli_rs",
            "session_id": self._session_id,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if account_id:
            h["chatgpt-account-id"] = account_id
        return h

    async def chat(self, messages, tools=None, system=None) -> LLMResponse:
        token, account_id = self._store.get()

        instructions = system or ""
        msgs = list(messages)
        # un system embebido en messages pasa a instructions
        if msgs and msgs[0].get("role") == "system":
            instructions = ((instructions + "\n\n") if instructions else "") + str(msgs[0].get("content") or "")
            msgs = msgs[1:]

        payload: dict = {
            "model": self._model,
            "input": _to_responses_input(msgs),
            "stream": True,
            "store": False,
        }
        if instructions:
            payload["instructions"] = instructions
        rtools = _to_responses_tools(tools)
        if rtools:
            payload["tools"] = rtools
            payload["tool_choice"] = "auto"

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        in_tok = out_tok = 0

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", _RESPONSES_URL,
                                     headers=self._headers(token, account_id),
                                     json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    resp.status_code  # noqa
                    raise httpx.HTTPStatusError(
                        f"OpenClaw/Codex {resp.status_code}: {body[:300]}",
                        request=resp.request, response=resp)
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw in ("", "[DONE]"):
                        continue
                    try:
                        ev = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    et = ev.get("type", "")
                    if et == "response.output_item.done":
                        item = ev.get("item", {})
                        it = item.get("type")
                        if it == "message":
                            for part in item.get("content", []):
                                if part.get("type") == "output_text" and part.get("text"):
                                    text_parts.append(part["text"])
                        elif it == "function_call":
                            args = item.get("arguments") or "{}"
                            try:
                                parsed = json.loads(args) if isinstance(args, str) else args
                            except json.JSONDecodeError:
                                parsed = {}
                            tool_calls.append(ToolCall(
                                id=item.get("call_id", ""),
                                name=item.get("name", ""),
                                arguments=parsed if isinstance(parsed, dict) else {},
                            ))
                    elif et == "response.completed":
                        usage = ev.get("response", {}).get("usage") or {}
                        in_tok = usage.get("input_tokens", 0)
                        out_tok = usage.get("output_tokens", 0)
                    elif et == "response.failed" or et == "error":
                        err = ev.get("response", {}).get("error") or ev.get("error") or ev
                        raise RuntimeError(f"OpenClaw/Codex respondió error: {err}")

        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    async def ping(self) -> bool:
        try:
            r = await self.chat([{"role": "user", "content": "ping"}])
            return isinstance(r.content, str)
        except Exception:
            return False
