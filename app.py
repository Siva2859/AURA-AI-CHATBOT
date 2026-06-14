import streamlit as st
import uuid
from datetime import datetime
import database as db
from ai_agent import generate_response
from utils import extract_file_data

# ----------------------------------------------------
# 1. UI SETUP & PROFESSIONAL THEMING (CSS)
# ----------------------------------------------------
st.set_page_config(page_title="AURA | AI Workstation", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# Custom CSS to fix input tracking, bubble sizes, and professional alignment
st.markdown("""
    <style>
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {background-color: #1E293B; border-right: 1px solid #334155;}
    
    /* Center welcome screen styling */
    .welcome-container {display: flex; flex-direction: column; align-items: center; justify-content: center; height: 40vh; text-align: center; color: #94A3B8;}
    .welcome-title {font-size: 2.5rem; font-weight: 700; color: #00D2FF; margin-bottom: 10px;}
    .welcome-subtitle {font-size: 1.1rem; color: #94A3B8;}
    
    /* Make chat inputs and options clean and linearly aligned */
    div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    
    /* Ensure markdown and text blocks match a consistent font layout */
    .stChatMessage {
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
        max-width: 85%;
    }
    </style>
""", unsafe_allow_html=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

history = db.get_chat_history(st.session_state.session_id)

# ----------------------------------------------------
# 2. SIDEBAR WORKSPACE & SETTINGS
# ----------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00D2FF;'>✨ AURA AI</h2>", unsafe_allow_html=True)
    
    if st.button("➕ New Workspace Session", use_container_width=True, type="primary"):
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
        
    st.markdown("### 🕒 Recent Sessions")
    recent_sessions = db.get_all_sessions()
    
    with st.container(height=200, border=False):
        if not recent_sessions:
            st.caption("No active histories recorded.")
        else:
            for s in recent_sessions[:10]: 
                is_active = (s["session_id"] == st.session_state.session_id)
                btn_type = "primary" if is_active else "secondary"
                
                if st.button(f"💬 {s['title']}", key=s["session_id"], use_container_width=True, type=btn_type):
                    st.session_state.session_id = s["session_id"]
                    st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ System Configuration")
    app_mode = st.selectbox("Operation Mode", ["💬 Standard Chat", "📄 Ask Documents", "🎨 Generate Image"])
    
    with st.expander("🧠 Generation Hyperparameters"):
        persona = st.selectbox("AI Agent Persona", ["Helpful Assistant", "Expert Programmer", "Creative Writer", "Harsh Code Reviewer", "Sarcastic Robot"])
        temp = st.slider("Temperature (Creativity)", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
        top_k = st.slider("Top-K (Vocabulary Filter)", min_value=1, max_value=100, value=40, step=1)
        
    with st.expander("📁 RAG Knowledge Base"):
        doc_name = st.text_input("Document Label", placeholder="e.g., Technical Specification")
        new_doc = st.text_area("Source Text Data", height=120)
        if st.button("Index into Database", use_container_width=True) and new_doc and doc_name:
            db.add_document_to_rag(new_doc, doc_name)
            st.success(f"Successfully Indexed: {doc_name}")

    st.markdown("---")
    
    # SHARE AND MANAGEMENT UTILITIES
    if history:
        # Construct shareable history text
        shareable_text = f"--- AURA AI SYSTEM CHAT LOG ({st.session_state.session_id}) ---\n\n"
        for msg in history:
            shareable_text += f"[{msg.role.upper()}]: {msg.content}\n\n"
            
        st.download_button(
            label="🔗 Share & Export Chat Log",
            data=shareable_text,
            file_name=f"aura_shareable_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
        
        if st.button("🗑️ Purge Current Session", use_container_width=True, type="secondary"):
            db.delete_session(st.session_state.session_id)
            st.session_state.session_id = str(uuid.uuid4()) 
            st.rerun() 

# ----------------------------------------------------
# 3. MAIN CONVERSATIONAL CANVAS
# ----------------------------------------------------
if not history:
    st.markdown("""
        <div class="welcome-container">
            <div class="welcome-title">AURA Intelligence System</div>
            <div class="welcome-subtitle">Select a mode from the sidebar configurations to begin multi-modal generation.</div>
        </div>
    """, unsafe_allow_html=True)
else:
    for msg in history:
        with st.chat_message(msg.role):
            st.markdown(msg.content)
            if msg.role == "model" and msg.mode_used == "Ask Documents":
                st.caption("🔍 *Context grounded from RAG Matrix Database*")

# ----------------------------------------------------
# 4. BALANCED BOTTOM INPUT PLATFORM
# ----------------------------------------------------
st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)

# Align options and entry boxes into a clean layout block
input_col, select_col = st.columns([4.5, 1.5])

with select_col:
    upload_choice = st.selectbox(
        "Upload Engine", 
        ["No Attachment", "Upload Image", "Upload PDF Document"],
        label_visibility="collapsed"
    )

with input_col:
    user_input = st.chat_input("Enter your prompt or context criteria here...")

# Attachment processing
uploaded_file = None
if upload_choice != "No Attachment":
    uploaded_file = st.file_uploader("Attach verification criteria file:", label_visibility="collapsed")
    if uploaded_file:
        st.toast(f"📎 Attached file successfully: {uploaded_file.name}")

# ----------------------------------------------------
# 5. PIPELINE INFERENCE PROCESSING
# ----------------------------------------------------
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
        if uploaded_file and uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
            st.image(uploaded_file, width=250)
        elif uploaded_file:
            st.caption(f"📁 Linked Asset: {uploaded_file.name}")

    save_text_representation = user_input + (f"\n\n*(Attached Asset: {uploaded_file.name})*" if uploaded_file else "")
    db.save_chat_turn(st.session_state.session_id, "user", save_text_representation, app_mode)

    with st.chat_message("model"):
        extracted_file = extract_file_data(uploaded_file)
        
        output, sources = generate_response(
            user_input=user_input, 
            app_mode=app_mode, 
            extracted_file=extracted_file, 
            audio_bytes=None, 
            temp=temp, 
            top_k=top_k,
            history=history,
            persona=persona
        )
        
        if isinstance(output, str):
            st.markdown(output)
            final_reply = output
        else:
            final_reply = st.write_stream(output)
        
        if sources:
            source_string = ", ".join(sources)
            st.info(f"📑 Citing Sources: {source_string}")
            final_reply += f"\n\n*Sources: {source_string}*"
            
        db.save_chat_turn(st.session_state.session_id, "model", final_reply, app_mode)
        st.rerun()
