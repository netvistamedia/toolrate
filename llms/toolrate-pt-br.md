# Visão Geral do Sistema ToolRate

## O que é o ToolRate?

O ToolRate é uma **camada de confiabilidade baseada em colaboração coletiva** para agentes de IA autônomos — um oráculo de confiabilidade em tempo real que permite aos agentes avaliar o quão confiável é uma ferramenta externa ou API *antes* de chamá-la.

Ele resolve um dos problemas práticos mais críticos no desenvolvimento de agentes: a maioria das falhas não é causada pelo próprio LLM, mas pelo comportamento imprevisível de ferramentas e APIs externas — limites de taxa, deriva de esquema, problemas de autenticação, proteções anti-bot e casos extremos.

---

## Para quem é o ToolRate?

- Desenvolvedores que constroem agentes de IA de **nível de produção**
- Times e desenvolvedores independentes que trabalham com **LangChain, CrewAI, LangGraph, AutoGen** ou **LlamaIndex**
- Desenvolvedores europeus que se preocupam com **LGPD/GDPR e residência de dados**
- Qualquer pessoa frustrada com agentes que funcionam bem em demonstrações, mas falham com frequência em cenários do mundo real

---

## Como o ToolRate Funciona

O sistema é intencionalmente simples e leve:

**1. Verificação pré-chamada**

Antes de chamar qualquer ferramenta ou API externa, o agente consulta o ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Resposta estruturada**

O ToolRate retorna imediatamente um payload JSON contendo:

| Campo | Descrição |
|---|---|
| `reliability_score` | Pontuação de 0 a 100 |
| `success_rate` | Taxa histórica baseada em chamadas reais de agentes |
| `pitfalls` | Modos de falha comuns + mitigações recomendadas |
| `alternatives` | Principais alternativas classificadas por desempenho |
| `jurisdiction` | Risco de LGPD/GDPR e informações sobre residência de dados |
| `latency` | Latência de resposta estimada |

**3. Decisão inteligente**

O agente pode então:

- Prosseguir com a ferramenta conforme planejado
- Alternar automaticamente para uma alternativa melhor
- Apresentar a decisão ao usuário

**4. Loop de feedback opcional**

Após a chamada, o agente pode enviar um relatório de resultado anônimo. Esses dados melhoram continuamente as pontuações para todos os usuários por meio de um forte **efeito de rede**.

---

## Potencial Global de Economia de Energia

Se todos os agentes de IA e chatbots do mundo adotassem o ToolRate, o impacto energético seria significativo.

Assumindo que em um ano haverá mais agentes de IA ativos do que seres humanos na Terra (>8 bilhões de agentes), e que o ToolRate pode reduzir chamadas de ferramentas com falha ou desperdiçadas em **60–75%**, a adoção generalizada poderia evitar bilhões de inferências desnecessárias de LLM e loops de nova tentativa diariamente.

> **Estimativa conservadora:** O ToolRate poderia economizar para o ecossistema global de IA entre **8 e 15 TWh de eletricidade por ano** — aproximadamente equivalente ao consumo anual de **1,5 a 2,5 milhões de residências americanas médias**.

As economias vêm principalmente de:

- Menos chamadas de API com falha
- Redução do desperdício de tokens
- Roteamento mais inteligente para ferramentas confiáveis

---

## Comparação com Outras Ferramentas

| Ferramenta | Tipo | Previne Falhas? | Dados Coletivos | Fornece Alternativas | LGPD/GDPR / Jurisdição | Foco Principal |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oráculo de confiabilidade pré-chamada | ✅ | ✅ | ✅ | ✅ Forte | Agentes de produção |
| LangSmith | Observabilidade + Rastreamento | ❌ | ❌ | ❌ | ⚠️ Limitado | Ecossistema LangChain |
| Langfuse | Observabilidade de código aberto | ❌ | ❌ | ❌ | ⚠️ Limitado | Rastreamento de código aberto |
| Braintrust | Avaliações + Rastreamento | ⚠️ Parcialmente | ❌ | ❌ | ⚠️ Limitado | Times orientados a avaliações |
| Helicone | Observabilidade de LLM + Ferramentas | ❌ | ❌ | ❌ | ⚠️ Limitado | Monitoramento de custos e latência |
| AgentOps | Monitoramento de agentes | ❌ | ❌ | ❌ | ⚠️ Limitado | Análise de comportamento de agentes |

> O ToolRate é atualmente a **única solução** que funciona de forma preventiva usando experiência real de agentes obtida de forma coletiva.

---

## Disponibilidade

| Canal | Detalhes |
|---|---|
| Site | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| SDK Python | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| SDK TypeScript | `npm install toolrate` |
| Licença | Business Source License 1.1 (BUSL-1.1) |

---

*Última atualização: abril de 2026*
