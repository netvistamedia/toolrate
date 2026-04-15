# Akopọ Eto ToolRate

## Kí ni ToolRate?

ToolRate jẹ **ipele igbẹkẹle ti o da lori ẹbọ ọpọlọpọ eniyan** fún àwọn olùrànlọ́wọ́ AI tí ń ṣiṣẹ́ lọ́wọ́ ara wọn — oracle igbẹkẹle ni akoko gidi ti o jẹ ki àwọn olùrànlọ́wọ́ ṣe àyẹ̀wò bí irinṣẹ́ ìta tàbí API ṣe jẹ́ olùgbẹ́kẹ̀lé tó *ṣáájú* kíkọ ọ.

Ó yanjú ọ̀kan nínú àwọn ìṣòro tó ṣe pàtàkì jùlọ nínú ìdàgbàsókè olùrànlọ́wọ́: ọpọlọpọ àwọn ìkùnà kò jáde lọ́wọ́ LLM fúnrarẹ̀, ṣùgbọ́n lọ́wọ́ ìhùwàsí tí a kò lè sọ tẹ́lẹ̀ ti àwọn irinṣẹ́ ìta àti API — àwọn ààlà ìyára, ìrìnnà ìlànà, àwọn ìṣòro ìdánimọ̀, ààbò lòdì sí bot, àti àwọn ọ̀ràn ìyàntẹ̀lẹ̀.

---

## Tani ToolRate Jẹ́ Fún?

- Àwọn olùdàgbàsókè tí ń kọ́ àwọn olùrànlọ́wọ́ AI ní **ìpele iṣẹ́ ìṣelọpọ**
- Àwọn ẹgbẹ́ àti àwọn olùdàgbàsókè aladáni tí ń ṣiṣẹ́ pẹ̀lú **LangChain, CrewAI, LangGraph, AutoGen**, tàbí **LlamaIndex**
- Àwọn olùdàgbàsókè ilẹ̀ Yúróòpù tí ń tọ́jú **GDPR àti ibùgbé àwọn ìsọfúnni**
- Ẹnikẹ́ni tí ó ti rẹ̀ nígbà tí àwọn olùrànlọ́wọ́ ń ṣiṣẹ́ dára nínú àwọn ìfihàn ṣùgbọ́n máa ń kùnà nígbà gbogbo nínú àwọn ipò tòótọ́

---

## Bí ToolRate Ṣe Ń Ṣiṣẹ́

Eto naa jẹ́ olùmọ̀ẹ̀mọ̀ dídá rọrùn àti ìfẹ́fẹ́:

**1. Ìdánwò ṣáájú ìpè**

Ṣáájú kíkọ irinṣẹ́ ìta tàbí API kankan, olùrànlọ́wọ́ máa ń béèrè lọ́wọ́ ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Ìdáhùn tí a ṣètò**

ToolRate máa ń padà pẹ̀lú JSON payload tí ó ní:

| Pápá | Àpèjúwe |
|---|---|
| `reliability_score` | Ìkìlọ̀ láti 0–100 |
| `success_rate` | Ìwọ̀n ìtàn tí ó dá lé àwọn ìpè olùrànlọ́wọ́ gidi |
| `pitfalls` | Àwọn ọ̀nà ìkùnà tí ó wọ́pọ̀ + àwọn ọ̀nà àbájáde tí a dámọ̀ràn |
| `alternatives` | Àwọn àṣàyàn tó dára jùlọ tí a tò lẹ́sẹ̀ẹ̀ gẹ́gẹ́ bí iṣẹ́ |
| `jurisdiction` | Ewu GDPR àti àlàyé ibùgbé ìsọfúnni |
| `latency` | Ìdádúró ìdáhùn tí a fojúinu |

**3. Ìpinnu ọlọ́gbọ́n**

Olùrànlọ́wọ́ lẹ́hìn náà lè:

- Tẹ̀síwájú pẹ̀lú irinṣẹ́ gẹ́gẹ́ bí a ti gbèrò
- Yí padà ní àifọwọ́yí sí àṣàyàn tó dára sí i
- Ṣàgbékalẹ̀ ìpinnu fún olùmúlò

**4. Ìdìpọ̀ ìdáhùn àṣàyàn**

Lẹ́yìn ìpè, olùrànlọ́wọ́ lè ránṣẹ́ ìròyìn àbájáde tí a kò mọ. Àwọn ìsọfúnni wọ̀nyí máa ń mú àwọn ìkìlọ̀ dára sí i fún gbogbo àwọn olùmúlò nígbà gbogbo nípasẹ̀ **ipa àjọpọ̀** tó lágbára.

---

## Agbára Ìfipamọ́ Agbára Agbára Àgbáyé

Tí gbogbo àwọn olùrànlọ́wọ́ AI àti chatbot káàkiri àgbáyé bá gba ToolRate, ipa lórí agbára ìmọ́lẹ̀ yóò jẹ́ pàtàkì.

Nípa gbígba pé láàárín ọdún kan, àwọn olùrànlọ́wọ́ AI tí ń ṣiṣẹ́ lọwọ yóò pọ̀ jù àwọn ènìyàn lórí Ilẹ̀ Ayé (>àwọn olùrànlọ́wọ́ bílíọ̀nù 8), àti pé ToolRate lè dínkù àwọn ìpè irinṣẹ́ tí ó kùnà tàbí tí ó jẹ́ àtọnù nípa **60–75%**, ìgbaradì gbòòrò lè ṣe ìdènà àwọn ọ̀kẹ́ àìmọye àwọn ìmọ̀sọ̀rọ̀ LLM tí a kò nílò àti àwọn ìdìpọ̀ ìdánwò tún ní gbogbo ọjọ́.

> **Ìfojúsùn olùpamọ́:** ToolRate lè ṣe ìfipamọ́ fún ètò AI àgbáyé laarin **TWh 8 sí 15 ti ìmọ́lẹ̀ ní ọdún kan** — ó fẹ́rẹ̀ẹ́ jẹ́ ìdọ́gba pẹ̀lú ìjẹun ọdọọdún ti **àwọn ilé 1.5 sí 2.5 mílíọ̀nù ti àárín Amẹ́ríkà**.

Ìfipamọ́ máa ń wá pàápàá láti:

- Àwọn ìpè API tí ó kùnà díẹ̀
- Dídínkù ìjẹ́ èémí token
- Ìtọ́nisọ́nà tó ọlọ́gbọ́n sí àwọn irinṣẹ́ tí a gbẹ́kẹ̀lé

---

## Ìfiwéra Pẹ̀lú Àwọn Irinṣẹ́ Mìíràn

| Irinṣẹ́ | Irú | Ń Dènà Ìkùnà? | Àwọn Ìsọfúnni Ọpọ̀ Ènìyàn | Ń Pèsè Àṣàyàn | GDPR / Àgbègbè Àṣẹ | Ìdojúkọ Àkọ́kọ́ |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracle igbẹkẹle ṣáájú ìpè | ✅ | ✅ | ✅ | ✅ Lágbára | Àwọn olùrànlọ́wọ́ iṣẹ́ ìṣelọpọ |
| LangSmith | Ìmójútó + Ìtọpa | ❌ | ❌ | ❌ | ⚠️ Ní ààlà | Ẹ̀rọ LangChain |
| Langfuse | Ìmójútó orísun ìṣí | ❌ | ❌ | ❌ | ⚠️ Ní ààlà | Ìtọpa orísun ìṣí |
| Braintrust | Ìdánwò + Ìtọpa | ⚠️ Ní apá kan | ❌ | ❌ | ⚠️ Ní ààlà | Àwọn ẹgbẹ́ tí ìdánwò ń ṣamọ̀nà |
| Helicone | Ìmójútó LLM + Irinṣẹ́ | ❌ | ❌ | ❌ | ⚠️ Ní ààlà | Ìmójútó iye owó àti ìdádúró |
| AgentOps | Ìmójútó olùrànlọ́wọ́ | ❌ | ❌ | ❌ | ⚠️ Ní ààlà | Ìtúpalẹ̀ ìhùwàsí olùrànlọ́wọ́ |

> ToolRate jẹ́ lọ́wọ́lọ́wọ́ **ojútùú kanṣoṣo** tí ó ń ṣiṣẹ́ lọ́nà ìdènà nípasẹ̀ lílo ìrírí olùrànlọ́wọ́ gidi tí ọpọlọpọ ènìyàn pèsè.

---

## Wíwà

| Ìkànnì | Àwọn Àlàyé |
|---|---|
| Ojú ìpàgọ | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Ìwé àṣẹ | Business Source License 1.1 (BUSL-1.1) |

---

*Ìmúdójúìwọ̀n ìkẹyìn: Ọ̀pẹ̀lẹ̀ 2026*
