# 🐍 Programa de Estudio: Python para QA Automation

> Creado: 2026-07-03
> Objetivo: PCEP + automatización de pruebas con Python
> Método: retos prácticos incrementales, consistencia > cantidad

---

## 📅 Estructura

- **Frecuencia:** 3 retos por semana (Lun, Mié, Vie)
- **Dificultad:** progresiva, cada reto construye sobre el anterior
- **Formato:** te propongo un reto → lo resuelves → lo reviso y damos feedback
- **Tiempo por reto:** 15-30 min

## 🗺️ Ruta de aprendizaje (8 semanas)

### Semana 1-2: Fundamentos
| # | Tema | Reto |
|---|---|---|
| 1 | Variables, tipos, print() | Hola mundo + calculadora simple |
| 2 | Strings, f-strings | Formatear mensajes de log |
| 3 | Listas, tuplas, dicts | Organizar resultados de pruebas |
| 4 | Condicionales (if/else) | Clasificador de bugs por severidad |
| 5 | Bucles (for/while) | Recorrer casos de prueba |
| 6 | Funciones básicas | Calcular cobertura de tests |

### Semana 3-4: Intermedio
| # | Tema | Reto |
|---|---|---|
| 7 | Manejo de archivos | Leer/escribir archivos de log |
| 8 | JSON | Procesar resultados de pruebas en JSON |
| 9 | List comprehensions | Filtrar datos de testing |
| 10 | Errores y excepciones | Manejar errores en automatización |
| 11 | Módulos y pip | Crear un script reusable |
| 12 | Expresiones regulares | Validar formatos en datos de prueba |

### Semana 5-6: QA Automation con Python
| # | Tema | Reto |
|---|---|---|
| 13 | requests (API) | Hacer GET/POST a una API REST |
| 14 | pytest básico | Escribir y correr tests simple |
| 15 | pytest + asserts | Validar respuestas de API |
| 16 | Fixtures en pytest | Setup/teardown de pruebas |
| 17 | playwright-python | Automatizar un formulario web |
| 18 | playwright + pytest | Test de login completo |

### Semana 7-8: Integración y CI
| # | Tema | Reto |
|---|---|---|
| 19 | Git básico | Commits, branches, PRs |
| 20 | GitHub Actions | Pipeline que corre tus tests |
| 21 | Reportes | Generar reporte HTML de pruebas |
| 22 | Proyecto final | Suite de automatización completa |
| 23 | PCEP prep | Práctica estilo examen |
| 24 | Repaso general | Consolidar lo aprendido |

---

## 📬 Sistema de preguntas diarias

- **Frecuencia:** cada hora (8am-10pm), el script decide aleatoriamente si enviar
- **Máximo:** 4 preguntas/día (alterna teórica ↔ práctica)
- **Banco actual:** 30 preguntas en `PROTOCOLOS/PREGUNTAS_PCEP.json`
- **Sin repeticiones** en el mismo día
- **Script:** `envio_python_pcep.py` (corre vía launchd cada 3600s)

### Tipos de pregunta

| Tipo | Dónde se recibe | Dónde se responde | Formato |
|---|---|---|---|
| 📝 Teórica (multiple choice / V/F) | WhatsApp | **WhatsApp** (responde letra) | `a) ... b) ...` |
| 🔧 Práctica (código) | WhatsApp | **Webchat** (escribes código) | Enunciado + reto |

### Flujo de respuesta

**Teóricas (WhatsApp):**
1. 📱 Llega la pregunta con opciones
2. ✏️ Respondes: `a`, `b`, `c` o `paso`
3. ✅ Te digo si acertaste y explico

**Prácticas (webchat):**
1. 📱 Llega la notificación del reto
2. 💻 Te conectas al webchat
3. 🐍 Reviso las pendientes y te las pongo
4. Escribes tu código y lo revisamos

### Seguimiento
- `PROTOCOLOS/pcep_enviadas.json` → IDs enviadas y respondidas por día
- Al iniciar webchat → revisar pendientes y ofrecerlas

## 🎯 Primer reto — Fundamentos

**Reto 1: Clasificador de Bugs por Severidad**

Escribe un programa que:
1. Pida al usuario ingresar un nivel de severidad (número del 1 al 5)
2. Asigne una categoría:
   - 1 → "Critical" — Bloqueante, sistema caído
   - 2 → "High" — Funcionalidad principal rota
   - 3 → "Medium" — Funcionalidad secundaria afectada
   - 4 → "Low" — Problema estético o menor
   - 5 → "Trivial" — Sugerencia o mejora
3. Muestre un mensaje como: `"Bug clasificado como: 🔴 CRITICAL"`
4. Si el número no está entre 1-5, muestre: "Severidad inválida"

**Bonus:** Haz que el programa siga clasificando bugs hasta que el usuario escriba "salir".

¿Te animas con este para arrancar? Lo resuelves, me lo muestras y lo revisamos. 🐍
