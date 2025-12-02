import streamlit as st
from rag_pipeline import RAGPipeline

st.set_page_config(page_title="Baby AI", page_icon="👶", layout="wide", initial_sidebar_state="collapsed")

if "rag" not in st.session_state:
    st.session_state.rag = RAGPipeline()
if "mic_on" not in st.session_state:
    st.session_state.mic_on = False
if "ai_on" not in st.session_state:
    st.session_state.ai_on = True
if "talking" not in st.session_state:
    st.session_state.talking = False

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.baby-container {
    text-align: center;
    padding: 30px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.baby-image {
    border-radius: 50%;
    border: 8px solid #fff;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    transition: all 0.3s;
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-20px); }
}
.baby-image:hover {
    transform: scale(1.1) translateY(-10px);
}
.talking {
    animation: talk 0.4s infinite, float 3s ease-in-out infinite;
    border-color: #FF5722;
    box-shadow: 0 0 40px rgba(255,87,34,0.8);
}
@keyframes talk {
    0%, 100% { transform: scale(1) rotate(0deg); }
    25% { transform: scale(1.05) rotate(-5deg); }
    75% { transform: scale(1.05) rotate(5deg); }
}
.title {
    color: white;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    font-size: 3em;
    margin-bottom: 20px;
}
.status-text {
    color: white;
    font-size: 1.5em;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}
stButton>button {
    background: linear-gradient(45deg, #4CAF50, #45a049);
    color: white;
    border: none;
    border-radius: 25px;
    padding: 15px 30px;
    font-size: 1.2em;
    font-weight: bold;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transition: all 0.3s;
}
stButton>button:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="baby-container">', unsafe_allow_html=True)

st.markdown("<h1 class='title'>👶 Baby AI Assistant</h1>", unsafe_allow_html=True)

img_class = "talking" if st.session_state.talking else ""
st.markdown(f'<div style="text-align: center;"><img src="https://img.freepik.com/premium-photo/baby-ai-bot-with-ai-label-technology-house-ai-technology-modernism_1053378-11285.jpg?w=2000" class="baby-image {img_class}" width="400"></div>', unsafe_allow_html=True)

expression = "😊 Ready to help!" if st.session_state.ai_on else "😴 Sleeping..."
st.markdown(f"<h2 class='status-text' style='text-align: center;'>{expression}</h2>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([1,1,1,1])

with col1:
    if st.button("🎤 Mic " + ("ON" if st.session_state.mic_on else "OFF"), use_container_width=True):
        st.session_state.mic_on = not st.session_state.mic_on
        st.rerun()

with col2:
    if st.button("🤖 AI " + ("ON" if st.session_state.ai_on else "OFF"), use_container_width=True):
        st.session_state.ai_on = not st.session_state.ai_on
        st.rerun()

with col3:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.rag = RAGPipeline()
        st.rerun()

with col4:
    if st.button("📊 Stats", use_container_width=True):
        st.info(f"Documents: {len(st.session_state.rag.documents)}")

st.markdown(f"<p class='status-text' style='text-align: center;'><b>Status:</b> Mic {'🟢' if st.session_state.mic_on else '🔴'} | AI {'🟢' if st.session_state.ai_on else '🔴'}</p>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("📁 Upload documents to train", accept_multiple_files=True, type=['txt'])
if uploaded_files:
    docs = [file.read().decode("utf-8") for file in uploaded_files]
    st.session_state.rag.add_documents(docs)
    st.success(f"✅ Learned from {len(docs)} documents!")

query = st.text_input("💬 Ask me anything:", key="query_input")

if st.button("🔍 Ask Baby AI", use_container_width=True) and query:
    if st.session_state.ai_on:
        st.session_state.talking = True
        st.rerun()
        with st.spinner("🤔 Thinking..."):
            result = st.session_state.rag.query(query)
            st.markdown(f"<div style='background-color: rgba(255,255,255,0.9); padding: 20px; border-radius: 15px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.2);'><b style='font-size: 1.3em;'>🤖 Baby AI says:</b><br><p style='font-size: 1.1em; margin-top: 10px;'>{result}</p></div>", unsafe_allow_html=True)
        st.session_state.talking = False
    else:
        st.warning("⚠️ Turn ON the AI first!")

st.markdown('</div>', unsafe_allow_html=True)
