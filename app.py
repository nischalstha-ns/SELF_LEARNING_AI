import streamlit as st
from rag_pipeline import RAGPipeline
from ai_assistant import VoiceVisionAI
import os
import cv2

st.set_page_config(page_title="Baby AI", page_icon="👶", layout="wide", initial_sidebar_state="collapsed")

if "rag" not in st.session_state:
    st.session_state.rag = RAGPipeline()
if "assistant" not in st.session_state:
    st.session_state.assistant = VoiceVisionAI()
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
        if os.path.exists("baby_ai_knowledge/learned.json"):
            os.remove("baby_ai_knowledge/learned.json")
        st.session_state.rag = RAGPipeline()
        st.rerun()

with col4:
    if st.button("📊 Stats", use_container_width=True):
        data = st.session_state.rag.data
        st.info(f"Conversations: {len(data['conversations'])} | Faces: {len(data['faces'])}")
        if len(data['faces']) > 0:
            st.write("**Known Faces:**")
            for face in data['faces'][-5:]:
                st.write(f"- {face['name']} ({face['timestamp'][:10]})")

st.markdown(f"<p class='status-text' style='text-align: center;'><b>Status:</b> Mic {'🟢' if st.session_state.mic_on else '🔴'} | AI {'🟢' if st.session_state.ai_on else '🔴'}</p>", unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    uploaded_files = st.file_uploader("📁 Upload documents", accept_multiple_files=True, type=['txt'])
    if uploaded_files:
        for file in uploaded_files:
            content = str(file.read(), encoding="utf-8", errors="ignore")
            st.session_state.rag.learn_conversation(f"Document: {file.name}", content)
        st.success(f"✅ Learned {len(uploaded_files)} documents!")

with col_b:
    face_tab1, face_tab2, face_tab3 = st.tabs(["📷 Camera", "🖼️ Upload", "🔍 Recognize"])
    
    with face_tab1:
        camera_image = st.camera_input("📸 Take a photo")
        if camera_image:
            face_name = st.text_input("Person's name:", key="camera_name")
            if st.button("Save from Camera") and face_name:
                faces = st.session_state.assistant.detect_faces(camera_image.read())
                if faces:
                    result = st.session_state.assistant.enroll_identity(faces[0]["embedding"], face_name, consent=True)
                    response = f"Nice to meet you {face_name}! I will remember your face."
                    st.success(f"✅ Enrolled: {result['person_id']}")
                    if st.session_state.mic_on:
                        st.session_state.assistant.tts_speak(response)
                else:
                    st.error("❌ No face detected")
    
    with face_tab2:
        face_image = st.file_uploader("👤 Upload face", type=['jpg', 'jpeg', 'png'])
        if face_image:
            face_name = st.text_input("Person's name:", key="upload_name")
            if st.button("Save from Upload") and face_name:
                face_id, msg = st.session_state.rag.detect_and_save_face(face_image.read(), face_name)
                if face_id:
                    st.success(f"✅ {msg} - Saved: {face_name}")
                else:
                    st.error(f"❌ {msg}")
    
    with face_tab3:
        recognize_image = st.camera_input("🔍 Recognize face")
        if recognize_image:
            if st.button("Recognize"):
                faces = st.session_state.assistant.detect_faces(recognize_image.read())
                if faces:
                    match = st.session_state.assistant.match_identity(faces[0]["embedding"])
                    if match:
                        result = f"Hello {match['display_name']}! Confidence: {match['confidence']:.1f}%"
                    else:
                        result = "Unknown person - not enrolled"
                else:
                    result = "No face detected"
                
                if st.session_state.mic_on:
                    st.session_state.assistant.tts_speak(result)
                st.info(f"🤖 {result}")

col_q1, col_q2 = st.columns([3, 1])

with col_q1:
    query = st.text_input("💬 Ask me anything:", key="query_input")

with col_q2:
    use_web = st.checkbox("🌐 Web Search", value=True)
    if st.button("🎤 Voice Input"):
        with st.spinner("Listening..."):
            voice_query = st.session_state.assistant.asr_listen()
            if voice_query:
                st.session_state.voice_query = voice_query
                st.rerun()

if "voice_query" in st.session_state:
    query = st.session_state.voice_query
    del st.session_state.voice_query

if st.button("🔍 Ask Baby AI", use_container_width=True) and query:
    if st.session_state.ai_on:
        with st.spinner("🤔 Searching and thinking..."):
            if use_web:
                result, sources = st.session_state.assistant.process_query(query, use_web=True)
            else:
                result = st.session_state.rag.query(query)
                sources = []
            
            if st.session_state.mic_on:
                st.session_state.assistant.tts_speak(result)
            
            st.markdown(f"<div style='background-color: rgba(255,255,255,0.9); padding: 20px; border-radius: 15px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.2);'><b style='font-size: 1.3em;'>🤖 Baby AI says:</b><br><p style='font-size: 1.1em; margin-top: 10px;'>{result}</p></div>", unsafe_allow_html=True)
            
            if sources:
                st.markdown("**Sources:**")
                for src in sources[:3]:
                    st.markdown(f"- {src}")
    else:
        st.warning("⚠️ Turn ON the AI first!")

col_hist1, col_hist2 = st.columns(2)

with col_hist1:
    if len(st.session_state.rag.data["conversations"]) > 0:
        with st.expander("📜 Conversation History"):
            for conv in st.session_state.rag.data["conversations"][-5:]:
                st.markdown(f"**You:** {conv['user']}")
                st.markdown(f"**AI:** {conv['ai']}")
                st.markdown("---")

with col_hist2:
    if len(st.session_state.rag.data["faces"]) > 0:
        with st.expander("👥 Saved Faces"):
            for face in st.session_state.rag.data["faces"][-5:]:
                st.markdown(f"**{face['name']}** - {face['timestamp'][:19]}")
                if os.path.exists(face['path']):
                    st.image(face['path'], width=100)

st.markdown('</div>', unsafe_allow_html=True)
