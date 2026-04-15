# ToolRate Systeemoverzicht

## Wat is ToolRate?

ToolRate is een **crowdsourced betrouwbaarheidslaag** voor autonome AI-agenten — een realtime betrouwbaarheidsorakel waarmee agenten kunnen beoordelen hoe betrouwbaar een extern hulpmiddel of API is *voordat* het wordt aangeroepen.

Het lost een van de meest kritieke praktische problemen bij agentsontwikkeling op: de meeste fouten worden niet veroorzaakt door het LLM zelf, maar door onvoorspelbaar gedrag van externe tools en API's — limieten op aanvraagfrequentie, schemadrift, authenticatieproblemen, anti-bot-beveiliging en randgevallen.

---

## Voor wie is ToolRate?

- Ontwikkelaars die **productieklare** AI-agenten bouwen
- Teams en individuele ontwikkelaars die werken met **LangChain, CrewAI, LangGraph, AutoGen** of **LlamaIndex**
- Europese ontwikkelaars die waarde hechten aan **AVG en gegevenslocatie**
- Iedereen die gefrustreerd is door agenten die het goed doen in demo's, maar in de praktijk regelmatig falen

---

## Hoe ToolRate werkt

Het systeem is bewust eenvoudig en lichtgewicht gehouden:

**1. Controle vóór aanroep**

Voordat een extern hulpmiddel of API wordt aangeroepen, raadpleegt de agent ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Gestructureerd antwoord**

ToolRate retourneert onmiddellijk een JSON-payload met daarin:

| Veld | Omschrijving |
|---|---|
| `reliability_score` | Score van 0–100 |
| `success_rate` | Historische slagingsratio op basis van echte agentaanroepen |
| `pitfalls` | Veelvoorkomende faalpatronen + aanbevolen tegenmaatregelen |
| `alternatives` | Beste alternatieven gerangschikt op prestaties |
| `jurisdiction` | AVG-risico en informatie over gegevenslocatie |
| `latency` | Geschatte responsvertraging |

**3. Intelligente beslissing**

De agent kan vervolgens:

- Doorgaan met het hulpmiddel zoals gepland
- Automatisch overschakelen naar een beter alternatief
- De beslissing aan de gebruiker voorleggen

**4. Optionele feedbacklus**

Na de aanroep kan de agent een anoniem resultatenrapport indienen. Deze gegevens verbeteren continu de scores voor alle gebruikers via een sterk **netwerkeffect**.

---

## Wereldwijd potentieel voor energiebesparing

Als alle AI-agenten en chatbots wereldwijd ToolRate zouden adopteren, zou de impact op het energieverbruik aanzienlijk zijn.

Ervan uitgaande dat er binnen een jaar meer actieve AI-agenten dan mensen op aarde zullen zijn (>8 miljard agenten), en dat ToolRate mislukte of verspilde tool-aanroepen met **60–75%** kan verminderen, zou wijdverbreide adoptie dagelijks miljarden onnodige LLM-inferenties en herhaallussen kunnen voorkomen.

> **Conservatieve schatting:** ToolRate kan het wereldwijde AI-ecosysteem tussen **8 en 15 TWh elektriciteit per jaar** besparen — ruwweg gelijkwaardig aan het jaarlijkse verbruik van **1,5 tot 2,5 miljoen gemiddelde Amerikaanse huishoudens**.

De besparingen komen voornamelijk van:

- Minder mislukte API-aanroepen
- Verminderde tokenverspilling
- Slimmere routering naar betrouwbare hulpmiddelen

---

## Vergelijking met andere tools

| Tool | Type | Voorkomt fouten? | Crowdsourced data | Biedt alternatieven | AVG / Jurisdictie | Primaire focus |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Betrouwbaarheidsorakel vóór aanroep | ✅ | ✅ | ✅ | ✅ Sterk | Productie-agenten |
| LangSmith | Observeerbaarheid + Tracering | ❌ | ❌ | ❌ | ⚠️ Beperkt | LangChain-ecosysteem |
| Langfuse | Open-source observeerbaarheid | ❌ | ❌ | ❌ | ⚠️ Beperkt | Open-source tracering |
| Braintrust | Evaluaties + Tracering | ⚠️ Gedeeltelijk | ❌ | ❌ | ⚠️ Beperkt | Evaluatiegedreven teams |
| Helicone | LLM + Tool-observeerbaarheid | ❌ | ❌ | ❌ | ⚠️ Beperkt | Kosten- en latentiebewaking |
| AgentOps | Agentbewaking | ❌ | ❌ | ❌ | ⚠️ Beperkt | Agentgedraganalyse |

> ToolRate is momenteel de **enige oplossing** die preventief werkt op basis van echte crowdsourced agentervaring.

---

## Beschikbaarheid

| Kanaal | Details |
|---|---|
| Website | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Licentie | Business Source License 1.1 (BUSL-1.1) |

---

*Laatst bijgewerkt: april 2026*
