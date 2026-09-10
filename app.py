"""
SantriBot v2 — Asisten Digital Pondok Pesantren Anwarul Islam
================================================================
Upgrade dari final project Hacktiv8: sekarang dengan RAG (Retrieval-Augmented
Generation) yang menarik dalil Al-Quran & Hadits LANGSUNG dari sumber
terverifikasi (API), bukan dari "ingatan" LLM — supaya tidak ada risiko
salah kutip ayat atau mengarang hadits.

Alur kerja (2 tahap, demi keamanan dalil):
  1) REFERENCE FINDER  : Gemini menganalisis pertanyaan pengguna, mengusulkan
     kandidat referensi (surah:ayat / kitab hadits:nomor) yang relevan.
  2) VERIFICATION FETCH : Kandidat itu diambil betulan dari API Quran/Hadits.
     Hanya teks yang BERHASIL diambil (real, terverifikasi) yang diteruskan.
  3) FINAL ANSWER       : Gemini menyusun jawaban HANYA berdasarkan teks
     terverifikasi tsb. Jika tidak ada referensi yang berhasil/relevan,
     Gemini wajib jujur menyatakan itu dan mengarahkan ke ustadz/kyai.
"""

import os
import re
import json
import requests
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# =========================
# KONFIGURASI DASAR
# =========================
st.set_page_config(
    page_title="SantriBot | Pondok Pesantren Anwarul Islam",
    page_icon="🕌",
    layout="centered",
)

NAMA_PONDOK = "Pondok Pesantren Anwarul Islam"
MODEL_NAME = "gemini-3.6-flash"

QURAN_API_BASE = "https://api.quran.gading.dev"
HADITH_API_BASE = "https://api.hadith.gading.dev"

HADITH_BOOKS = {
    "bukhari": "Shahih Bukhari",
    "muslim": "Shahih Muslim",
    "tirmidzi": "Sunan Tirmidzi",
    "nasai": "Sunan Nasai",
    "abudaud": "Sunan Abu Daud",
    "ibnumajah": "Sunan Ibnu Majah",
    "ahmad": "Musnad Ahmad",
    "darimi": "Sunan Darimi",
    "malik": "Muwatha' Malik",
}


def is_quota_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


QUOTA_ERROR_MESSAGE = (
    "⏳ Mohon maaf, kuota API Gemini gratis untuk hari ini sudah habis "
    "(ini batas dari akun Google gratisan, bukan masalah dari SantriBot). "
    "Silakan coba lagi dalam beberapa saat, atau besok setelah kuota "
    "harian direset. Kalau ingin dipakai lebih intensif oleh banyak "
    "santri sekaligus, pertimbangkan mengaktifkan billing (berbayar) di "
    "Google AI Studio supaya limitnya jauh lebih tinggi."
)

INFO_PONDOK = """\
- Nama resmi: Pondok Pesantren Anwarul Islam
- Fokus pembelajaran: Al-Quran, Hadits, Fiqih, Akhlak, dan kitab kuning
- Untuk urusan administrasi, jadwal detail, dan konsultasi hukum fiqih yang
  kompleks, santri/wali santri disarankan menghubungi pengurus/ustadz pondok
  secara langsung.
"""

SYSTEM_PROMPT_TEMPLATE = """\
Kamu adalah SantriBot, asisten digital untuk {nama_pondok}.

GAYA BAHASA:
- Bahasa Indonesia yang hangat, membumi, dan mudah dipahami — seperti kakak
  senior/ustadz muda yang sabar menjelaskan ke adik-adik santri. TIDAK kaku,
  TIDAK terlalu formal-birokratis, tapi tetap santun dan menjaga adab.
- Boleh gunakan sapaan akrab seperti "Ananda" atau langsung ke intinya
  dengan ramah, sesuaikan dengan nada pertanyaan pengguna.
- Hindari bahasa yang menggurui atau terkesan menceramahi berlebihan.

TUGAS UTAMA:
Membantu santri/wali santri/pengurus mencari referensi dalil Al-Quran dan
Hadits yang berkaitan dengan pertanyaan mereka, serta memberi penjelasan
ringkas dan mudah dicerna.

ATURAN PALING PENTING (KEAMANAN DALIL):
- Kamu HANYA boleh mengutip ayat Al-Quran atau Hadits dari teks yang
  diberikan di bagian "REFERENSI TERVERIFIKASI" di bawah. Teks itu diambil
  langsung dari database resmi, BUKAN dari ingatanmu sendiri.
- JANGAN PERNAH mengarang, mengira-ngira, atau mengutip dari ingatan ayat/
  hadits di luar yang tersedia di REFERENSI TERVERIFIKASI. Ini prinsip yang
  tidak boleh dilanggar karena menyangkut keakuratan agama.
- Jika REFERENSI TERVERIFIKASI kosong atau tidak relevan dengan pertanyaan,
  katakan dengan jujur: "SantriBot belum menemukan dalil spesifik yang
  terverifikasi untuk topik ini." Tetap boleh memberi penjelasan umum
  berdasarkan pengetahuan Islam dasar yang tidak kontroversial, TAPI jangan
  mengklaimnya sebagai kutipan ayat/hadits.
- Untuk pertanyaan hukum fiqih yang kompleks, ikhtilaf ulama, atau
  memerlukan fatwa personal, selalu arahkan ke Kyai/Ustadz pembimbing di
  pondok untuk keputusan final — sampaikan ini secara natural, bukan sebagai
  disclaimer templated yang kaku.
- Setiap kali mengutip dalil dari REFERENSI TERVERIFIKASI, sebutkan sumbernya
  dengan jelas (contoh: "QS. Al-Baqarah: 155" atau "HR. Muslim No. 2699").

DATA PONDOK:
{info_pondok}

REFERENSI TERVERIFIKASI (hasil pencarian real-time, gunakan HANYA ini untuk kutipan dalil):
{verified_context}
"""

REFERENCE_FINDER_PROMPT = """\
Kamu adalah mesin pencari referensi dalil Islam. Berdasarkan pertanyaan
pengguna berikut, usulkan MAKSIMAL 2 ayat Al-Quran dan MAKSIMAL 2 hadits yang
kemungkinan besar relevan. Jika pertanyaan tidak berkaitan dengan topik
keislaman/dalil sama sekali (misal sekadar sapaan atau tanya jadwal), kembalikan
array kosong untuk keduanya.

Untuk hadits, pilih dari daftar kitab berikut saja (gunakan key persis ini):
bukhari, muslim, tirmidzi, nasai, abudaud, ibnumajah, ahmad, darimi, malik

PENTING: Ini hanya KANDIDAT AWAL yang akan diverifikasi ulang lewat database,
jadi usahakan seakurat mungkin berdasarkan pengetahuanmu, tapi tidak apa jika
tidak 100% pasti karena akan diverifikasi.

Balas HANYA dalam format JSON valid seperti ini, tanpa teks lain, tanpa markdown:
{{"quran": [{{"surah": <nomor 1-114>, "ayah": <nomor ayat>}}], "hadith": [{{"book": "<key>", "number": <nomor>}}]}}

Pertanyaan pengguna: "{question}"
"""


# =========================
# FUNGSI FETCH TERVERIFIKASI
# =========================
def fetch_quran_ayat(surah: int, ayah: int):
    """Ambil satu ayat Al-Quran dari API resmi. Return None jika gagal."""
    try:
        r = requests.get(f"{QURAN_API_BASE}/surah/{surah}/{ayah}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("data", {})
        arabic = (
            data.get("text", {}).get("arab")
            or data.get("arab")
            or data.get("text_arab")
        )
        translation = (
            data.get("translation", {}).get("id")
            or data.get("translation")
            or data.get("text_indonesia")
        )
        surah_name = (
            data.get("surah", {}).get("name", {}).get("transliteration", {}).get("id")
            or data.get("surah", {}).get("name", {}).get("short")
            or f"Surah {surah}"
        )
        if not arabic or not translation:
            return None
        return {
            "type": "quran",
            "ref": f"QS. {surah_name}: {ayah}",
            "arabic": arabic,
            "translation": translation,
        }
    except Exception:
        return None


def fetch_hadith(book: str, number: int):
    """Ambil satu hadits dari API resmi. Return None jika gagal."""
    book = book.lower().strip()
    if book not in HADITH_BOOKS:
        return None
    try:
        r = requests.get(f"{HADITH_API_BASE}/books/{book}/{number}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("data", {})
        contents = data.get("contents", data)
        arabic = contents.get("arab") if isinstance(contents, dict) else None
        translation = contents.get("id") if isinstance(contents, dict) else None
        if not arabic or not translation:
            return None
        return {
            "type": "hadith",
            "ref": f"HR. {HADITH_BOOKS[book]} No. {number}",
            "arabic": arabic,
            "translation": translation,
        }
    except Exception:
        return None


def find_candidate_references(client, question: str):
    """Tahap 1: minta Gemini mengusulkan kandidat referensi (belum terverifikasi)."""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[REFERENCE_FINDER_PROMPT.format(question=question)],
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=300),
        )
        text = response.text.strip()
        text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception:
        return {"quran": [], "hadith": []}


SAPAAN_KEYWORDS = {
    "hai", "halo", "hallo", "hei", "hey", "assalamualaikum",
    "assalamu'alaikum", "makasih", "terima kasih", "thanks", "oke", "ok",
    "sip", "baik", "iya", "ya", "siap", "test", "tes", "p", "pagi",
    "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
}


def is_probably_smalltalk(text: str) -> bool:
    """Deteksi cepat (tanpa panggil Gemini) untuk sapaan/basa-basi pendek,
    supaya tidak buang-buang kuota API untuk hal yang jelas tidak butuh
    pencarian dalil sama sekali."""
    cleaned = text.strip().lower().strip("!?.,")
    if len(cleaned) <= 3:
        return True
    return cleaned in SAPAAN_KEYWORDS


def gather_verified_references(client, question: str):
    """Tahap 2: verifikasi kandidat dengan fetch nyata ke API. Hanya hasil sukses yang dipakai."""
    if is_probably_smalltalk(question):
        return []
    candidates = find_candidate_references(client, question)
    verified = []
    for q in candidates.get("quran", [])[:2]:
        result = fetch_quran_ayat(q.get("surah"), q.get("ayah"))
        if result:
            verified.append(result)
    for h in candidates.get("hadith", [])[:2]:
        result = fetch_hadith(h.get("book", ""), h.get("number"))
        if result:
            verified.append(result)
    return verified


def format_verified_context(verified: list) -> str:
    if not verified:
        return "(Tidak ada referensi terverifikasi yang ditemukan untuk pertanyaan ini.)"
    blocks = []
    for v in verified:
        blocks.append(f"[{v['ref']}]\nArab: {v['arabic']}\nTerjemahan: {v['translation']}")
    return "\n\n".join(blocks)


# =========================
# CUSTOM CSS — TEMA ISLAMI HIJAU & EMAS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    /* Latar belakang utama dibiarkan mengikuti tema Light/Dark/System
       bawaan Streamlit secara alami — supaya SantriBot berperilaku
       seperti aplikasi modern lain (Claude, ChatGPT, dst) yang
       menyesuaikan otomatis, bukan dipaksa satu warna saja. */
}

.santribot-header {
    background: linear-gradient(135deg, #0b6e4f 0%, #145c3f 60%, #0b4a34 100%);
    padding: 28px 24px;
    border-radius: 18px;
    text-align: center;
    margin-bottom: 18px;
    box-shadow: 0 8px 24px rgba(11, 110, 79, 0.25);
}
.santribot-header h1 {
    color: #f4d35e;
    font-size: 30px;
    margin: 0 0 4px 0;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.santribot-header p {
    color: #eafaf1;
    margin: 0;
    font-size: 14px;
    opacity: 0.9;
}

.disclaimer-banner {
    background: #fff8e6;
    border-left: 4px solid #f4d35e;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 13px;
    color: #6b5a1e;
    margin-bottom: 18px;
}

.dalil-card {
    background: #ffffff;
    border: 1px solid #d8ead9;
    border-left: 4px solid #0b6e4f;
    border-radius: 12px;
    padding: 14px 18px;
    margin: 10px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.dalil-ref {
    color: #0b6e4f;
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 6px;
}
.dalil-arabic {
    font-family: 'Amiri', serif;
    font-size: 22px;
    text-align: right;
    direction: rtl;
    color: #17301f;
    line-height: 1.9;
    margin-bottom: 8px;
}
.dalil-translation {
    font-size: 14px;
    color: #333;
    font-style: italic;
}

/* Paksa teks chat selalu kontras & terbaca, apapun tema terang/gelap
   yang dipakai sistem/browser pengguna */
[data-testid="stChatMessage"] {
    background-color: #ffffff !important;
    border: 1px solid #e3ece4 !important;
    border-radius: 14px !important;
}
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li,
[data-testid="stChatMessageContent"] span,
[data-testid="stChatMessageContent"] strong,
[data-testid="stChatMessageContent"] ol,
[data-testid="stChatMessageContent"] ul {
    color: #1a2e22 !important;
}
[data-testid="stChatMessageContent"] a {
    color: #0b6e4f !important;
}
/* Input kotak chat di bagian bawah juga dipaksa kontras (kotak ini
   mandiri: background & teksnya sepasang, jadi selalu terbaca apapun
   tema sistemnya, tanpa perlu ganggu elemen lain) */
[data-testid="stChatInput"] textarea {
    color: #1a2e22 !important;
    background-color: #ffffff !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #6b8577 !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HEADER
# =========================
st.markdown(f"""
<div class="santribot-header">
    <h1>🕌 SantriBot</h1>
    <p>Asisten Digital {NAMA_PONDOK}</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer-banner">
    ⚠️ SantriBot membantu mencari <b>referensi dalil</b> dari database Al-Quran &amp; Hadits
    terverifikasi. Untuk penetapan hukum (fatwa) resmi, tetap perlu musyawarah
    langsung dengan Kyai/Ustadz pengasuh pondok.
</div>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("⚙️ Pengaturan")
    temperature = st.slider("Kreativitas jawaban (temperature)", 0.0, 1.0, 0.4, 0.1)
    max_tokens = st.slider("Panjang maksimum jawaban", 256, 2048, 1200, 128)
    show_dalil_cards = st.checkbox("Tampilkan kartu dalil terverifikasi", value=True)

    st.divider()
    if st.button("🗑️ Hapus Riwayat Percakapan"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "SantriBot mengambil dalil secara real-time dari:\n\n"
        "- api.quran.gading.dev\n"
        "- api.hadith.gading.dev\n\n"
        "Jawaban tidak mengandalkan ingatan AI untuk kutipan agama."
    )

# =========================
# INISIALISASI CLIENT
# =========================
def get_api_key():
    """Ambil API key dari Streamlit Secrets (kalau dideploy di Streamlit
    Community Cloud) atau dari file .env (kalau dijalankan lokal)."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")


api_key = get_api_key()
if not api_key:
    st.warning("⚠️ GEMINI_API_KEY belum diatur. Lihat `.env.example` untuk cara mengaturnya.")
client = genai.Client(api_key=api_key) if api_key else None

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("verified") and show_dalil_cards:
            for v in msg["verified"]:
                st.markdown(f"""
                <div class="dalil-card">
                    <div class="dalil-ref">✅ {v['ref']} — Terverifikasi</div>
                    <div class="dalil-arabic">{v['arabic']}</div>
                    <div class="dalil-translation">{v['translation']}</div>
                </div>
                """, unsafe_allow_html=True)

prompt = st.chat_input("Tanyakan sesuatu ke SantriBot...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if client is None:
        with st.chat_message("assistant"):
            st.error("API key belum dikonfigurasi, SantriBot belum bisa menjawab.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Mencari dalil terverifikasi..."):
                verified_refs = gather_verified_references(client, prompt)
                verified_context = format_verified_context(verified_refs)

            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                nama_pondok=NAMA_PONDOK,
                info_pondok=INFO_PONDOK,
                verified_context=verified_context,
            )

            history = []
            for msg in st.session_state.messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

            with st.spinner("SantriBot sedang menyusun jawaban..."):
                try:
                    chat = client.chats.create(
                        model=MODEL_NAME,
                        history=history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        ),
                    )
                    response = chat.send_message(prompt)
                    answer = response.text
                except Exception as e:
                    if is_quota_error(e):
                        answer = QUOTA_ERROR_MESSAGE
                    else:
                        answer = f"Mohon maaf, terjadi kendala teknis: {e}"

            st.markdown(answer)
            if verified_refs and show_dalil_cards:
                for v in verified_refs:
                    st.markdown(f"""
                    <div class="dalil-card">
                        <div class="dalil-ref">✅ {v['ref']} — Terverifikasi</div>
                        <div class="dalil-arabic">{v['arabic']}</div>
                        <div class="dalil-translation">{v['translation']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "verified": verified_refs,
        })
