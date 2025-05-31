import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import base64

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="Mental Health Chatbot", page_icon="🧠", layout="centered")

# CSS untuk chat
st.markdown("""
    <style>
    .user-msg {
        text-align: right;
        background-color: #DCF8C6;
        padding: 10px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 75%;
        margin-left: auto;
    }
    .bot-msg {
        text-align: left;
        background-color: #F1F0F0;
        padding: 10px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 75%;
        margin-right: auto;
    }
    </style>
""", unsafe_allow_html=True)

# Inisialisasi state
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

# Fungsi-fungsi
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

def build_prompt(history, new_message):
    mood_prompt = {
        "senang": "respon dengan semangat dan antusias",
        "sedih": "berikan dukungan emosional dan empati",
        "marah": "bersikap menenangkan dan netral",
        "netral": "bersikap ramah dan suportif"
    }
    prompt = (
        f"Kamu adalah chatbot kesehatan mental yang ramah dan bersahabat. "
        f"{mood_prompt[st.session_state.user_mood]}. Gunakan bahasa santai dan mengalir.\n\n"
        f"{'Nama pengguna: ' + st.session_state.user_name if st.session_state.user_name else ''}\n\n"
    )
    for h in history:
        prompt += f"User: {h['user']}\nChatbot: {h['bot']}\n"
    prompt += f"User: {new_message}\nChatbot:"
    return prompt

def handle_message(user_message):
    if detect_emergency(user_message):
        emergency = (
            "Aku sangat khawatir dengan keadaanmu. Kamu tidak sendirian. ❤️\n\n"
            "Silakan hubungi:\n"
            "☎️ 119 (Layanan Darurat Kesehatan Mental)\n"
            "☎️ 112 (Darurat Nasional)\n"
            "Atau segera hubungi orang terdekat yang kamu percaya."
        )
        st.session_state.history.append({"user": user_message, "bot": emergency})
        return

    st.session_state.user_mood = {
        "positif": "senang",
        "negatif": "sedih",
        "netral": "netral"
    }[analyze_sentiment(user_message)]

    with st.spinner("Mengetik..."):
        prompt = build_prompt(st.session_state.history, user_message)
        response = model.generate_content(prompt)
        bot_reply = response.text.strip()

    st.session_state.history.append({"user": user_message, "bot": bot_reply})

# Halaman Awal
if not st.session_state.chat_started:
    st.title("🧠 Mental Health Chatbot")
    st.markdown("Halo! Saya teman bicara virtual kamu. Klik tombol di bawah untuk mulai.")
    if st.button("🚀 Mulai Chat"):
        st.session_state.chat_started = True
        st.rerun()
    st.stop()

# Form identitas pengguna (seperti pop-up)
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
    st.stop()

# Jika sudah siap chat
if st.session_state.ready_to_chat:
    st.markdown(f"### 👋 Hai {st.session_state.user_name or 'teman'}!")

    chat_container = st.container()
    with chat_container:
        for chat in st.session_state.history:
            st.markdown(f'<div class="user-msg">{chat["user"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">{chat["bot"]}</div>', unsafe_allow_html=True)

    # Quick Message
    st.markdown("#### 💬 Quick Message")
    quick_messages = [
        "Saya merasa cemas",
        "Saya butuh teman bicara",
        "Saya ingin cerita tentang hari saya",
        "Saya sedang stress karena kuliah",
        "Saya tidak tahu harus bagaimana"
    ]
    quick_col = st.columns(len(quick_messages))
    for i, msg in enumerate(quick_messages):
        if quick_col[i].button(msg):
            handle_message(msg)
            st.rerun()

    # Input Chat
    user_input = st.chat_input("Tulis pesan Anda...")
    if user_input:
        handle_message(user_input)
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("Pengaturan")
    st.markdown(f"**Nama:** {st.session_state.user_name or 'Belum diisi'}")
    st.markdown(f"**Mood:** {st.session_state.user_mood.capitalize()}")
    st.markdown("---")
    if st.button("🔄 Reset Percakapan"):
        reset_chat()
        st.rerun()
    st.markdown(export_chat(), unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Chatbot ini bukan pengganti profesional. Hubungi darurat jika butuh bantuan segera.")
