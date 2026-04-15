# Ikhtisar Sistem ToolRate

## Apa itu ToolRate?

ToolRate adalah **lapisan keandalan berbasis kerumunan** untuk agen AI otonom — sebuah oracle keandalan waktu nyata yang memungkinkan agen menilai seberapa andal suatu alat eksternal atau API *sebelum* memanggilnya.

Ini memecahkan salah satu masalah praktis paling kritis dalam pengembangan agen: sebagian besar kegagalan bukan disebabkan oleh LLM itu sendiri, melainkan oleh perilaku tak terduga dari alat dan API eksternal — batas laju, pergeseran skema, masalah autentikasi, perlindungan anti-bot, dan kasus tepi.

---

## Untuk Siapa ToolRate?

- Pengembang yang membangun agen AI **tingkat produksi**
- Tim dan pengembang solo yang bekerja dengan **LangChain, CrewAI, LangGraph, AutoGen**, atau **LlamaIndex**
- Pengembang Eropa yang peduli dengan **GDPR dan residensi data**
- Siapa pun yang frustrasi dengan agen yang bekerja baik dalam demo tetapi sering gagal dalam skenario dunia nyata

---

## Cara Kerja ToolRate

Sistem ini sengaja dirancang sederhana dan ringan:

**1. Pemeriksaan sebelum panggilan**

Sebelum memanggil alat atau API eksternal apa pun, agen mengirim kueri ke ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Respons terstruktur**

ToolRate segera mengembalikan payload JSON yang berisi:

| Bidang | Deskripsi |
|---|---|
| `reliability_score` | Skor dari 0–100 |
| `success_rate` | Tingkat historis berdasarkan panggilan agen nyata |
| `pitfalls` | Mode kegagalan umum + mitigasi yang direkomendasikan |
| `alternatives` | Alternatif terbaik yang diurutkan berdasarkan performa |
| `jurisdiction` | Risiko GDPR dan informasi residensi data |
| `latency` | Perkiraan latensi respons |

**3. Keputusan cerdas**

Agen kemudian dapat:

- Melanjutkan dengan alat seperti yang direncanakan
- Beralih secara otomatis ke alternatif yang lebih baik
- Menyampaikan keputusan kepada pengguna

**4. Loop umpan balik opsional**

Setelah panggilan, agen dapat mengirimkan laporan hasil anonim. Data ini terus meningkatkan skor untuk semua pengguna melalui **efek jaringan** yang kuat.

---

## Potensi Penghematan Energi Global

Jika semua agen AI dan chatbot di seluruh dunia mengadopsi ToolRate, dampak energinya akan signifikan.

Dengan asumsi bahwa dalam satu tahun akan ada lebih banyak agen AI aktif daripada manusia di Bumi (>8 miliar agen), dan ToolRate dapat mengurangi panggilan alat yang gagal atau terbuang sebesar **60–75%**, adopsi luas dapat mencegah miliaran inferensi LLM yang tidak perlu dan loop percobaan ulang setiap hari.

> **Perkiraan konservatif:** ToolRate dapat menghemat ekosistem AI global antara **8 hingga 15 TWh listrik per tahun** — kira-kira setara dengan konsumsi tahunan **1,5 hingga 2,5 juta rumah tangga Amerika rata-rata**.

Penghematan terutama berasal dari:

- Lebih sedikit panggilan API yang gagal
- Pengurangan pemborosan token
- Perutean lebih cerdas ke alat yang andal

---

## Perbandingan dengan Alat Lain

| Alat | Tipe | Mencegah Kegagalan? | Data Kerumunan | Menyediakan Alternatif | GDPR / Yurisdiksi | Fokus Utama |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracle keandalan sebelum panggilan | ✅ | ✅ | ✅ | ✅ Kuat | Agen produksi |
| LangSmith | Observabilitas + Pelacakan | ❌ | ❌ | ❌ | ⚠️ Terbatas | Ekosistem LangChain |
| Langfuse | Observabilitas sumber terbuka | ❌ | ❌ | ❌ | ⚠️ Terbatas | Pelacakan sumber terbuka |
| Braintrust | Evaluasi + Pelacakan | ⚠️ Sebagian | ❌ | ❌ | ⚠️ Terbatas | Tim berbasis evaluasi |
| Helicone | Observabilitas LLM + Alat | ❌ | ❌ | ❌ | ⚠️ Terbatas | Pemantauan biaya & latensi |
| AgentOps | Pemantauan agen | ❌ | ❌ | ❌ | ⚠️ Terbatas | Analisis perilaku agen |

> ToolRate saat ini adalah **satu-satunya solusi** yang bekerja secara preventif menggunakan pengalaman agen nyata berbasis kerumunan.

---

## Ketersediaan

| Saluran | Detail |
|---|---|
| Situs web | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| Python SDK | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| TypeScript SDK | `npm install toolrate` |
| Lisensi | Business Source License 1.1 (BUSL-1.1) |

---

*Terakhir diperbarui: April 2026*
