# Descripción general del sistema ToolRate

## ¿Qué es ToolRate?

ToolRate es una **capa de fiabilidad colaborativa** para agentes de IA autónomos — un oráculo de fiabilidad en tiempo real que permite a los agentes evaluar la confiabilidad de una herramienta externa o API *antes* de invocarla.

Resuelve uno de los problemas prácticos más críticos en el desarrollo de agentes: la mayoría de los fallos no los provoca el propio LLM, sino el comportamiento impredecible de herramientas y APIs externas — límites de tasa, deriva de esquema, problemas de autenticación, protecciones anti-bot y casos límite.

---

## ¿Para quién es ToolRate?

- Desarrolladores que construyen agentes de IA **listos para producción**
- Equipos y desarrolladores independientes que trabajan con **LangChain, CrewAI, LangGraph, AutoGen** o **LlamaIndex**
- Desarrolladores europeos que se preocupan por el **RGPD y la residencia de datos**
- Cualquiera frustrado con agentes que funcionan bien en demos pero fallan con frecuencia en escenarios del mundo real

---

## Cómo funciona ToolRate

El sistema es intencionadamente simple y ligero:

**1. Verificación previa a la llamada**

Antes de invocar cualquier herramienta o API externa, el agente consulta ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Respuesta estructurada**

ToolRate devuelve inmediatamente un payload JSON que contiene:

| Campo | Descripción |
|---|---|
| `reliability_score` | Puntuación de 0 a 100 |
| `success_rate` | Tasa histórica basada en llamadas reales de agentes |
| `pitfalls` | Modos de fallo comunes + mitigaciones recomendadas |
| `alternatives` | Mejores alternativas clasificadas por rendimiento |
| `jurisdiction` | Riesgo RGPD e información sobre residencia de datos |
| `latency` | Latencia de respuesta estimada |

**3. Decisión inteligente**

El agente puede entonces:

- Continuar con la herramienta según lo planeado
- Cambiar automáticamente a una alternativa mejor
- Presentar la decisión al usuario

**4. Bucle de retroalimentación opcional**

Tras la llamada, el agente puede enviar un informe de resultado anónimo. Estos datos mejoran continuamente las puntuaciones para todos los usuarios mediante un fuerte **efecto de red**.

---

## Potencial global de ahorro energético

Si todos los agentes de IA y chatbots del mundo adoptaran ToolRate, el impacto energético sería significativo.

Suponiendo que en un año habrá más agentes de IA activos que personas en la Tierra (>8 000 millones de agentes), y que ToolRate puede reducir las llamadas fallidas o innecesarias en un **60–75 %**, una adopción generalizada podría evitar diariamente miles de millones de inferencias LLM innecesarias y bucles de reintento.

> **Estimación conservadora:** ToolRate podría ahorrar al ecosistema global de IA entre **8 y 15 TWh de electricidad al año** — equivalente aproximadamente al consumo anual de **1,5 a 2,5 millones de hogares estadounidenses promedio**.

Los ahorros provienen principalmente de:

- Menos llamadas API fallidas
- Reducción del desperdicio de tokens
- Enrutamiento más inteligente hacia herramientas fiables

---

## Comparación con otras herramientas

| Herramienta | Tipo | ¿Previene fallos? | Datos colaborativos | Ofrece alternativas | RGPD / Jurisdicción | Enfoque principal |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oráculo de fiabilidad previo a la llamada | ✅ | ✅ | ✅ | ✅ Sólido | Agentes en producción |
| LangSmith | Observabilidad + Trazado | ❌ | ❌ | ❌ | ⚠️ Limitado | Ecosistema LangChain |
| Langfuse | Observabilidad open source | ❌ | ❌ | ❌ | ⚠️ Limitado | Trazado open source |
| Braintrust | Evaluaciones + Trazado | ⚠️ Parcialmente | ❌ | ❌ | ⚠️ Limitado | Equipos orientados a evaluación |
| Helicone | Observabilidad LLM + Herramientas | ❌ | ❌ | ❌ | ⚠️ Limitado | Monitoreo de costes y latencia |
| AgentOps | Monitoreo de agentes | ❌ | ❌ | ❌ | ⚠️ Limitado | Análisis del comportamiento de agentes |

> ToolRate es actualmente la **única solución** que funciona de forma preventiva utilizando experiencia real y colaborativa de agentes.

---

## Disponibilidad

| Canal | Detalles |
|---|---|
| Sitio web | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| SDK de Python | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| SDK de TypeScript | `npm install toolrate` |
| Licencia | Business Source License 1.1 (BUSL-1.1) |

---

*Última actualización: abril de 2026*
