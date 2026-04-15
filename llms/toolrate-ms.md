# Gambaran Keseluruhan Sistem ToolRate

## Apakah ToolRate?

ToolRate ialah **lapisan kebolehpercayaan berasaskan orang ramai** untuk ejen AI autonomi — sebuah oracle kebolehpercayaan masa nyata yang membolehkan ejen menilai tahap kepercayaan sesuatu alat luaran atau API *sebelum* memanggilnya.

Ia menyelesaikan salah satu masalah praktikal yang paling kritikal dalam pembangunan ejen: kebanyakan kegagalan bukan disebabkan oleh LLM itu sendiri, tetapi oleh tingkah laku alat dan API luaran yang tidak dapat diramalkan — had kadar, penyimpangan skema, isu pengesahan, perlindungan anti-bot, dan kes tepi.

---

## Untuk Siapa ToolRate?

- Pembangun yang membina ejen AI **peringkat pengeluaran**
- Pasukan dan pembangun solo yang menggunakan **LangChain, CrewAI, LangGraph, AutoGen**, atau **LlamaIndex**
- Pembangun Eropah yang mengambil berat tentang **GDPR dan kediaman data**
- Sesiapa sahaja yang kecewa dengan ejen yang berfungsi baik dalam demo tetapi kerap gagal dalam senario dunia nyata

---

## Cara ToolRate Berfungsi

Sistem ini direka secara sengaja untuk menjadi ringkas dan ringan:

**1. Semakan pra-panggilan**

Sebelum memanggil mana-mana alat atau API luaran, ejen membuat pertanyaan kepada ToolRate:

```python
assessment = toolrate.guard(tool_identifier=..., context=...)
```

**2. Respons berstruktur**

ToolRate segera memulangkan muatan JSON yang mengandungi:

| Medan | Penerangan |
|---|---|
| `reliability_score` | Skor dari 0 hingga 100 |
| `success_rate` | Kadar sejarah berdasarkan panggilan ejen sebenar |
| `pitfalls` | Mod kegagalan biasa + pengurangan yang disyorkan |
| `alternatives` | Alternatif terbaik yang disenaraikan mengikut prestasi |
| `jurisdiction` | Risiko GDPR dan maklumat kediaman data |
| `latency` | Anggaran kependaman respons |

**3. Keputusan pintar**

Ejen kemudiannya boleh:

- Meneruskan dengan alat seperti yang dirancang
- Beralih secara automatik kepada alternatif yang lebih baik
- Memaparkan keputusan kepada pengguna

**4. Gelung maklum balas pilihan**

Selepas panggilan, ejen boleh menyerahkan laporan hasil tanpa nama. Data ini secara berterusan meningkatkan skor untuk semua pengguna melalui **kesan rangkaian** yang kukuh.

---

## Potensi Penjimatan Tenaga Global

Sekiranya semua ejen AI dan chatbot di seluruh dunia menggunakan ToolRate, impak tenaganya akan menjadi signifikan.

Dengan mengandaikan bahawa dalam masa setahun jumlah ejen AI aktif akan melebihi jumlah manusia di Bumi (>8 bilion ejen), dan ToolRate dapat mengurangkan panggilan alat yang gagal atau membazir sebanyak **60–75%**, penggunaan meluas boleh mengelakkan berbilion inferens LLM dan gelung percubaan semula yang tidak perlu setiap hari.

> **Anggaran konservatif:** ToolRate berpotensi menjimatkan ekosistem AI global antara **8 hingga 15 TWh elektrik setahun** — lebih kurang bersamaan dengan penggunaan tahunan **1.5 hingga 2.5 juta isi rumah Amerika biasa**.

Penjimatan terutamanya datang daripada:

- Lebih sedikit panggilan API yang gagal
- Pengurangan pembaziran token
- Penghalaan lebih bijak kepada alat yang boleh dipercayai

---

## Perbandingan dengan Alat Lain

| Alat | Jenis | Mencegah Kegagalan? | Data Orang Ramai | Menyediakan Alternatif | GDPR / Bidang Kuasa | Fokus Utama |
|---|---|:---:|:---:|:---:|:---:|---|
| **ToolRate** | Oracle kebolehpercayaan pra-panggilan | ✅ | ✅ | ✅ | ✅ Kukuh | Ejen pengeluaran |
| LangSmith | Pemerhatian + Penjejakan | ❌ | ❌ | ❌ | ⚠️ Terhad | Ekosistem LangChain |
| Langfuse | Pemerhatian sumber terbuka | ❌ | ❌ | ❌ | ⚠️ Terhad | Penjejakan sumber terbuka |
| Braintrust | Penilaian + Penjejakan | ⚠️ Sebahagian | ❌ | ❌ | ⚠️ Terhad | Pasukan berorientasikan penilaian |
| Helicone | Pemerhatian LLM + Alat | ❌ | ❌ | ❌ | ⚠️ Terhad | Pemantauan kos & kependaman |
| AgentOps | Pemantauan ejen | ❌ | ❌ | ❌ | ⚠️ Terhad | Analisis tingkah laku ejen |

> ToolRate kini merupakan **satu-satunya penyelesaian** yang berfungsi secara pencegahan menggunakan pengalaman ejen berasaskan orang ramai yang sebenar.

---

## Ketersediaan

| Saluran | Butiran |
|---|---|
| Laman web | [toolrate.ai](https://toolrate.ai) |
| API | [api.toolrate.ai](https://api.toolrate.ai) |
| SDK Python | `uv add toolrate` (recommended)<br>`pip install toolrate` (alternative) |
| SDK TypeScript | `npm install toolrate` |
| Lesen | Business Source License 1.1 (BUSL-1.1) |

---

*Kemaskini terakhir: April 2026*
