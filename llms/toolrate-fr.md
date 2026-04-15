# Présentation du système ToolRate

## Qu'est-ce que ToolRate ?

ToolRate est une **couche de fiabilité participative** pour les agents IA autonomes — un oracle de fiabilité en temps réel qui permet aux agents d'évaluer la fiabilité d'un outil externe ou d'une API *avant* de l'appeler.

Il résout l'un des problèmes pratiques les plus critiques dans le développement d'agents : la plupart des échecs ne sont pas causés par le LLM lui-même, mais par le comportement imprévisible des outils et APIs externes — limites de débit, dérive de schéma, problèmes d'authentification, protections anti-bot et cas limites.

---

## À qui s'adresse ToolRate ?

- Les développeurs qui construisent des agents IA **prêts pour la production**
- Les équipes et développeurs indépendants travaillant avec **LangChain, CrewAI, LangGraph, AutoGen** ou **LlamaIndex**
- Les développeurs européens soucieux du **RGPD et de la résidence des données**
- Tous ceux qui sont frustrés par des agents qui fonctionnent bien en démo mais échouent fréquemment dans des scénarios réels

---

## Comment fonctionne ToolRate

Le système est intentionnellement simple et léger :

**1. Vérification pré-appel**

Avant d'appeler un outil ou une API externe, l'agent interroge ToolRate :

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Réponse structurée**

ToolRate retourne immédiatement un payload JSON contenant :

| Champ | Description |
|---|---|
| `reliability_score` | Score de 0 à 100 |
| `success_rate` | Taux historique basé sur de vrais appels d'agents |
| `pitfalls` | Modes de défaillance courants + mesures correctives recommandées |
| `alternatives` | Meilleures alternatives classées par performance |
| `jurisdiction` | Risque RGPD et informations sur la résidence des données |
| `latency` | Latence de réponse estimée |

**3. Décision intelligente**

L'agent peut alors :

- Continuer avec l'outil comme prévu
- Basculer automatiquement vers une meilleure alternative
- Soumettre la décision à l'utilisateur

**4. Boucle de rétroaction optionnelle**

Après l'appel, l'agent peut soumettre un rapport de résultat anonyme. Ces données améliorent continuellement les scores pour tous les utilisateurs grâce à un fort **effet de réseau**.

---

## Potentiel mondial d'économies d'énergie

Si tous les agents IA et chatbots dans le monde adoptaient ToolRate, l'impact énergétique serait significatif.

En supposant que dans un an il y aura plus d'agents IA actifs que d'humains sur Terre (>8 milliards d'agents), et que ToolRate peut réduire les appels d'outils échoués ou inutiles de **60 à 75 %**, une adoption généralisée pourrait prévenir quotidiennement des milliards d'inférences LLM inutiles et de boucles de nouvelles tentatives.

> **Estimation prudente :** ToolRate pourrait faire économiser à l'écosystème IA mondial entre **8 et 15 TWh d'électricité par an** — soit approximativement la consommation annuelle de **1,5 à 2,5 millions de foyers américains moyens**.

Les économies proviennent principalement de :

- Moins d'appels API échoués
- Réduction du gaspillage de tokens
- Un routage plus intelligent vers des outils fiables

---

## Comparaison avec d'autres outils

| Outil | Type | Prévient les échecs ? | Données participatives | Fournit des alternatives | RGPD / Juridiction | Objectif principal |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracle de fiabilité pré-appel | ✅ | ✅ | ✅ | ✅ Fort | Agents en production |
| LangSmith | Observabilité + Traçage | ❌ | ❌ | ❌ | ⚠️ Limité | Écosystème LangChain |
| Langfuse | Observabilité open source | ❌ | ❌ | ❌ | ⚠️ Limité | Traçage open source |
| Braintrust | Évaluations + Traçage | ⚠️ Partiellement | ❌ | ❌ | ⚠️ Limité | Équipes axées sur l'évaluation |
| Helicone | Observabilité LLM + Outils | ❌ | ❌ | ❌ | ⚠️ Limité | Surveillance des coûts et de la latence |
| AgentOps | Surveillance des agents | ❌ | ❌ | ❌ | ⚠️ Limité | Analyse du comportement des agents |

> ToolRate est actuellement la **seule solution** qui fonctionne de manière préventive en s'appuyant sur une véritable expérience participative des agents.

---

## Disponibilité

| Canal | Détails |
|---|---|
| Site web | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| SDK Python | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| SDK TypeScript | `npm install toolrate` |
| Licence | Business Source License 1.1 (BUSL-1.1) |

---

*Dernière mise à jour : avril 2026*
