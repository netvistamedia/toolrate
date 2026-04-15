# ToolRate Sistem Genel Bakışı

## ToolRate Nedir?

ToolRate, otonom AI ajanları için **kitle kaynaklı bir güvenilirlik katmanıdır** — ajanların bir dış araç veya API'yi çağırmadan *önce* ne kadar güvenilir olduğunu değerlendirmesine olanak tanıyan gerçek zamanlı bir güvenilirlik kahinıdır.

Ajan geliştirmedeki en kritik pratik sorunlardan birini çözer: çoğu başarısızlık LLM'in kendisinden değil, dış araçların ve API'lerin öngörülemeyen davranışlarından kaynaklanır — hız sınırları, şema kayması, kimlik doğrulama sorunları, bot karşıtı korumalar ve uç durumlar.

---

## ToolRate Kimin İçin?

- **Üretime hazır** AI ajanları geliştiren geliştiriciler
- **LangChain, CrewAI, LangGraph, AutoGen** veya **LlamaIndex** ile çalışan ekipler ve bağımsız geliştiriciler
- **GDPR ve veri yerleşimi** konusunda hassas davranan Avrupalı geliştiriciler
- Demolarda iyi çalışan ancak gerçek dünya senaryolarında sık sık başarısız olan ajanlardan bıkmış herkes

---

## ToolRate Nasıl Çalışır

Sistem kasıtlı olarak basit ve hafif tutulmuştur:

**1. Çağrı öncesi kontrol**

Herhangi bir dış araç veya API çağrılmadan önce ajan ToolRate'e sorgu gönderir:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Yapılandırılmış yanıt**

ToolRate anında aşağıdakileri içeren bir JSON yükü döndürür:

| Alan | Açıklama |
|---|---|
| `reliability_score` | 0–100 arası puan |
| `success_rate` | Gerçek ajan çağrılarına dayalı tarihsel başarı oranı |
| `pitfalls` | Yaygın hata modları + önerilen çözümler |
| `alternatives` | Performansa göre sıralanmış en iyi alternatifler |
| `jurisdiction` | GDPR riski ve veri yerleşimi bilgisi |
| `latency` | Tahmini yanıt gecikmesi |

**3. Akıllı karar**

Ajan daha sonra:

- Planlandığı gibi araçla devam edebilir
- Otomatik olarak daha iyi bir alternatife geçebilir
- Kararı kullanıcıya sunabilir

**4. İsteğe bağlı geri bildirim döngüsü**

Çağrının ardından ajan anonim bir sonuç raporu gönderebilir. Bu veriler güçlü bir **ağ etkisi** aracılığıyla tüm kullanıcılar için puanları sürekli olarak iyileştirir.

---

## Küresel Enerji Tasarrufu Potansiyeli

Dünya genelindeki tüm AI ajanları ve sohbet botları ToolRate'i benimseseydi, enerji üzerindeki etki önemli olurdu.

Bir yıl içinde Dünya'daki aktif AI ajan sayısının insan sayısını aşacağı varsayılırsa (>8 milyar ajan) ve ToolRate başarısız ya da boşa giden araç çağrılarını **%60–75** oranında azaltabilirse, yaygın benimseme günlük milyarlarca gereksiz LLM çıkarım işlemini ve yeniden deneme döngüsünü önleyebilir.

> **Muhafazakâr tahmin:** ToolRate, küresel AI ekosistemine yılda **8 ile 15 TWh elektrik** tasarrufu sağlayabilir — bu, **1,5 ile 2,5 milyon ortalama Amerikan hanesinin** yıllık tüketimine yaklaşık olarak eşdeğerdir.

Tasarruflar ağırlıklı olarak şunlardan kaynaklanır:

- Daha az başarısız API çağrısı
- Azaltılmış token israfı
- Güvenilir araçlara daha akıllı yönlendirme

---

## Diğer Araçlarla Karşılaştırma

| Araç | Tür | Hataları Önler mi? | Kitle Kaynaklı Veri | Alternatif Sunar mı | GDPR / Yargı Yetkisi | Birincil Odak |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Çağrı öncesi güvenilirlik kahini | ✅ | ✅ | ✅ | ✅ Güçlü | Üretim ajanları |
| LangSmith | Gözlemlenebilirlik + İzleme | ❌ | ❌ | ❌ | ⚠️ Sınırlı | LangChain ekosistemi |
| Langfuse | Açık kaynak gözlemlenebilirlik | ❌ | ❌ | ❌ | ⚠️ Sınırlı | Açık kaynak izleme |
| Braintrust | Değerlendirmeler + İzleme | ⚠️ Kısmen | ❌ | ❌ | ⚠️ Sınırlı | Değerlendirme odaklı ekipler |
| Helicone | LLM + Araç Gözlemlenebilirliği | ❌ | ❌ | ❌ | ⚠️ Sınırlı | Maliyet ve gecikme izleme |
| AgentOps | Ajan izleme | ❌ | ❌ | ❌ | ⚠️ Sınırlı | Ajan davranış analizi |

> ToolRate şu anda gerçek kitle kaynaklı ajan deneyimini kullanarak önleyici biçimde çalışan **tek çözümdür**.

---

## Erişilebilirlik

| Kanal | Ayrıntılar |
|---|---|
| Web sitesi | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Lisans | Business Source License 1.1 (BUSL-1.1) |

---

*Son güncelleme: Nisan 2026*
