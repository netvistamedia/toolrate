# ToolRate-järjestelmän yleiskatsaus

## Mikä on ToolRate?

ToolRate on **joukkoistamiseen perustuva luotettavuuskerros** autonomisille tekoälyagenteille — reaaliaikainen luotettavuusoraakkeli, jonka avulla agentit voivat arvioida ulkoisen työkalun tai API:n luotettavuuden *ennen* sen kutsumista.

Se ratkaisee yhden agenttikehityksen kriittisimmistä käytännön ongelmista: useimmat virheet eivät johdu itse LLM:stä, vaan ulkoisten työkalujen ja API:en arvaamattomasta käyttäytymisestä — nopeusrajoituksista, skeemadriftistä, todennusongelmista, bottienestosta ja reunatapauksista.

---

## Kenelle ToolRate on tarkoitettu?

- Kehittäjille, jotka rakentavat **tuotantotason** tekoälyagentteja
- Tiimeille ja itsenäisille kehittäjille, jotka työskentelevät **LangChainin, CrewAI:n, LangGraphin, AutoGenin** tai **LlamaIndexin** kanssa
- Eurooppalaisille kehittäjille, joille **GDPR ja tietojen säilytyspaikka** ovat tärkeitä
- Kaikille, jotka ovat turhautuneita agentteihin, jotka toimivat hyvin demoissa mutta epäonnistuvat usein todellisissa tilanteissa

---

## Miten ToolRate toimii

Järjestelmä on tarkoituksella yksinkertainen ja kevyt:

**1. Tarkistus ennen kutsua**

Ennen ulkoisen työkalun tai API:n kutsumista agentti tekee kyselyn ToolRatelle:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Jäsennelty vastaus**

ToolRate palauttaa välittömästi JSON-hyötykuorman, joka sisältää:

| Kenttä | Kuvaus |
|---|---|
| `reliability_score` | Pisteet 0–100 |
| `success_rate` | Historiallinen onnistumisprosentti todellisten agenttikutsujen perusteella |
| `pitfalls` | Yleiset vikatilat + suositellut lievennystoimenpiteet |
| `alternatives` | Parhaat vaihtoehdot suorituskyvyn mukaan järjestettynä |
| `jurisdiction` | GDPR-riski ja tietojen sijaintitiedot |
| `latency` | Arvioitu vasteaika |

**3. Älykäs päätös**

Agentti voi tämän jälkeen:

- Jatkaa työkalun käyttöä suunnitelman mukaisesti
- Vaihtaa automaattisesti parempaan vaihtoehtoon
- Esittää päätöksen käyttäjälle

**4. Valinnainen palautesilmukka**

Kutsun jälkeen agentti voi lähettää anonyymin tulosraportin. Nämä tiedot parantavat jatkuvasti kaikkien käyttäjien pisteitä vahvan **verkkovaikutuksen** ansiosta.

---

## Globaali energiansäästöpotentiaali

Jos kaikki tekoälyagentit ja chatbotit maailmanlaajuisesti ottaisivat ToolRaten käyttöön, energiavaikutus olisi merkittävä.

Olettaen, että vuoden sisällä aktiivisia tekoälyagentteja on enemmän kuin ihmisiä Maapallolla (yli 8 miljardia agenttia) ja että ToolRate voi vähentää epäonnistuneita tai turhia työkalukutsuja **60–75 %**, laajamittainen käyttöönotto voisi päivittäin estää miljardeja tarpeettomia LLM-inferenssejä ja uudelleenyrityssilmukoita.

> **Konservatiivinen arvio:** ToolRate voisi säästää globaalin tekoälyekosysteemin energiaa **8–15 TWh vuodessa** — mikä vastaa suunnilleen **1,5–2,5 miljoonan keskimääräisen amerikkalaisen kotitalouden** vuosikulutusta.

Säästöt syntyvät pääasiassa:

- Vähemmistä epäonnistuneista API-kutsuista
- Vähentyneestä tokenien tuhlauksesta
- Älykkäämmästä reitityksestä luotettaville työkaluille

---

## Vertailu muihin työkaluihin

| Työkalu | Tyyppi | Estää virheet? | Joukkoistamisdata | Tarjoaa vaihtoehtoja | GDPR / Lainkäyttöalue | Ensisijainen fokus |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Luotettavuusoraakkeli ennen kutsua | ✅ | ✅ | ✅ | ✅ Vahva | Tuotantoagentit |
| LangSmith | Havaittavuus + Jäljitys | ❌ | ❌ | ❌ | ⚠️ Rajallinen | LangChain-ekosysteemi |
| Langfuse | Avoimen lähdekoodin havaittavuus | ❌ | ❌ | ❌ | ⚠️ Rajallinen | Avoimen lähdekoodin jäljitys |
| Braintrust | Arvioinnit + Jäljitys | ⚠️ Osittain | ❌ | ❌ | ⚠️ Rajallinen | Arviointilähtöiset tiimit |
| Helicone | LLM + Työkaluhavaittavuus | ❌ | ❌ | ❌ | ⚠️ Rajallinen | Kustannus- ja viiveseuranta |
| AgentOps | Agenttiseuranta | ❌ | ❌ | ❌ | ⚠️ Rajallinen | Agenttikäyttäytymisen analyysi |

> ToolRate on tällä hetkellä **ainoa ratkaisu**, joka toimii ennaltaehkäisevästi hyödyntäen todellista joukkoistettua agenttikokemusta.

---

## Saatavuus

| Kanava | Tiedot |
|---|---|
| Verkkosivusto | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Lisenssi | Business Source License 1.1 (BUSL-1.1) |

---

*Viimeksi päivitetty: huhtikuu 2026*
