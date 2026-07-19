/**
 * Sidecar de WhatsApp para AgentOS (r2-autonomous).
 *
 * Recibe mensajes de WhatsApp y los reenvía al agente via HTTP.
 * Responde con la reply del agente al remitente.
 *
 * Config via env:
 *   WA_SIDECAR_PORT     Puerto HTTP de este sidecar (default 3100)
 *   WA_AGENT_PORT       Puerto del agente FastAPI (default 9000)
 *   WA_AGENT_NAME       Nombre del agente (para logs)
 *   WA_SESSION_DIR      Ruta absoluta donde guardar la sesión (default ./wa_session)
 *   WA_ALLOWED_NUMBERS  Números permitidos, coma-separados, sin prefijo + (default = todos)
 *   WA_CHROME_PATH      Ruta a Chrome/Edge (opcional, auto-detectado)
 *   WA_WEB_VERSION      Versión de WhatsApp Web (default 2.3000.1043250633-alpha)
 *
 * Uso:
 *   node sidecar.js   (cwd = hub/templates/whatsapp/ para acceder a node_modules)
 */

const fs = require("fs");
const path = require("path");
const http = require("http");
const express = require("express");
const QRCode = require("qrcode");
const { Client, LocalAuth } = require("whatsapp-web.js");

const SIDECAR_PORT = parseInt(process.env.WA_SIDECAR_PORT || "3100");
const AGENT_PORT   = parseInt(process.env.WA_AGENT_PORT   || "9000");
const AGENT_NAME   = process.env.WA_AGENT_NAME   || "agent";
const SESSION_DIR  = process.env.WA_SESSION_DIR  || path.join(__dirname, "wa_session");
const ALLOWED_RAW  = process.env.WA_ALLOWED_NUMBERS || "";
const ALLOWED      = ALLOWED_RAW ? ALLOWED_RAW.split(",").map(n => n.trim().replace(/\D/g, "")) : [];
const WA_WEB_VER   = process.env.WA_WEB_VERSION || "2.3000.1043250633-alpha";

// ── Chrome ────────────────────────────────────────────────────────────────────
function findChrome() {
  const candidates = [
    process.env.WA_CHROME_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  return candidates.find(p => { try { return fs.existsSync(p); } catch { return false; } });
}

// ── Estado ────────────────────────────────────────────────────────────────────
let ready = false;
let lastQr = null;     // string raw del QR
let lastError = null;
let messagesIn = 0;
let messagesOut = 0;

// ── Cliente WhatsApp ──────────────────────────────────────────────────────────
fs.mkdirSync(SESSION_DIR, { recursive: true });

const chromePath = findChrome();
console.log(`[${AGENT_NAME}] sidecar arrancando — chrome: ${chromePath || "no encontrado"}`);
console.log(`[${AGENT_NAME}] sesión en: ${SESSION_DIR}`);

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
  webVersionCache: {
    type: "remote",
    remotePath: `https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/${WA_WEB_VER}.html`,
  },
  puppeteer: {
    headless: true,
    executablePath: chromePath,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
  },
});

client.on("qr", (qr) => {
  lastQr = qr;
  ready = false;
  console.log(`[${AGENT_NAME}] QR disponible — escanear con WhatsApp → Dispositivos vinculados`);
});

client.on("ready", () => {
  ready = true;
  lastQr = null;
  lastError = null;
  console.log(`[${AGENT_NAME}] ✅ WhatsApp conectado`);
});

client.on("auth_failure", (msg) => {
  lastError = `auth_failure: ${msg}`;
  console.error(`[${AGENT_NAME}] ❌ Auth falló:`, msg);
});

client.on("disconnected", (reason) => {
  ready = false;
  lastError = `disconnected: ${reason}`;
  console.warn(`[${AGENT_NAME}] ⚠️ Desconectado:`, reason);
  // Reconexión automática
  setTimeout(() => {
    console.log(`[${AGENT_NAME}] Reconectando...`);
    client.initialize().catch(e => { lastError = String(e?.message || e); });
  }, 5000);
});

client.on("message", async (msg) => {
  if (msg.isStatus || msg.fromMe) return;

  const senderNumber = msg.from.replace(/\D/g, "").replace(/^521/, "52");

  if (ALLOWED.length > 0 && !ALLOWED.some(n => senderNumber.endsWith(n) || n.endsWith(senderNumber))) {
    console.log(`[${AGENT_NAME}] Mensaje de número no autorizado: ${msg.from} — ignorado`);
    return;
  }

  messagesIn++;
  const text = msg.body;
  console.log(`[${AGENT_NAME}] ← ${msg.from}: ${text.slice(0, 80)}`);

  try {
    const reply = await forwardToAgent(text, msg.from);
    if (reply) {
      await msg.reply(reply);
      messagesOut++;
      console.log(`[${AGENT_NAME}] → ${msg.from}: ${reply.slice(0, 80)}`);
    }
  } catch (e) {
    console.error(`[${AGENT_NAME}] Error al procesar mensaje:`, e?.message || e);
    try { await msg.reply("⚠️ Error interno al procesar tu mensaje."); } catch {}
  }
});

// ── Comunicación con el agente ────────────────────────────────────────────────
function forwardToAgent(message, sessionId) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ message, session_id: sessionId, user_id: sessionId });
    const req = http.request({
      hostname: "127.0.0.1",
      port: AGENT_PORT,
      path: "/api/v1/chat",
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
    }, (res) => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => {
        try { resolve(JSON.parse(data).reply || ""); }
        catch { resolve(""); }
      });
    });
    req.on("error", reject);
    req.setTimeout(60000, () => { req.destroy(); reject(new Error("timeout")); });
    req.write(body);
    req.end();
  });
}

// Arrancar cliente (no romper el servidor HTTP si falla)
client.initialize().catch(e => {
  lastError = String(e?.message || e);
  console.error(`[${AGENT_NAME}] ⚠️ Error al inicializar cliente:`, lastError);
});
process.on("unhandledRejection", e => { lastError = String(e?.message || e); });

// ── HTTP API ──────────────────────────────────────────────────────────────────
const app = express();
app.use(express.json());

app.get("/status", (_req, res) => res.json({
  ready,
  waiting_qr: !!lastQr,
  error: lastError,
  agent: AGENT_NAME,
  agent_port: AGENT_PORT,
  messages_in: messagesIn,
  messages_out: messagesOut,
  chrome: chromePath || null,
}));

// QR como data URL PNG (listo para <img src="...">)
app.get("/qr", async (_req, res) => {
  if (!lastQr) return res.status(404).json({ error: "Sin QR disponible — ya conectado o no iniciado" });
  try {
    const dataUrl = await QRCode.toDataURL(lastQr, { width: 256, margin: 2 });
    res.json({ qr: lastQr, qr_image: dataUrl });
  } catch (e) {
    res.json({ qr: lastQr, qr_image: null });
  }
});

app.post("/stop", (_req, res) => {
  res.json({ ok: true });
  setTimeout(() => process.exit(0), 200);
});

app.listen(SIDECAR_PORT, () => {
  console.log(`[${AGENT_NAME}] HTTP sidecar en http://localhost:${SIDECAR_PORT}`);
});
