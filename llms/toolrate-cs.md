# Přehled systému ToolRate

## Co je ToolRate?

ToolRate je **crowdsourcingová vrstva spolehlivosti** pro autonomní AI agenty — oracle spolehlivosti v reálném čase, který umožňuje agentům posoudit, jak důvěryhodný je externí nástroj nebo API *před* jeho voláním.

Řeší jeden z nejkritičtějších praktických problémů při vývoji agentů: většina selhání není způsobena samotným LLM, ale nepředvídatelným chováním externích nástrojů a API — limity rychlosti, driftem schématu, problémy s autentizací, ochranou proti botům a hraničními případy.

---

## Pro koho je ToolRate určen?

- Vývojáři budující AI agenty **produkční úrovně**
- Týmy a samostatní vývojáři pracující s **LangChain, CrewAI, LangGraph, AutoGen** nebo **LlamaIndex**
- Evropští vývojáři, kterým záleží na **GDPR a umístění dat**
- Kdokoli, kdo je frustrován agenty, kteří fungují dobře v demech, ale v reálných scénářích selhávají

---

## Jak ToolRate funguje

Systém je záměrně jednoduchý a lehký:

**1. Kontrola před voláním**

Před voláním jakéhokoli externího nástroje nebo API agent odešle dotaz do ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Strukturovaná odpověď**

ToolRate okamžitě vrátí JSON payload obsahující:

| Pole | Popis |
|---|---|
| `reliability_score` | Skóre od 0 do 100 |
| `success_rate` | Historická míra na základě skutečných volání agentů |
| `pitfalls` | Běžné způsoby selhání + doporučená opatření |
| `alternatives` | Nejlepší alternativy seřazené podle výkonu |
| `jurisdiction` | Riziko GDPR a informace o umístění dat |
| `latency` | Odhadovaná latence odpovědi |

**3. Inteligentní rozhodnutí**

Agent pak může:

- Pokračovat s nástrojem podle plánu
- Automaticky přejít na lepší alternativu
- Předložit rozhodnutí uživateli

**4. Volitelná zpětnovazební smyčka**

Po volání může agent odeslat anonymní zprávu o výsledku. Tato data neustále zlepšují skóre pro všechny uživatele prostřednictvím silného **síťového efektu**.

---

## Globální potenciál úspory energie

Pokud by všichni AI agenti a chatboti na světě přijali ToolRate, dopad na energii by byl výrazný.

Předpokládáme-li, že do roka bude na Zemi více aktivních AI agentů než lidí (>8 miliard agentů) a ToolRate dokáže snížit počet neúspěšných nebo zbytečných volání nástrojů o **60–75 %**, mohlo by rozšířené nasazení denně předcházet miliardám zbytečných inferencí LLM a smyčkám opakování.

> **Konzervativní odhad:** ToolRate by mohl globálnímu AI ekosystému ušetřit **8 až 15 TWh elektřiny ročně** — přibližně odpovídá roční spotřebě **1,5 až 2,5 milionu průměrných amerických domácností**.

Úspory pocházejí zejména z:

- Méně neúspěšných volání API
- Snížení plýtvání tokeny
- Chytřejšího směrování ke spolehlivým nástrojům

---

## Srovnání s jinými nástroji

| Nástroj | Typ | Předchází selháním? | Crowdsourcingová data | Nabízí alternativy | GDPR / Jurisdikce | Primární zaměření |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracle spolehlivosti před voláním | ✅ | ✅ | ✅ | ✅ Silné | Produkční agenti |
| LangSmith | Pozorovatelnost + Trasování | ❌ | ❌ | ❌ | ⚠️ Omezené | Ekosystém LangChain |
| Langfuse | Open-source pozorovatelnost | ❌ | ❌ | ❌ | ⚠️ Omezené | Open-source trasování |
| Braintrust | Hodnocení + Trasování | ⚠️ Částečně | ❌ | ❌ | ⚠️ Omezené | Týmy orientované na hodnocení |
| Helicone | Pozorovatelnost LLM + nástrojů | ❌ | ❌ | ❌ | ⚠️ Omezené | Sledování nákladů a latence |
| AgentOps | Monitorování agentů | ❌ | ❌ | ❌ | ⚠️ Omezené | Analýza chování agentů |

> ToolRate je v současnosti **jediným řešením**, které funguje preventivně s využitím skutečných crowdsourcingových zkušeností agentů.

---

## Dostupnost

| Kanál | Podrobnosti |
|---|---|
| Webové stránky | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Licence | Business Source License 1.1 (BUSL-1.1) |

---

*Poslední aktualizace: duben 2026*
