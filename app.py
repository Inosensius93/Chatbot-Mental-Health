import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import base64

# Konfigurasi awal
load_dotenv()

# Inisialisasi Gemini AI
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
except Exception as e:
    st.error(f"Error menginisialisasi AI: {str(e)}")
    st.stop()

# Konfigurasi halaman
st.set_page_config(
    page_title="Mental Health Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi session state
if "history" not in st.session_state:
    st.session_state.history = []
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_mood" not in st.session_state:
    st.session_state.user_mood = "netral"

# Fungsi utilitas
def reset_chat():
    st.session_state.history = []
    st.session_state.user_mood = "netral"

def export_chat():
    chat_text = "Riwayat Percakapan:\n\n"
    for chat in st.session_state.history:
        chat_text += f"User: {chat['user']}\n"
        chat_text += f"Bot: {chat['bot']}\n\n"

    b64 = base64.b64encode(chat_text.encode()).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="chat_history.txt">Download Riwayat Chat</a>'

def detect_emergency(message):
    emergency_keywords = ["bunuh diri", "mati aja", "depresi berat", "putus asa"]
    return any(keyword in message.lower() for keyword in emergency_keywords)

def analyze_sentiment(text):
    text = text.lower()
    positive = sum(word in text for word in ["senang", "bahagia", "baik", "terima kasih"])
    negative = sum(word in text for word in ["sedih", "marah", "buruk", "stress"])

    if positive > negative:
        return "positif"
    elif negative > positive:
        return "negatif"
    return "netral"

def generate_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Maaf, terjadi kesalahan: {str(e)}. Silakan coba lagi."

def build_prompt(history, new_message):
    mood_map = {
        "senang": "respon dengan semangat dan antusias",
        "sedih": "berikan dukungan emosional dan empati",
        "marah": "bersikap menenangkan dan netral",
        "netral": "bersikap ramah dan suportif"
    }

    prompt = (
        f"Kamu adalah chatbot kesehatan mental yang berperan sebagai teman dekat. {mood_map[st.session_state.user_mood]}. "
        "Gunakan bahasa santai, gaul, dan tidak kaku. Jangan tampilkan poin-poin atau penjelasan seperti (1. Validasi perasaan). Respon harus natural dan mengalir.\n"
        f"{'Nama pengguna: ' + st.session_state.user_name if st.session_state.user_name else ''}\n\n"
    )

    for entry in history:
        prompt += f"User: {entry['user']}\nChatbot: {entry['bot']}\n"

    prompt += f"User: {new_message}\nChatbot:"
    return prompt

def submit():
    user_message = st.session_state.user_input
    if user_message:
        if detect_emergency(user_message):
            emergency_response = (
                "Aku sangat khawatir dengan keadaanmu. Kamu tidak sendirian. ❤️\n\n"
                "Silakan hubungi:\n"
                "☎️ 119 (Layanan Darurat Kesehatan Mental)\n"
                "☎️ 112 (Darurat Nasional)\n"
                "Atau segera hubungi orang terdekat yang kamu percaya."
            )
            st.session_state.history.append({"user": user_message, "bot": emergency_response})
            st.session_state.user_input = ""
            return

        sentiment = analyze_sentiment(user_message)
        st.session_state.user_mood = {
            "positif": "senang",
            "negatif": "sedih",
            "netral": "netral"
        }[sentiment]

        prompt = build_prompt(st.session_state.history, user_message)
        with st.spinner("Chatbot sedang merespons..."):
            bot_response = generate_response(prompt)

        st.session_state.history.append({"user": user_message, "bot": bot_response})
        st.session_state.user_input = ""

# CSS Styling
st.markdown("""
<style>
:root {
    --primary: #6a8caf;
    --secondary: #a5b4fc;
    --bg-light: #f8fafc;
    --text-dark: #1e293b;
}

.chat-container {
    display: flex;
    flex-direction: column;
    max-height: 70vh;
    max-width: 800px;
    margin: 20px auto;
    border-radius: 16px;
    background: var(--bg-light);
    font-family: 'Inter', sans-serif;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}

.chat-header {
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: white;
    padding: 16px;
    font-weight: 600;
    text-align: center;
    border-radius: 16px 16px 0 0;
}

.chat-history {
    flex-grow: 1;
    overflow-y: auto;
    padding: 20px;
    background: white;
    min-height: 300px;
}

.user-message {
    background: #e0f2fe;
    color: var(--text-dark);
    padding: 12px 16px;
    border-radius: 16px 16px 0 16px;
    max-width: 75%;
    margin-left: auto;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.bot-message {
    background: white;
    color: var(--text-dark);
    padding: 12px 16px;
    border-radius: 16px 16px 16px 0;
    max-width: 75%;
    margin-right: auto;
    margin-bottom: 12px;
    border-left: 3px solid var(--primary);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.input-container {
    border-top: 1px solid #e2e8f0;
    padding: 15px;
    background: white;
    border-radius: 0 0 16px 16px;
}

.quick-replies {
    display: flex;
    gap: 8px;
    margin: 10px 0;
    flex-wrap: wrap;
}

.quick-reply-btn {
    background: #f1f5f9;
    border: none;
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
}

.quick-reply-btn:hover {
    background: var(--primary);
    color: white;
}

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Pengaturan Chatbot")

    st.session_state.user_name = st.text_input(
        "Nama Anda (opsional):", 
        value=st.session_state.user_name
    )

    st.markdown("**Pilih Mood Anda:**")
    moods = {
        "senang": "😊 Senang",
        "sedih": "😢 Sedih", 
        "marah": "😠 Marah",
        "netral": "😐 Netral"
    }

    for mood, label in moods.items():
        if st.button(
            label,
            key=f"mood_{mood}",
            on_click=lambda m=mood: setattr(st.session_state, "user_mood", m)
        ):
            st.session_state.user_mood = mood

    st.markdown("---")
    st.markdown("**Fitur Cepat:**")
    quick_topics = ["Stres", "Kecemasan", "Tidur", "Hubungan"]
    for topic in quick_topics:
        if st.button(f"💡 Tips {topic}"):
            st.session_state.user_input = f"Berikan tips mengatasi {topic.lower()}"
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset Percakapan", on_click=reset_chat):
        st.rerun()

    st.markdown(export_chat(), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Tentang Aplikasi:**")
    st.caption("""
    Chatbot kesehatan mental ini adalah teman berbicara virtual. 
    Bukan pengganti profesional. Jika dalam krisis, segera cari bantuan.
    """)

# MAIN CHAT INTERFACE DENGAN st.container()
with st.container():
    st.markdown(f"""
    <div class="chat-container">
        <div class="chat-header">
            🧠 Mental Health Buddy • {st.session_state.user_name or "Teman"} • Mood: {st.session_state.user_mood.capitalize()}
        </div>
        <div class="chat-history">
    """, unsafe_allow_html=True)

    for chat in st.session_state.history:
        st.markdown(f'<div class="user-message">{chat["user"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="bot-message">{chat["bot"]}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # Tutup chat-history

    # Quick replies
    quick_replies = [
        "Aku merasa sedih hari ini",
        "Bagaimana cara mengurangi stres?",
        "Ceritakan sesuatu yang menyenangkan",
        "Aku butuh motivasi"
    ]

    st.markdown('<div class="quick-replies">', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, reply in enumerate(quick_replies):
        if cols[i%2].button(reply, key=f"quick_{i}"):
            st.session_state.user_input = reply
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Input
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    st.text_input(
        "Tulis pesan...",
        key="user_input",
        on_change=submit,
        placeholder="Ketik sesuatu dan tekan Enter...",
        label_visibility="collapsed"
    )
    st.markdown("</div>", unsafe_allow_html=True)  # Tutup input-container
    st.markdown("</div>", unsafe_allow_html=True)  # Tutup chat-container

# Auto scroll
st.markdown("""
<script>
window.addEventListener('load', function() {
    const chatHistory = window.parent.document.querySelector('.chat-history');
    if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
});
</script>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("""
⚠️ Chatbot ini bukan pengganti bantuan profesional. 
Jika dalam krisis, segera hubungi layanan darurat setempat.
""")
