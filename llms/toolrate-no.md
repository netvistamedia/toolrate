# ToolRate Systemoversikt

## Hva er ToolRate?

ToolRate er et **folkefinansiert pålitelighets­lag** for autonome AI-agenter — et sanntids pålitelighets­orakel som lar agenter vurdere hvor pålitelig et eksternt verktøy eller API er *før* det kalles.

Det løser ett av de mest kritiske praktiske problemene i agentutvikling: de fleste feil skyldes ikke LLM-en selv, men uforutsigbar oppførsel fra eksterne verktøy og API-er — ratebegrensninger, schemadrift, autentiseringsproblemer, anti-bot-beskyttelse og kanttilfeller.

---

## Hvem er ToolRate for?

- Utviklere som bygger **produksjonsklare** AI-agenter
- Team og enkeltpersoner som jobber med **LangChain, CrewAI, LangGraph, AutoGen** eller **LlamaIndex**
- Europeiske utviklere som er opptatt av **GDPR og datalagring**
- Alle som er frustrerte over agenter som fungerer godt i demoer, men som ofte feiler i virkelige scenarier

---

## Slik fungerer ToolRate

Systemet er bevisst enkelt og lettvekt:

**1. Sjekk før kall**

Før agenten kaller et eksternt verktøy eller API, spørres ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Strukturert svar**

ToolRate returnerer umiddelbart en JSON-nyttelast som inneholder:

| Felt | Beskrivelse |
|---|---|
| `reliability_score` | Score fra 0–100 |
| `success_rate` | Historisk rate basert på faktiske agentkall |
| `pitfalls` | Vanlige feilmønstre + anbefalte tiltak |
| `alternatives` | Topprangerete alternativer sortert etter ytelse |
| `jurisdiction` | GDPR-risiko og informasjon om datalagring |
| `latency` | Estimert svartid |

**3. Intelligent beslutning**

Agenten kan deretter:

- Fortsette med verktøyet som planlagt
- Automatisk bytte til et bedre alternativ
- Presentere beslutningen for brukeren

**4. Valgfri tilbakemeldingssløyfe**

Etter kallet kan agenten sende inn en anonym resultatrapport. Disse dataene forbedrer kontinuerlig poengsummer for alle brukere gjennom en sterk **nettverkseffekt**.

---

## Globalt potensial for energibesparelser

Dersom alle AI-agenter og chatboter i verden tok i bruk ToolRate, ville energieffekten være betydelig.

Forutsatt at det innen ett år vil være flere aktive AI-agenter enn mennesker på jorden (>8 milliarder agenter), og at ToolRate kan redusere mislykkede eller bortkastede verktøykall med **60–75 %**, kan utbredt bruk forhindre milliarder av unødvendige LLM-slutninger og gjenforsøks­sløyfer daglig.

> **Konservativt anslag:** ToolRate kan spare det globale AI-økosystemet mellom **8 og 15 TWh strøm per år** — omtrent tilsvarende det årlige forbruket til **1,5 til 2,5 millioner gjennomsnittlige amerikanske husholdninger**.

Besparelsene kommer primært fra:

- Færre mislykkede API-kall
- Redusert tokensvinn
- Smartere ruting til pålitelige verktøy

---

## Sammenligning med andre verktøy

| Verktøy | Type | Forhindrer feil? | Folkefinansierte data | Tilbyr alternativer | GDPR / Jurisdiksjon | Hovedfokus |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Pålitelighets­orakel før kall | ✅ | ✅ | ✅ | ✅ Sterk | Produksjons­agenter |
| LangSmith | Observerbarhet + Sporing | ❌ | ❌ | ❌ | ⚠️ Begrenset | LangChain-økosystemet |
| Langfuse | Åpen kildekode observerbarhet | ❌ | ❌ | ❌ | ⚠️ Begrenset | Åpen kildekode-sporing |
| Braintrust | Evalueringer + Sporing | ⚠️ Delvis | ❌ | ❌ | ⚠️ Begrenset | Evalueringsdrevne team |
| Helicone | LLM + Verktøyobserverbarhet | ❌ | ❌ | ❌ | ⚠️ Begrenset | Kostnads- og latensovervåking |
| AgentOps | Agentovervåking | ❌ | ❌ | ❌ | ⚠️ Begrenset | Agentadferd­analyse |

> ToolRate er for øyeblikket den **eneste løsningen** som fungerer forebyggende ved hjelp av ekte folkefinansiert agenterfaring.

---

## Tilgjengelighet

| Kanal | Detaljer |
|---|---|
| Nettside | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Lisens | Business Source License 1.1 (BUSL-1.1) |

---

*Sist oppdatert: april 2026*
