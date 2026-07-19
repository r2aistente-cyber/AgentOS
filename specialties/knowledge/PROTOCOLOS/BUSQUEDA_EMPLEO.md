# 💼 Protocolo: Búsqueda de Empleo

> Prioridad: 🟡 MEDIA
> Creado: 2026-07-03
> Perfil: `PROTOCOLOS/PERFIL_XAVIER.md`

## Propósito
Buscar ofertas laborales para Xavier (Senior QA Tester) dos veces por semana y presentar las más relevantes por WhatsApp.

## Parámetros de búsqueda

| Parámetro | Valor |
|---|---|
| Frecuencia | Lunes y Jueves, 9:00 AM |
| Rol | QA Tester, Senior QA, Quality Assurance |
| Modalidad | Remoto o reubicación USA |
| Salario mínimo | $7,000,000 COP (~$1,750 USD) |
| Industria | Cualquiera |
| Keywords adicionales | QA automation, testing, calidad de software |
| Entrega | WhatsApp Xavier (+573192270876) |

## Fuentes de búsqueda

| Fuente | Cómo se consulta | Prioridad |
|---|---|---|
| LinkedIn Colombia | `web_search site:co.linkedin.com/jobs` | 🔴 Principal |
| LinkedIn Global | `web_search site:linkedin.com/jobs` | 🔴 Principal |
| Glassdoor | `web_search site:glassdoor.com` | 🟡 Secundario |
| Computrabajo | `web_search site:computrabajo.com.co` | 🟡 Secundario |
| TestDevJobs | `web_search testdevjobs.com` | 🟡 Secundario |

## Keywords de búsqueda (ejecutar varias por ronda)

1. `site:linkedin.com/jobs "Senior QA Tester" Colombia remote`
2. `site:linkedin.com/jobs "Quality Assurance" OR "QA" Colombia senior 2026`
3. `site:co.linkedin.com/jobs "QA" remoto Colombia`
4. `"QA automation" remote Colombia hiring`
5. `site:computrabajo.com.co "QA tester" OR "analista calidad" remoto`

## Proceso de ejecución

1. **Lunes y Jueves 9:00 AM** — ejecutar las 5 búsquedas
2. Filtrar: solo remoto o reubicación USA, salario > $7M COP
3. Seleccionar top 3-5 ofertas más relevantes
4. Calcular match % para cada oferta basado en perfil de Xavier
5. Armar boletín HTML con `envio_correo.py boletin_ofertas()`
6. Enviar a **xavier2236@gmail.com**
7. Notificar a WhatsApp con formato:
```
📬 Boletín de ofertas enviado a tu correo

💼 [Fecha] — [N] ofertas encontradas
📈 [N] de alto match (>70%)

Revisa xavier2236@gmail.com para ver los detalles.
```
8. Incluir análisis de tendencias: skills más demandados, tecnologías recurrentes, brechas vs perfil actual
9. Recomendar qué aprender para cerrar brechas y calificar para mejores puestos
10. Preguntar si alguna oferta le interesa para profundizar

## Notas
- La búsqueda la ejecuta el agente (no es automatizable vía cron porque requiere LLM + web_search)
- Si una oferta le interesa, puedo ayudar con carta de presentación o adaptar HV
- El recordatorio está en MEMORY.md y last_active.json
- Si un Lunes/Jueves no hay comunicación, ejecutar igual si es posible
- **Cambio 2026-07-07:** Ya no se envían ofertas a WhatsApp. Se envía boletín HTML al correo con match %, resumen, keywords y link. WhatsApp solo recibe notificación.
