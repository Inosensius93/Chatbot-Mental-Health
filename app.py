import streamlit as st
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import google.generativeai as genai
import itertools
from google.api_core.exceptions import ResourceExhausted
import base64
import re
import os

# Konfigurasi halaman
st.set_page_config(page_title="Hybrid Interactive Chatbot", page_icon="🧠", layout="centered")

# --- Konfigurasi API Key dari Streamlit Secrets ---
try:
    api_keys_env = st.secrets["GOOGLE_API_KEYS"]
except Exception:
    st.error("❌ Tidak dapat menemukan GOOGLE_API_KEYS di Streamlit Secrets. Harap tambahkan.")
    st.stop()

if not api_keys_env:
    st.error("❌ Nilai GOOGLE_API_KEYS di Streamlit Secrets kosong.")
    st.stop()

api_keys = api_keys_env.split(",")
api_key_cycle = itertools.cycle(api_keys)
current_api_key = next(api_key_cycle)
genai.configure(api_key=current_api_key)

def switch_api_key():
    """Ganti ke API key berikutnya."""
    global current_api_key
    current_api_key = next(api_key_cycle)
    genai.configure(api_key=current_api_key)

# --- Memuat Model dari Hugging Face Hub ---
# GANTI DENGAN NAMA REPOSITORI MODEL ANDA DI HUGGING FACE
MODEL_NAME_ON_HUB = "Inosensius/chatbot-mental-health" # <-- PASTIKAN INI BENAR

@st.cache_resource
def load_model_from_hub():
    """Mengunduh dan menyimpan model & tokenizer dari Hugging Face Hub."""
    with st.spinner(f"Memuat model '{MODEL_NAME_ON_HUB}'... Ini mungkin butuh beberapa menit."):
        try:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME_ON_HUB)
            model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME_ON_HUB)
            #st.success("Model berhasil dimuat!")
            return tokenizer, model
        except Exception as e:
            st.error(f"❌ Gagal memuat model dari Hugging Face. Pastikan nama repositori '{MODEL_NAME_ON_HUB}' sudah benar dan bersifat publik. Error: {e}")
            st.stop()

# Memanggil fungsi baru untuk memuat model
hf_tokenizer, hf_model = load_model_from_hub()

def local_chat(question: str) -> str:
    """Fungsi ini sekarang menggunakan model dari Hugging Face."""
    prompt = f"Instruksi: Berikan jawaban empatik dan santai.\nPertanyaan: {question}"
    inputs = hf_tokenizer(prompt, return_tensors="pt").to(hf_model.device)

    with torch.no_grad():
        outputs = hf_model.generate(
            **inputs,
            max_length=150  # Hanya max_length yang kita butuhkan
        )

    response = hf_tokenizer.decode(outputs[0], skip_special_tokens=True)
    return re.sub(r"<extra_id_\\d+>", "", response).strip()

def hybrid_chat(user_message: str) -> str:
    """Fungsi hybrid yang menggunakan Gemini dan fallback ke model Hugging Face."""
    local_response = local_chat(user_message)
    history_text = ""
    try:
        if hasattr(st.session_state, 'history') and st.session_state.history:
            recent_history = st.session_state.history[-3:]
            for chat in recent_history:
                if isinstance(chat, dict) and 'user' in chat and 'bot' in chat:
                    user_msg = str(chat['user']).strip()
                    bot_msg = str(chat['bot']).strip()
                    if user_msg and bot_msg:
                        history_text += f"User: {user_msg}\nBot: {bot_msg}\n"
    except Exception as e:
        print(f"Error processing chat history: {e}")
        history_text = ""
    prompt_gemini = f"""Kamu adalah chatbot kesehatan mental yang ramah, santai, dan empatik bernama MentalBuddy.

Aturan penting:
- Baca dengan teliti pesan user dan berikan respons yang relevan.
- Selalu mulai dengan validasi emosional yang natural. **Gunakan variasi kalimat agar tidak terdengar berulang.** Contohnya: "Aku bisa bayangin betapa beratnya itu untukmu...", "Kedengarannya sulit ya, terima kasih sudah mau berbagi denganku.", "Wajar banget kok merasa seperti itu, kamu nggak sendirian.", atau "Aku turut merasakan apa yang kamu alami."
- **Setelah memberikan validasi, periksa maksud user:**
    - **Jika user MENGULANGI perasaannya tanpa memberikan detail baru,** berhenti meminta detail. Alihkan percakapan dengan menawarkan satu teknik menenangkan yang sederhana (seperti teknik pernapasan atau grounding) atau ajukan pertanyaan reflektif yang lembut. Contoh: "Aku bisa bayangin betapa beratnya tekanan itu... Mungkin kita bisa coba satu hal kecil untuk meredakannya sekarang, mau?"
    - **Jika user ingin bercerita atau meluapkan perasaan,** ajak mereka untuk bercerita lebih lanjut ("Kalau kamu nyaman, boleh cerita lebih detail?").
    - **Jika user secara eksplisit meminta 'tips', 'saran', atau 'cara mengatasi',** berikan 2-3 poin saran yang praktis, singkat, dan actionable. Hindari daftar yang terlalu panjang.
- **Setelah memberikan saran,** akhiri dengan pertanyaan terbuka seperti "Gimana menurutmu?" atau "Apakah ada tips yang ingin kamu coba?".
- Gunakan bahasa Indonesia yang natural dan santai.
- Maksimal 2-3 kalimat per respons.
- Jangan memberikan saran medis atau diagnosis profesional.

{f"Riwayat percakapan sebelumnya:{chr(10)}{history_text}" if history_text else "Ini adalah percakapan pertama."}

Pesan user saat ini: "{user_message}"

Berikan respons yang tepat, natural, dan relevan sesuai aturan di atas:"""

    for attempt in range(len(api_keys)):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt_gemini)
            
            if response and response.text and response.text.strip():
                gemini_response = response.text.strip()
                if len(gemini_response) > 10 and not gemini_response.startswith("Error"):
                    return gemini_response
                else:
                    switch_api_key()
                    continue
            else:
                switch_api_key()
                continue
                
        except ResourceExhausted:
            print(f"API Key {current_api_key[:10]}... habis kuota, switching...")
            switch_api_key()
            continue
        except Exception as e:
            print(f"Error dengan API Key: {e}")
            switch_api_key()
            continue

    return local_response

# --- Sisa kode UI Anda tidak perlu diubah, sudah bagus ---

def reset_chat():
    st.session_state.history = []
    st.session_state.user_mood = "netral"
    st.session_state.ready_to_chat = False
    st.session_state.chat_started = False

def export_chat():
    chat_text = "Riwayat Percakapan:\n\n"
    for chat in st.session_state.history:
        chat_text += f"User: {chat['user']}\nBot: {chat['bot']}\n\n"
    b64 = base64.b64encode(chat_text.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="chat_history.txt">Download Riwayat Chat</a>'

def detect_emergency(msg):
    keywords = ["bunuh diri", "mati aja", "depresi berat", "putus asa"]
    return any(k in msg.lower() for k in keywords)

def analyze_sentiment(text):
    text = text.lower()
    pos = sum(w in text for w in ["senang", "bahagia", "baik", "terima kasih"])
    neg = sum(w in text for w in ["sedih", "marah", "buruk", "stress"])
    return "positif" if pos > neg else "negatif" if neg > pos else "netral"

if "chat_started" not in st.session_state:
    st.session_state.chat_started = False
if "ready_to_chat" not in st.session_state:
    st.session_state.ready_to_chat = False
if "history" not in st.session_state:
    st.session_state.history = []
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_mood" not in st.session_state:
    st.session_state.user_mood = "netral"

if not st.session_state.chat_started:
    st.title("🧠 Hybrid Interactive Chatbot")
    st.markdown("Halo! Saya teman bicara virtual kamu. Klik tombol di bawah untuk mulai.")
    if st.button("🚀 Mulai Chat"):
        st.session_state.chat_started = True
        st.rerun()
    st.stop()

if st.session_state.chat_started and not st.session_state.ready_to_chat:
    with st.form("user_info_form"):
        st.subheader("Sebelum mulai, kenalan dulu yuk 😊")
        name = st.text_input("Nama Anda (opsional):")
        mood = st.radio("Bagaimana suasana hati Anda hari ini?", ["😊 Senang", "😢 Sedih", "😠 Marah", "😐 Netral"])
        submitted = st.form_submit_button("Lanjut ke Chat")
        if submitted:
            st.session_state.user_name = name
            st.session_state.user_mood = {
                "😊 Senang": "senang",
                "😢 Sedih": "sedih",
                "😠 Marah": "marah",
                "😐 Netral": "netral"
            }[mood]
            st.session_state.ready_to_chat = True
            st.rerun()

if st.session_state.ready_to_chat:
    st.markdown(f"### 👋 Hai {st.session_state.user_name or 'teman'}!")

    for chat in st.session_state.history:
        st.markdown(f"🧍‍♂️ **User**: {chat['user']}")
        st.markdown(f"🤖 **Bot**: {chat['bot']}")

    user_input = st.chat_input("Tulis pesan Anda...")
    if user_input:
        if detect_emergency(user_input):
            emergency = (
                "Aku sangat khawatir dengan keadaanmu. Kamu tidak sendirian. ❤️\n\n"
                "Silakan hubungi:\n"
                "☎️ 119 (Layanan Darurat Kesehatan Mental)\n"
                "☎️ 112 (Darurat Nasional)\n"
                "Atau segera hubungi orang terdekat yang kamu percaya."
            )
            st.session_state.history.append({"user": user_input, "bot": emergency})
        else:
            st.session_state.user_mood = {
                "positif": "senang",
                "negatif": "sedih",
                "netral": "netral"
            }[analyze_sentiment(user_input)]

            with st.spinner("Mengetik..."):
                bot_response = hybrid_chat(user_input)

            st.session_state.history.append({"user": user_input, "bot": bot_response})

        st.rerun()

with st.sidebar:
    st.header("Pengaturan")
    st.markdown(f"**Nama:** {st.session_state.user_name or 'Belum diisi'}")
    st.markdown(f"**Mood:** {st.session_state.user_mood.capitalize()}")
    if st.button("🔄 Reset Percakapan"):
        reset_chat()
        st.rerun()
    st.markdown(export_chat(), unsafe_allow_html=True)
