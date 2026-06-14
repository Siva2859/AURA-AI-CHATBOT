import streamlit as st
import uuid
from datetime import datetime
import database as db
from ai_agent import generate_response
from utils import extract_file_data

# ----------------------------------------------------
# 1. UI SETUP & CUSTOM CSS
# ----------------------------------------------------
st.set_page_config(page_title="AURA | AI Assistant", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {background-color: #171717; border-right: 1px solid #333;}
    .welcome-container {display: flex; flex-direction: column; align-items: center; justify-content: center; height: 55vh; text-align: center; color: #ECECEC;}
    .welcome-text {font-size: 2.2rem; font-weight: 500; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

history = db.get_chat_history(st.session_state.session_id)

# ----------------------------------------------------
# 2. SIDEBAR WORKSPACE
# ----------------------------------------------------
with st.sidebar:
    if st.button("➕ New chat", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
        
    st.markdown("### 🕒 Recent Chats")
    recent_sessions = db.get_all_sessions()
    
    with st.container(height=250, border=False):
        if not recent_sessions:
            st.caption("No recent chats.")
        else:
            for s in recent_sessions[:15]: 
                is_active = (s["session_id"] == st.session_state.session_id)
                btn_type = "primary" if is_active else "secondary"
                
                if st.button(f"💬 {s['title']}", key=s["session_id"], use_container_width=True, type=btn_type):
                    st.session_state.session_id = s["session_id"]
                    st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Tools & Settings")
    app_mode = st.selectbox("Modes", ["💬 Standard Chat", "📄 Ask Documents", "🎨 Generate Image"], label_visibility="collapsed")
    
    with st.expander("🧠 AI Settings"):
        # NEW: Persona Selector
        persona = st.selectbox("AI Persona", ["Helpful Assistant", "Expert Programmer", "Creative Writer", "Harsh Code Reviewer", "Sarcastic Robot"])
        temp = st.slider("Temperature", 0.0, 1.0, 0.7)
        top_k = st.slider("Top-K", 1, 100, 40)
        
    with st.expander("📁 Text Knowledge (RAG)"):
        doc_name = st.text_input("File Name", placeholder="e.g., Q3 Report")
        new_doc = st.text_area("Paste Text Data", height=150)
        if st.button("Store Data", use_container_width=True) and new_doc and doc_name:
            db.add_document_to_rag(new_doc, doc_name)
            st.success(f"Stored: {doc_name}")

    st.markdown("---")
    if history:
        chat_text = "AURA Chat History Export\n=========================\n\n"
        for msg in history:
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M')
            chat_text += f"[{timestamp}] {msg.role.upper()}:\n{msg.content}\n\n"
            
        st.download_button(
            label="📥 Export Current Chat (.txt)",
            data=chat_text,
            file_name=f"aura_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        if st.button("🗑️ Delete Current Chat", use_container_width=True, type="secondary"):
            db.delete_session(st.session_state.session_id)
            st.session_state.session_id = str(uuid.uuid4()) 
            st.rerun() 

# ----------------------------------------------------
# 3. MAIN CANVAS 
# ----------------------------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)

if not history:
    st.markdown('<div class="welcome-container"><div class="welcome-text">What\'s on your mind today?</div></div>', unsafe_allow_html=True)
else:
    for msg in history:
        with st.chat_message(msg.role):
            st.markdown(msg.content)
            if msg.role == "model" and msg.mode_used == "Ask Documents":
                st.caption("🔍 *Sourced from Knowledge Base*")

# ----------------------------------------------------
# 4. BOTTOM INPUT AREA 
# ----------------------------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)

col1, col2 = st.columns([1.5, 5])

with col1:
    upload_choice = st.selectbox(
        "Attachment Options", 
        ["None", "Upload PDF", "Upload Image", "Upload File"], 
        label_visibility="collapsed"
    )

with col2:
    user_input = st.chat_input("Ask anything...")
    
uploaded_file = None
audio_bytes = None 

if upload_choice != "None":
    uploaded_file = st.file_uploader(
        f"Drag and drop to {upload_choice}", 
        label_visibility="collapsed"
    )
    if uploaded_file:
        st.success(f"Ready to send: {uploaded_file.name}")

# ----------------------------------------------------
# 5. PROCESS NEW INPUT
# ----------------------------------------------------
if user_input:
    display_text = user_input
    
    with st.chat_message("user"):
        st.write(display_text)
        if uploaded_file and uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
            st.image(uploaded_file, width=200, caption=uploaded_file.name)
        elif uploaded_file:
            st.info(f"Attached Document: {uploaded_file.name}")

    db_save_text = display_text + (f"\n*(Included file: {uploaded_file.name})*" if uploaded_file else "")
    db.save_chat_turn(st.session_state.session_id, "user", db_save_text, app_mode)

    with st.chat_message("model"):
        # We removed the st.spinner() here because streaming starts instantly!
        extracted_file = extract_file_data(uploaded_file)
        
        output, sources = generate_response(
            user_input=user_input, 
            app_mode=app_mode, 
            extracted_file=extracted_file, 
            audio_bytes=audio_bytes, 
            temp=temp, 
            top_k=top_k,
            history=history,
            persona=persona # <--- Persona passed to AI
        )
        
        # If output is a string (like from Image generation or an Error), render normally
        if isinstance(output, str):
            st.markdown(output)
            reply_text = output
        # If output is a generator (streaming text), use st.write_stream for the typing effect
        else:
            reply_text = st.write_stream(output)
        
        if sources:
            source_str = ", ".join(sources)
            st.info(f"📑 **Sources cited:** {source_str}")
            reply_text += f"\n\n*Sources: {source_str}*"
            
        db.save_chat_turn(st.session_state.session_id, "model", reply_text, app_mode)
        
        st.rerun()