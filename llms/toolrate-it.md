# Panoramica del sistema ToolRate

## Cos'è ToolRate?

ToolRate è uno **strato di affidabilità collaborativo** per agenti AI autonomi — un oracolo di affidabilità in tempo reale che consente agli agenti di valutare l'attendibilità di uno strumento esterno o di un'API *prima* di invocarla.

Risolve uno dei problemi pratici più critici nello sviluppo di agenti: la maggior parte dei fallimenti non è causata dall'LLM stesso, ma dal comportamento imprevedibile di strumenti e API esterne — limiti di frequenza, deriva dello schema, problemi di autenticazione, protezioni anti-bot e casi limite.

---

## A chi è destinato ToolRate?

- Sviluppatori che costruiscono agenti AI **pronti per la produzione**
- Team e sviluppatori indipendenti che lavorano con **LangChain, CrewAI, LangGraph, AutoGen** o **LlamaIndex**
- Sviluppatori europei attenti al **GDPR e alla residenza dei dati**
- Chiunque sia frustrato da agenti che funzionano bene nelle demo ma falliscono frequentemente in scenari reali

---

## Come funziona ToolRate

Il sistema è volutamente semplice e leggero:

**1. Verifica pre-chiamata**

Prima di invocare qualsiasi strumento o API esterna, l'agente interroga ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Risposta strutturata**

ToolRate restituisce immediatamente un payload JSON contenente:

| Campo | Descrizione |
|---|---|
| `reliability_score` | Punteggio da 0 a 100 |
| `success_rate` | Tasso storico basato su chiamate reali degli agenti |
| `pitfalls` | Modi di guasto comuni + mitigazioni consigliate |
| `alternatives` | Migliori alternative classificate per prestazioni |
| `jurisdiction` | Rischio GDPR e informazioni sulla residenza dei dati |
| `latency` | Latenza di risposta stimata |

**3. Decisione intelligente**

L'agente può quindi:

- Procedere con lo strumento come pianificato
- Passare automaticamente a un'alternativa migliore
- Presentare la decisione all'utente

**4. Ciclo di feedback opzionale**

Dopo la chiamata, l'agente può inviare un rapporto anonimo sui risultati. Questi dati migliorano continuamente i punteggi per tutti gli utenti grazie a un forte **effetto di rete**.

---

## Potenziale globale di risparmio energetico

Se tutti gli agenti AI e i chatbot nel mondo adottassero ToolRate, l'impatto energetico sarebbe significativo.

Supponendo che entro un anno ci siano più agenti AI attivi che esseri umani sulla Terra (>8 miliardi di agenti), e che ToolRate possa ridurre le chiamate fallite o inutili del **60–75 %**, un'adozione diffusa potrebbe prevenire quotidianamente miliardi di inferenze LLM non necessarie e cicli di ripetizione.

> **Stima conservativa:** ToolRate potrebbe far risparmiare all'ecosistema AI globale tra **8 e 15 TWh di elettricità all'anno** — equivalente circa al consumo annuo di **1,5 fino a 2,5 milioni di famiglie americane medie**.

I risparmi derivano principalmente da:

- Meno chiamate API fallite
- Riduzione dello spreco di token
- Instradamento più intelligente verso strumenti affidabili

---

## Confronto con altri strumenti

| Strumento | Tipo | Previene i fallimenti? | Dati collaborativi | Fornisce alternative | GDPR / Giurisdizione | Focus principale |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracolo di affidabilità pre-chiamata | ✅ | ✅ | ✅ | ✅ Forte | Agenti in produzione |
| LangSmith | Osservabilità + Tracciamento | ❌ | ❌ | ❌ | ⚠️ Limitato | Ecosistema LangChain |
| Langfuse | Osservabilità open source | ❌ | ❌ | ❌ | ⚠️ Limitato | Tracciamento open source |
| Braintrust | Valutazioni + Tracciamento | ⚠️ Parzialmente | ❌ | ❌ | ⚠️ Limitato | Team orientati alla valutazione |
| Helicone | Osservabilità LLM + Strumenti | ❌ | ❌ | ❌ | ⚠️ Limitato | Monitoraggio costi e latenza |
| AgentOps | Monitoraggio agenti | ❌ | ❌ | ❌ | ⚠️ Limitato | Analisi del comportamento degli agenti |

> ToolRate è attualmente la **unica soluzione** che opera in modo preventivo utilizzando la vera esperienza collaborativa degli agenti.

---

## Disponibilità

| Canale | Dettagli |
|---|---|
| Sito web | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| SDK Python | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| SDK TypeScript | `npm install toolrate` |
| Licenza | Business Source License 1.1 (BUSL-1.1) |

---

*Ultimo aggiornamento: aprile 2026*
