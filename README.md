# 🕌 SantriBot v2 — Asisten Digital Pondok Pesantren Anwarul Islam

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Powered%20by-Gemini%20API-4285F4?logo=googlegemini&logoColor=white" alt="Gemini API">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

<p align="center">
  <b>Chatbot Islami yang membantu santri mencari dalil Al-Quran & Hadits</b><br>
  <i>Referensi selalu diambil live dari database terverifikasi — tidak mengarang ayat/hadits.</i>
</p>

<!-- 📸 GANTI BARIS DI BAWAH DENGAN SCREENSHOT ASLI APLIKASI KAMU
     Simpan screenshot di folder screenshots/ lalu ganti nama filenya di sini -->
<p align="center">
  <img src="screenshots/tampilan-utama.png" alt="Tampilan SantriBot" width="700">
</p>

<p align="center">
  🔗 <a href="#">Live Demo</a> &nbsp;|&nbsp;
  📖 <a href="#-cara-menjalankan">Cara Install</a> &nbsp;|&nbsp;
  🗺️ <a href="#%EF%B8%8F-roadmap-pengembangan-selanjutnya">Roadmap</a>
</p>

---

## 📑 Daftar Isi

- [Apa yang Berubah](#-apa-yang-berubah-dari-versi-sebelumnya)
- [Kenapa Perlu RAG](#%EF%B8%8F-kenapa-perlu-sistem-rag-untuk-dalil)
- [Batasan yang Disengaja](#%EF%B8%8F-batasan-yang-disengaja-penting)
- [Teknologi](#%EF%B8%8F-teknologi)
- [Cara Menjalankan](#-cara-menjalankan)
- [Catatan Teknis API](#-catatan-teknis-penting-verifikasi-format-api)
- [Struktur Proyek](#-struktur-proyek)
- [Roadmap](#%EF%B8%8F-roadmap-pengembangan-selanjutnya)
- [Screenshot](#-screenshot-ui)

---

Versi lanjutan dari final project Hacktiv8 *LLM-Based Tools and Gemini API
Integration for Data Scientists*, dikembangkan lebih lanjut supaya
benar-benar bisa dipakai oleh Pondok Pesantren Anwarul Islam maupun pondok
lain.

## 🎯 Apa yang Berubah dari Versi Sebelumnya?

| Aspek | Versi 1 (Final Project) | Versi 2 (Sekarang) |
|---|---|---|
| Gaya bahasa | Formal-kaku | Hangat, membumi, tetap sopan |
| Sumber dalil | Dari "ingatan" LLM (berisiko salah kutip) | **RAG**: diambil live dari API Quran & Hadits terverifikasi |
| Tampilan | Default Streamlit | Custom tema hijau-emas islami, kartu dalil dengan teks Arab |
| Fokus | Generik pondok pesantren | Khusus branding Anwarul Islam |

## 🛡️ Kenapa Perlu Sistem RAG untuk Dalil?

LLM seperti Gemini **bisa saja salah mengutip ayat atau menyebut nomor
hadits yang keliru**, karena ia menjawab berdasarkan pola statistik, bukan
database pasti. Untuk urusan agama, ini fatal karena berisiko menyandarkan
sesuatu ke Al-Quran/Hadits yang sebenarnya tidak ada di sana.

Maka SantriBot v2 didesain 3 tahap:

1. **Reference Finder** — Gemini mengusulkan *kandidat* referensi (misalnya
   "kemungkinan QS. Al-Baqarah ayat 155 relevan").
2. **Verification Fetch** — Sistem benar-benar mengambil teks itu dari API
   resmi (`api.quran.gading.dev` dan `api.hadith.gading.dev`). Jika gagal
   ditemukan, kandidat itu dibuang.
3. **Grounded Answer** — Gemini menyusun jawaban akhir **hanya** berdasarkan
   teks yang berhasil diverifikasi di atas. Jika tidak ada yang cocok,
   Gemini wajib jujur bilang belum menemukan dalil spesifik, dan mengarahkan
   ke ustadz/kyai — bukan mengarang.

Setiap dalil yang tampil di layar diberi label **"✅ Terverifikasi"** dan
ditampilkan lengkap dengan teks Arab + terjemahan resminya.

## ⚠️ Batasan yang Disengaja (Penting!)

- SantriBot **tidak dirancang untuk memutuskan hukum fiqih/fatwa final**,
  apalagi untuk masalah khilafiyah (perbedaan pendapat ulama). Ia hanya
  membantu *mencari & menyajikan dalil* sebagai bahan belajar. Keputusan
  hukum tetap harus melalui Kyai/Ustadz pondok.
- Karena API hadits yang dipakai belum mendukung pencarian berbasis kata
  kunci (hanya berbasis nomor per kitab), ketepatan relevansi hadits yang
  diambil bisa saja tidak 100% presisi — namun **isinya tetap dijamin asli**
  (bukan karangan), karena selalu diambil dari database resmi.
- Untuk kitab-kitab ulama (kitab kuning), fitur ini **belum diimplementasikan**
  di versi ini karena membutuhkan teks digital asli dari kitab yang
  bersangkutan (lihat bagian Roadmap di bawah).

## 🛠️ Teknologi

- **Python 3.9+** & **Streamlit** (UI)
- **Google Gen AI SDK (`google-genai`)** — model `gemini-2.5-flash`
- **api.quran.gading.dev** — sumber teks Al-Quran + terjemahan Kemenag
- **api.hadith.gading.dev** — sumber teks Hadits 9 perawi + terjemahan
- **python-dotenv**, **requests**

## 🚀 Cara Menjalankan

1. **Download semua file** ke satu folder, misalnya `santribot-v2`.

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfigurasi API Key**
   - Ambil gratis di [Google AI Studio](https://aistudio.google.com/apikey)
   - Copy `.env.example` menjadi `.env`, isi `GEMINI_API_KEY`

4. **Jalankan**
   ```bash
   streamlit run app.py
   ```

5. Buka `http://localhost:8501`

## 🧪 Catatan Teknis Penting: Verifikasi Format API

API `api.quran.gading.dev` dan `api.hadith.gading.dev` adalah proyek
open-source pihak ketiga yang formatnya bisa saja sedikit berubah dari
waktu ke waktu. Kode di `app.py` (fungsi `fetch_quran_ayat` dan
`fetch_hadith`) sudah ditulis defensif (mencoba beberapa kemungkinan nama
field), tapi **sangat disarankan untuk mengetes dulu** setelah instalasi:

1. Coba tanya sesuatu yang jelas berkaitan dengan dalil, misalnya:
   *"Apa dalil tentang sabar dalam menghadapi ujian?"*
2. Perhatikan apakah kartu dalil (✅ Terverifikasi) muncul dengan teks Arab
   dan terjemahan yang benar.
3. **Jika kartu dalil tidak muncul padahal seharusnya ada**, kemungkinan
   besar struktur JSON dari API sudah berubah. Buka langsung di browser:
   `https://api.quran.gading.dev/surah/2/155` — lalu kirim contoh hasil
   JSON tersebut, dan kode parsing di `fetch_quran_ayat`/`fetch_hadith` bisa
   disesuaikan.
4. Perlu diperhatikan juga: API ini memiliki **rate limit** (sekitar
   10 request/5 menit per alamat IP). Untuk pemakaian pondok yang lebih
   ramai, disarankan meng-*host* API tersebut sendiri (kode sumbernya
   open-source di GitHub: `gadingnst/quran-api` dan `gadingnst/hadith-api`).

## 📂 Struktur Proyek

```
santribot-v2/
├── app.py              # Aplikasi utama (UI + RAG pipeline)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🗺️ Roadmap Pengembangan Selanjutnya

1. **Integrasi Kitab Kuning** — memungkinkan pondok mengunggah file digital
   kitab yang biasa dikaji (PDF/teks hasil OCR), lalu sistem melakukan
   pencarian semantik (embedding) di dalamnya sebagai sumber referensi
   tambahan yang juga terverifikasi (karena berasal dari file yang memang
   dimiliki pondok, bukan karangan AI).
2. **Local caching Quran/Hadits** — menyimpan hasil fetch API secara lokal
   supaya lebih cepat dan tidak terkena rate limit saat banyak santri
   memakai bersamaan.
3. **Multi-user & riwayat per santri** — menyimpan riwayat percakapan per
   akun santri (perlu sistem login sederhana).
4. **Deploy publik** — deploy ke Streamlit Community Cloud (gratis) supaya
   bisa diakses semua santri lewat link, tanpa perlu install apa pun di HP.

## 📸 Screenshot UI

*(Tambahkan screenshot tampilan aplikasi setelah dijalankan.)*

## ⚠️ Catatan Akhir

SantriBot adalah alat bantu belajar dan pencarian referensi, **bukan
pengganti otoritas Kyai/Ustadz** dalam menetapkan hukum syariat. Gunakan
sebagai pendamping belajar, dan selalu verifikasi ulang untuk keputusan
hukum yang penting.

---
Dikembangkan sebagai proyek lanjutan Final Project *LLM-Based Tools and
Gemini API Integration for Data Scientists* — Hacktiv8, untuk kemaslahatan
Pondok Pesantren Anwarul Islam. 🤲
