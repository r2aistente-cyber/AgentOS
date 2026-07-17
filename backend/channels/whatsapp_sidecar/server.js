/**
 * R2 Autonomous — WhatsApp Sidecar
 * Puerto: 3099
 *
 * Endpoints:
 *   GET  /status          → estado de la conexión
 *   GET  /qr              → QR code (string) si no está conectado
 *   POST /send            → { to, message } → envía mensaje
 *   POST /webhook         → registrar URL de incoming messages
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());

const PORT = process.env.SIDECAR_PORT || 3099;
const SESSION_DIR = process.env.SESSION_DIR || './.ww_session';

let currentQR = null;
let isConnected = false;
let webhookUrl = null;

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  },
});

client.on('qr', (qr) => {
  currentQR = qr;
  isConnected = false;
  qrcode.generate(qr, { small: true });
  console.log('[R2-WA] QR generado. Escanea con WhatsApp.');
});

client.on('ready', () => {
  isConnected = true;
  currentQR = null;
  console.log('[R2-WA] Conectado.');
});

client.on('disconnected', (reason) => {
  isConnected = false;
  console.log('[R2-WA] Desconectado:', reason);
  setTimeout(() => client.initialize(), 5000);
});

client.on('message', async (msg) => {
  if (!webhookUrl) return;
  try {
    const payload = {
      channel: 'whatsapp',
      sender: msg.from,
      chat_id: msg.from,
      text: msg.body,
      timestamp: msg.timestamp,
    };
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    console.error('[R2-WA] Error enviando webhook:', e.message);
  }
});

client.initialize();

// ─── REST API ─────────────────────────────────────────────────────────────

app.get('/status', (req, res) => {
  res.json({
    connected: isConnected,
    has_qr: !!currentQR,
    sidecar: 'online',
    webhook: webhookUrl,
  });
});

app.get('/qr', (req, res) => {
  if (isConnected) return res.json({ qr: null, connected: true });
  if (!currentQR) return res.status(202).json({ qr: null, message: 'Esperando QR...' });
  res.json({ qr: currentQR });
});

app.post('/send', async (req, res) => {
  const { to, message } = req.body;
  if (!to || !message) return res.status(400).json({ error: 'to y message requeridos' });
  if (!isConnected) return res.status(503).json({ error: 'WhatsApp no conectado' });

  // Seguridad: no enviar a números sueltos sin @g.us o @c.us
  const target = to.includes('@') ? to : `${to.replace(/\D/g, '')}@c.us`;

  try {
    await client.sendMessage(target, message);
    res.json({ ok: true, to: target });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/webhook', (req, res) => {
  const { url } = req.body;
  webhookUrl = url || null;
  res.json({ ok: true, webhook: webhookUrl });
});

app.listen(PORT, () => {
  console.log(`[R2-WA] Sidecar escuchando en :${PORT}`);
});
