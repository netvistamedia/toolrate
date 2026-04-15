# Taƙaitaccen Tsarin ToolRate

## Menene ToolRate?

ToolRate wata **Layer na dogaro da aka gina ta hanyar haɗin jama'a** ce don wakilai masu zaman kansu na AI — Oracle na dogaro a lokaci na gaske wanda ke ba da damar wakilai su tantance yadda yake da aminci a wata kayan aiki na waje ko API *kafin* kiran shi.

Yana warware ɗaya daga cikin matsalolin aiwatar da aiki mafi mahimmanci a ci gaban wakili: yawancin gazawar ba ta fito daga LLM kanta ba, amma daga halin da ba a iya hasashen ba na kayan aikin waje da API — iyakokin gudu, matsalolin tsari, matsalolin tabbatarwa, kariyar anti-bot, da lokuta na iyaka.

---

## ToolRate Yake Ga Waye?

- Masu haɓakawa waɗanda ke gina wakilai na AI na **matakin samarwa**
- Ƙungiyoyi da masu haɓakawa masu zaman kansu waɗanda ke aiki tare da **LangChain, CrewAI, LangGraph, AutoGen**, ko **LlamaIndex**
- Masu haɓakawa na Turai waɗanda ke kula da **GDPR da mazaunin bayanai**
- Duk wanda yake takaici da wakilai waɗanda ke aiki sosai a cikin nunin amma suna gazawa akai-akai a cikin yanayi na gaske

---

## Yadda ToolRate Yake Aiki

An tsara tsarin da niyyar zama mai sauƙi da haske:

**1. Duba kafin kira**

Kafin kiran kowane kayan aiki na waje ko API, wakili yana tambayar ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Amsa mai tsari**

ToolRate nan da nan yana dawo da JSON payload wanda ya ƙunshi:

| Filin | Bayanai |
|---|---|
| `reliability_score` | Maki daga 0–100 |
| `success_rate` | Tarihin kason nasara bisa kiran wakili na gaske |
| `pitfalls` | Yanayin gazawa na kowa + shawarwarin ragewa |
| `alternatives` | Madaidaitan zaɓuɓɓuka da aka jera bisa aiki |
| `jurisdiction` | Haɗarin GDPR da bayanan mazaunin bayanai |
| `latency` | Hasashen lokacin amsa |

**3. Yanke shawara mai hankali**

Wakili zai iya:

- Ci gaba da kayan aikin kamar yadda aka tsara
- Canza kai tsaye zuwa zaɓi mafi kyau
- Gabatar da yanke shawara ga mai amfani

**4. Madauri na amsa mai zabi**

Bayan kira, wakili zai iya ƙaddamar da rahoton sakamako na sirri. Wannan bayanan yana inganta maki ga duk masu amfani akai-akai ta hanyar **tasirin hanyar sadarwa** mai ƙarfi.

---

## Yuwuwar Adana Makamashi a Duniya

Idan duk wakilai na AI da chatbot a duk duniya sun karɓi ToolRate, tasirin makamashi zai zama mai mahimmanci.

Tare da hasashen cewa a cikin shekara ɗaya za a sami wakilai na AI masu aiki fiye da mutane a Duniya (> wakilai biliyan 8), kuma ToolRate zai iya rage kiran kayan aiki da suka gaza ko ɓata da **60–75%**, karɓar yaɗuwa na iya hana biliyan ayi na LLM mara ma'ana da madauran sake gwadawa kowace rana.

> **Hasashe mai kiyayya:** ToolRate na iya tanadin tsarin AI na duniya tsakanin **TWh 8 zuwa 15 na wutar lantarki a kowace shekara** — kimanin daidai da amfanin shekara-shekara na **gidaje miliyan 1.5 zuwa 2.5 na matsakaicin Amurkawa**.

Ajiyar tana zuwa musamman daga:

- Ƙarancin kiran API da suka gaza
- Rage ɓatar token
- Hanyar mafi hankali zuwa kayan aikin da ake dogara da su

---

## Kwatankwacin da Sauran Kayan Aiki

| Kayan Aiki | Nau'i | Yana Hana Gazawa? | Bayanai na Jama'a | Yana Bayar da Zaɓuɓɓuka | GDPR / Ikon Shari'a | Babban Mayar da Hankali |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracle na dogaro kafin kira | ✅ | ✅ | ✅ | ✅ Mai ƙarfi | Wakilai na samarwa |
| LangSmith | Lura + Bin diddigin | ❌ | ❌ | ❌ | ⚠️ Iyakantacce | Tsarin LangChain |
| Langfuse | Lura ta buɗaɗɗen tushe | ❌ | ❌ | ❌ | ⚠️ Iyakantacce | Bin diddigin buɗaɗɗen tushe |
| Braintrust | Kimantawa + Bin diddigin | ⚠️ Wani ɓangare | ❌ | ❌ | ⚠️ Iyakantacce | Ƙungiyoyi masu mayar da hankali kan kimantawa |
| Helicone | Lura LLM + Kayan Aiki | ❌ | ❌ | ❌ | ⚠️ Iyakantacce | Sa ido kan farashi da lokacin amsa |
| AgentOps | Sa ido kan wakilai | ❌ | ❌ | ❌ | ⚠️ Iyakantacce | Nazarin halin wakili |

> ToolRate a halin yanzu shine **kadai mafita** wanda ke aiki ta hanyar hanawa ta amfani da kwarewar wakili na gaske da aka tattara daga jama'a.

---

## Samuwa

| Tashar | Bayanai |
|---|---|
| Gidan yanar gizo | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Lasisin | Business Source License 1.1 (BUSL-1.1) |

---

*An sabunta ƙarshe: Afrilu 2026*
