# ⚙️ AgentOS — Sistema de Configuración

> **Versión:** 2.0  
> **Arquitectura:** Hub + Agentes independientes  
> **Propósito:** Cómo se configura AgentOS y cada agente

---

## 1. Estructura de configuración

AgentOS tiene dos niveles de configuración:

```text
NIVEL 1 — Config del Hub (global)
  C:\AgentOS\config.yaml
  → Puerto, directorio de templates, pool de LLM, etc.

NIVEL 2 — Config de cada agente (individual)
  D:\Agentes\R2 PRIME\config.yaml
  → Personalidad, proveedor LLM, tools, canales, sandbox
```

Cada agente es completamente independiente.

---

## 2. Config del Hub

```yaml
# C:\AgentOS\config.yaml
hub:
  name: "AgentOS"
  port: 8234
  templates_dir: "C:\\AgentOS\\templates"
  log_dir: "C:\\AgentOS\\logs"

  port_range:
    start: 9000
    end: 9999

  health_check:
    interval_seconds: 15
    timeout_seconds: 5
    auto_restart: true

  api_keys:                     # Keys globales (hereda el agente si no tiene propia)
    openai: "${OPENAI_API_KEY}"
    anthropic: "${ANTHROPIC_API_KEY}"
    google: "${GOOGLE_API_KEY}"
  
  api_key_inheritance: true     # Los agentes heredan si no especifican la suya
```

---

## 3. Config de cada agente

```yaml
# D:\Agentes\R2 PRIME\config.yaml
agent:
  name: "R2 PRIME"
  description: "Asistente personal de Xavier"
  install_path: "D:\\Agentes\\R2 PRIME"
  port: 9001
  status: online

personality:
  tone: "directo"               # directo | formal | profesional | divertido | cálido
  humor: "sarcástico"           # ninguno | poco | natural | sarcástico
  empathy: "leal"               # fría | profesional | cálida | muy_cálida | leal
  formality: "tú"               # tú | usted
  system_prompt: "Eres R2 PRIME, el asistente personal de Xavier..."

llm:
  provider: ollama              # ollama | openai | anthropic | google | custom
  api_key: ""                   # Vacío si usa Ollama o hereda del Hub
  model: qwen2.5:7b
  temperature: 0.7
  host: http://localhost:11434  # Ollama o endpoint custom

tools:
  allow:
    - read_file
    - write_file
    - list_files
    - search_web
    - fetch_url
    - save_memory
    - get_memory
    - read_document             # PDF, DOCX, TXT, CSV, XLSX
    - read_image                # Visión con LLM
    - read_audio                # Transcripción whisper
    - exec_command              # Solo Nivel 3
    - send_whatsapp
  deny: []

security:
  level: 3                      # 0 (solo habla) | 1 (lectura) | 2 (lectura+escritura) | 3 (todo)
  sandbox:
    paths:
      - D:\\Agentes\\R2 PRIME\\data\\

files:
  max_upload_size_mb: 50
  allowed_extensions:
    - .txt .pdf .docx .xlsx .jpg .png .webp .mp3 .wav
    - .csv .json .xml .py .js .html .css .md .yaml .log

channels:
  web: true
  whatsapp:
    enabled: true
    phone: "+573192270876"
  telegram:
    enabled: false

auto_restart: true
```

---

## 4. Ubicación de los agentes

Cada agente se instala donde el usuario eligió al crearlo. El Hub mantiene un registro en `C:\AgentOS\data\agents.json`:

```json
{
  "r2-prime": {
    "name": "R2 PRIME",
    "install_path": "D:\\Agentes\\R2 PRIME",
    "port": 9001,
    "status": "online"
  },
  "abogado-laboral": {
    "name": "Abogado Laboral",
    "install_path": "C:\\Users\\Xavier\\Documents\\Bufete",
    "port": 9002,
    "status": "online"
  }
}
```

---

## 5. Personalización de un agente

Desde la ventana de configuración de AgentOS puedes cambiar cualquier parámetro. Los cambios en LLM, tools o personalidad requieren reiniciar el agente.

Los cambios en `files.allowed_extensions`, `security.sandbox` o `channels` se aplican al instante (sin reinicio).

---

## 6. Tools personalizadas por agente

Los archivos Python en `{agent_dir}/tools/` se cargan automáticamente al iniciar el agente:

```python
# D:\Agentes\R2 PRIME\tools\mi_tool.py

@tool(name="consultar_clima", 
      description="Consulta el clima de una ciudad")
def consultar_clima(ciudad: str) -> dict:
    """Tool personalizada solo para este agente."""
    import requests
    r = requests.get(f"https://api.weatherapi.com/.../{ciudad}")
    return r.json()
```

Sin registro manual. Sin compilación. Solo crear el archivo.
