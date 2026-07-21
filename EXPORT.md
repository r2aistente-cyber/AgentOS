# 📦 AgentOS — Exportación de Agentes

> **Versión:** 1.0  
> **Propósito:** Permitir que agentes creados en el Hub se exporten como paquetes independientes y se desplieguen en cualquier máquina.

---

## 1. El problema

Hoy los agentes viven dentro del Hub. Si quieres que un agente experto en POS maneje 5 POS distintos en 5 máquinas diferentes, no puedes — el agente está atado al Hub.

```text
ASÍ NO:                        ASÍ SÍ:
┌──────────┐                   ┌──────────┐
│   HUB    │                   │   HUB    │
│          │                   │          │
│  🤖 POS  │                   │  🎛️ Admin│
│  (solo)  │                   └──────────┘
└──────────┘                        │
                                    │ Exporta agentes
                          ┌─────────┼─────────┐
                          │         │         │
                          ▼         ▼         ▼
                     ┌────────┐ ┌────────┐ ┌────────┐
                     │🤖 POS  │ │🤖 POS  │ │🤖 POS  │
                     │Máq 1   │ │Máq 2   │ │Máq 3   │
                     └────────┘ └────────┘ └────────┘
```

---

## 2. ¿Qué es un agente exportado?

Un **snapshot completo del agente** — su personalidad, su conocimiento Y todo lo que ha aprendido.

```text
📦 agente-pos-v1.0.tar.gz     ← Un solo archivo
 ├── manifest.json             ← Metadatos (nombre, versión, autor)
 ├── specialty.json            ← Config del agente (personalidad, tools)
 │
 ├── engine/                   ← Motor mínimo (binario compilado)
 │   ├── r2-engine             ← Ejecutable (Rust, ~8 MB)
 │   └── config.yaml           ← Config del engine local
 │
 ├── knowledge/                ← Conocimiento del agente
 │   ├── docs/                 ← Documentos indexados
 │   └── index/                ← RAG index precalculado
 │
 ├── memory/                   ← 🧠 SU CEREBRO (todo lo aprendido)
 │   ├── sessions.db           ← Conversaciones completas
 │   ├── long_term.db          ← Memoria a largo plazo (clave-valor)
 │   ├── learnings.db          ← Patrones aprendidos, preferencias
 │   └── feedback.db           ← Correcciones que ha recibido
 │
 ├── audit/                    ← 📋 HISTORIAL DE ACCIONES
 │   └── audit.log             ← Todo lo que ha hecho (inmodificable)
 │
 └── app/                     ← 🖥️ App nativa (Tauri, como el Hub)
     └── R2 Agent.app          ← .app / .exe según SO
                                ← Icono en bandeja del sistema
                                ← Sin navegador, sin terminal
```

**Exportar = clonar el cerebro.** Cuando importas en otra máquina, el agente recuerda
todo: conversaciones anteriores, preferencias del usuario, lecciones aprendidas.

---

## 3. El Hub como tienda de agentes

El Hub se convierte en un marketplace/gestor de agentes:

```text
┌─────────────────────────────────────────────────┐
│                   🏪 AGENT HUB                   │
│                                                   │
│  Agentes instalados:                              │
│  ┌───────────────────────────────────────────┐   │
│  │ 🤖 R2 Core         │ v1.0 │ 🟢 Activo    │   │
│  │ 🤖 POS Expert      │ v2.3 │ 🟢 Activo    │   │
│  │ 🤖 Legal Assistant  │ v1.5 │ ⏸️ Detenido │   │
│  │ 🤖 Marketing Agent  │ v0.9 │ 🧪 Beta     │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  Acciones por agente:                             │
│  ┌───────────────────────────────────────────┐   │
│  │ [▶ Iniciar] [⏹ Detener] [⚙️ Config]      │   │
│  │ [📦 Exportar] [📋 Logs] [🗑️ Eliminar]    │   │
│  └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Exportar un agente** → genera el `.tar.gz` listo para copiar.

**Importar un agente** → desde el `.tar.gz` se despliega en 1 clic.

---

## 4. Despliegue en máquina destino

### 4.1 Manual (copiar y ejecutar)

```bash
# En la máquina destino (Windows, Mac, Linux):
$ r2 import agente-pos-v1.0.tar.gz
✓ Importando agente POS Expert...
✓ Engine instalado
✓ App nativa creada
✓ Icono en la bandeja del sistema

# O directamente:
$ r2 run agente-pos-v1.0.tar.gz
✓ POS Expert corriendo
✓ Icono 🤖 en el menú
✓ Cmd+Space para abrir/cerrar
```

**El usuario NO abre un navegador.** Ve un icono en su bandeja del sistema,
hace click y habla con el agente como cualquier app nativa.

### 4.2 Script de instalación

Dentro del `.tar.gz` viene un script que hace todo:

```bash
# El usuario solo hace:
$ ./install.sh
```

### 4.3 Sin dependencias

La máquina destino **no necesita**:
- ❌ Python
- ❌ Node.js
- ❌ Docker
- ❌ Nada

El engine está compilado (Rust) y es autónomo. Solo necesita el modelo LLM (Ollama local o API cloud configurable).

---

## 5. ¿Cómo se conecta al modelo LLM?

Cada agente exportado puede configurarse para usar:

```yaml
# En la máquina destino, el usuario configura:
llm:
  provider: ollama          # ollama | openai | anthropic
  model: qwen2.5:7b
  host: http://localhost:11434
```

O si la máquina no tiene GPU, puede apuntar a un servidor LLM remoto:

```yaml
llm:
  provider: ollama
  model: qwen2.5:7b
  host: http://192.168.0.100:11434   # LLM en otra máquina de la red
```

---

## 6. El agente POS en acción

```text
Flujo completo:

1️⃣ CREACIÓN EN EL HUB
   Abres Agent Hub → Creas agente "POS Expert"
   → Le das personalidad de bartender
   → Le conectas las tools del POS (get_sales, check_inventory)
   → Le subes documentos del negocio
   → Click [📦 Exportar]
   → Obtienes: agente-pos-v1.0.tar.gz

2️⃣ DESPLIEGUE EN MÁQUINA 1 (POS del bar)
   Copias el .tar.gz al PC del bar
   $ r2 import agente-pos-v1.0.tar.gz
   Configuras: puerto local, modelo Ollama
   → Icono 🤖 en la bandeja del sistema
   → Clic → Hablas con el agente
   → Se conecta al POS local automáticamente

3️⃣ DESPLIEGUE EN MÁQUINA 2 (otro bar)
   Copias el mismo .tar.gz a otro PC
   $ r2 import agente-pos-v1.0.tar.gz
   Misma configuración, distinta máquina
   → El agente se conecta a ese POS específico

4️⃣ ACTUALIZACIÓN
   Mejoras el agente en el Hub
   → Nueva versión: agente-pos-v2.0.tar.gz
   → Lo copias a todas las máquinas
   → $ r2 update agente-pos-v2.0.tar.gz
```

---

## 7. El engine compilado

El motor que corre dentro del agente exportado:

```text
engine/
├── r2-engine                  ← Binario único (Rust, compilado estático)
│                              ← ~8 MB, sin dependencias externas
│
├── config.yaml                ← Puertos, LLM, canales
│
├── specialties/               ← Especialidad del agente
│   └── pos-expert.json
│
└── knowledge/                 ← Conocimiento (RAG pre-indexado)
    ├── docs/
    └── index/
```

El engine es el mismo para todos los agentes. Lo que cambia es:
- `specialty.json` → define personalidad y herramientas
- `knowledge/` → define qué sabe
- `config.yaml` → define conectividad

**Un solo binario, infinitas personalidades.**

---

## 8. Versiones y actualizaciones

```text
agente-pos-v1.0.tar.gz
agente-pos-v1.1.tar.gz    ← Bugfix
agente-pos-v2.0.tar.gz    ← Nuevas herramientas
```

En el Hub se lleva control de versiones. Puedes:
- Exportar cualquier versión anterior
- Comparar cambios entre versiones
- Hacer rollback en una máquina

---

## 9. Seguridad

```yaml
# El agente exportado hereda la seguridad del engine:
security:
  sandbox_paths:
    - /home/pos/data/         # Solo accede a datos del POS
    - /tmp/r2-temp/
  permission_level: 1         # Solo lectura por defecto
  no_exec: true               # Sin exec_command
```

El agente exportado es **más limitado que el del Hub** porque no tiene `exec_command`, no tiene acceso al sistema, solo a su sandbox.

---

## 10. Resumen

```text
📦 EXPORTAR AGENTE
  Hub → [Exportar] → agente-pos-v1.0.tar.gz

🚀 DESPLEGAR
  $ r2 import agente-pos-v1.0.tar.gz
  ✓ Listo en 5 segundos

🔄 ACTUALIZAR
  $ r2 update agente-pos-v2.0.tar.gz
  ✓ Sin perder configuración local

🔌 REQUISITOS MÍNIMOS
  • Sistema operativo (Windows/Mac/Linux)
  • Ollama (o API key si usa cloud)
  • Nada más
  • ❌ Sin navegador — app nativa
  • ❌ Sin terminal — icono en bandeja
```

---

## 11. Checklist para Trantor

- [ ] `r2 export` en Hub → genera `.tar.gz` con app nativa incluida
- [ ] `r2 import <package.tar.gz>` → extrae + instala app en bandeja
- [ ] `r2 run` → inicia engine + app nativa (icono en sistema)
- [ ] `r2 update <package.tar.gz>` → actualiza sin perder memoria
- [ ] App nativa empaquetada dentro del `.tar.gz`
- [ ] Instalación sin navegador, sin terminal
- [ ] Engine mínimo compilado (Rust, sin dependencias)
- [ ] Cross-platform: .dmg (Mac) / .exe (Win) / .AppImage (Linux)
