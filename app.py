import streamlit as st
import uuid
from datetime import datetime
import database as db
from ai_agent import generate_response
from utils import extract_file_data

# ----------------------------------------------------
# 1. PREMIUM WINDOW & INTERFACE THEMING (CSS)
# ----------------------------------------------------
st.set_page_config(page_title="AURA | Intelligence Station", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# Ultra-modern minimalist styling matching premium AI platforms
st.markdown("""
    <style>
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Clean Dark Dashboard Background */
    .stApp {background-color: #0B0F19;}
    [data-testid="stSidebar"] {background-color: #0F172A; border-right: 1px solid #1E293B;}
    
    /* Center welcome screen styling */
    .welcome-container {display: flex; flex-direction: column; align-items: center; justify-content: center; height: 35vh; text-align: center; padding: 20px;}
    .welcome-title {font-size: 3rem; font-weight: 800; background: linear-gradient(45deg, #00D2FF, #10B981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px;}
    .welcome-subtitle {font-size: 1.1rem; color: #64748B; max-width: 500px;}
    
    /* WhatsApp/ChatGPT Minimalist Message Layouts */
    .chat-bubble-user {
        background-color: #1E293B; 
        color: #F8FAFC; 
        padding: 14px 20px; 
        border-radius: 20px 20px 4px 20px; 
        margin-bottom: 8px; 
        max-width: 75%; 
        float: right;
        clear: both;
        border: 1px solid #334155;
        font-size: 1rem;
    }
    
    /* Edit Button Styling (Right-aligned under user bubble) */
    .edit-btn-container {
        float: right;
        clear: both;
        margin-bottom: 24px;
        margin-top: -4px;
        margin-right: 10px;
    }
    
    /* AI Model Bubble - Transparent with Green Avatar Accent */
    .chat-bubble-model {
        background-color: transparent; 
        color: #E2E8F0; 
        padding: 14px 0px; 
        margin-bottom: 24px; 
        max-width: 90%; 
        float: left;
        clear: both;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    
    /* Green AI Avatar Customization */
    .ai-avatar {
        color: #10B981; /* Premium Emerald Green */
        font-weight: 800;
        margin-right: 8px;
        font-size: 1.2rem;
    }
    
    .chat-container {width: 100%; overflow: auto;}
    
    /* Custom Code Styling */
    code {background-color: #1E293B !important; color: #00D2FF !important; padding: 3px 6px !important; border-radius: 4px !important; font-family: monospace;}
    
    /* Pinned Bottom Input Container Style */
    div[data-testid="stForm"] {
        border: 1px solid #334155 !important;
        background-color: #151F32 !important;
        border-radius: 24px !important;
        padding: 8px 16px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# Session Synchronization Checks
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = ""

history = db.get_chat_history(st.session_state.session_id)

# ----------------------------------------------------
# 2. SIDEBAR WORKSPACE MANAGER
# ----------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00D2FF; font-weight:800; letter-spacing:-1px;'>AURA SYSTEM</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B; font-size:0.85rem; margin-top:-15px;'>v2.5 Premium Production Ready</p>", unsafe_allow_html=True)
    
    if st.button("➕ Open New Conversation", use_container_width=True, type="primary"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.input_buffer = ""
        st.rerun()
        
    st.markdown("---")
    st.markdown("#### 🕒 Recent Workspace Timelines")
    recent_sessions = db.get_all_sessions()
    
    with st.container(height=300, border=False):
        if not recent_sessions:
            st.caption("No historical workspaces indexed.")
        else:
            for idx, s in enumerate(recent_sessions[:15]): 
                is_active = (s["session_id"] == st.session_state.session_id)
                
                with st.expander(f"{'🟢 ' if is_active else '📄 '} {s['title']}", expanded=is_active):
                    if not is_active:
                        if st.button("👁️ Access Thread", key=f"view_{s['session_id']}_{idx}", use_container_width=True):
                            st.session_state.session_id = s["session_id"]
                            st.session_state.input_buffer = ""
                            st.rerun()
                    
                    action_history = db.get_chat_history(s["session_id"])
                    share_text = f"--- AURA DATA CHAT STREAM: {s['title']} ---\n\n"
                    for m in action_history:
                        share_text += f"[{m.role.upper()}]: {m.content}\n\n"
                    
                    col_sh, col_dl, col_del = st.columns(3)
                    with col_sh:
                        st.download_button("🔗 Share", data=share_text, file_name=f"aura_share_{s['session_id']}.txt", mime="text/plain", key=f"sh_{s['session_id']}_{idx}")
                    with col_dl:
                        st.download_button("📥 Save", data=share_text, file_name=f"aura_download_{s['session_id']}.txt", mime="text/plain", key=f"dl_{s['session_id']}_{idx}")
                    with col_del:
                        if st.button("🗑️ Clear", key=f"del_{s['session_id']}_{idx}", use_container_width=True):
                            db.delete_session(s["session_id"])
                            if s["session_id"] == st.session_state.session_id:
                                st.session_state.session_id = str(uuid.uuid4())
                            st.rerun()

    st.markdown("---")
    st.markdown("#### ⚙️ Orchestration Core")
    app_mode = st.selectbox("Operational Framework Mode", ["💬 Standard Chat", "📄 Ask Documents", "🎨 Generate Image"], label_visibility="collapsed")
    
    # PREMIUM HYPERPARAMETER RENAMING
    with st.expander("🧠 Advanced Model Control"):
        persona = st.selectbox("AI Expert Profile", ["Helpful Assistant", "Expert Programmer", "Creative Writer", "Harsh Code Reviewer", "Sarcastic Robot"])
        temp = st.slider("💡 Creativity Balance (Temperature)", min_value=0.0, max_value=1.0, value=0.7, step=0.1, help="Low = Analytical & Precise. High = Creative & Varied.")
        top_k = st.slider("🎯 Vocabulary Focus (Top-K)", min_value=1, max_value=100, value=40, step=1, help="Limits the AI to only choose from the top X most likely words.")

# ----------------------------------------------------
# 3. CONVERSATIONAL STREAM CANVAS
# ----------------------------------------------------
if not history:
    st.markdown("""
        <div class="welcome-container">
            <div class="welcome-title">How can I assist your workflow today?</div>
            <div class="welcome-subtitle">Seamlessly switch operational configuration modes in the active sidebar to parse files or stream generative answers.</div>
        </div>
    """, unsafe_allow_html=True)
else:
    for index, msg in enumerate(history):
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        if msg.role == "user":
            # User Bubble
            st.markdown(f'<div class="chat-bubble-user">{msg.content}</div>', unsafe_allow_html=True)
            
            # Repositioned Minimal Edit Feature (Right aligned under bubble)
            st.markdown('<div class="edit-btn-container">', unsafe_allow_html=True)
            if st.button(f"✏️ Revise Prompt", key=f"edit_trigger_{index}", type="secondary", help="Pull this text down into the input box to edit and resubmit."):
                clean_prompt = msg.content.split("\n\n*(Attached Asset:")[0]
                st.session_state.input_buffer = clean_prompt
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True) # Close main container
        else:
            # AI Bubble with Green Styling applied to the Avatar Text
            st.markdown(f'<div class="chat-bubble-model"><span class="ai-avatar">✨ AURA:</span><br>{msg.content}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if msg.mode_used == "Ask Documents":
                st.caption("🔍 *Grounded directly via RAG Matrix Vector Subsystem*")

# Spacer to ensure the input bar doesn't overlap the last message
st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. FIXED ACTION FOOTER FORM (Floating Bar)
# ----------------------------------------------------
with st.form(key="input_form", clear_on_submit=True):
    col_plus, col_text, col_sub = st.columns([0.8, 7.4, 1.3])
    
    with col_plus:
        # The ➕ popover for hidden attachments
        plus_menu = st.popover("➕", use_container_width=True)
        with plus_menu:
            st.markdown("<p style='font-size:0.85rem; font-weight:bold; margin-bottom:2px;'>Asset Pipeline Attachments</p>", unsafe_allow_html=True)
            upload_choice = st.radio("Pipeline Mode", ["Text Prompt Only", "Upload Multi-Modal Image", "Parse Structure PDF Document"], label_visibility="collapsed")
            uploaded_file = st.file_uploader("Upload Target File", label_visibility="collapsed")
            
    with col_text:
        # Expanding Text Area linked to the Session Buffer
        user_query = st.text_area(
            "Prompt Input Box",
            value=st.session_state.input_buffer,
            height=50,
            placeholder="Type your message, query parameters, or instructions...",
            label_visibility="collapsed"
        )
        
    with col_sub:
        submit_action = st.form_submit_button("Send ✨", use_container_width=True)

# ----------------------------------------------------
# 5. EXECUTION MATRIX PIPELINE
# ----------------------------------------------------
if submit_action and user_query:
    st.session_state.input_buffer = "" # Clear editing buffer
    
    save_text_representation = user_query + (f"\n\n*(Attached Asset: {uploaded_file.name})*" if (upload_choice != "Text Prompt Only" and uploaded_file) else "")
    db.save_chat_turn(st.session_state.session_id, "user", save_text_representation, app_mode)

    with st.chat_message("model"):
        extracted_file = extract_file_data(uploaded_file) if (upload_choice != "Text Prompt Only") else None
        
        output, sources = generate_response(
            user_input=user_query, 
            app_mode=app_mode, 
            extracted_file=extracted_file, 
            audio_bytes=None, 
            temp=temp, 
            top_k=top_k,
            history=history,
            persona=persona
        )
        
        if isinstance(output, str):
            st.markdown(f'<div class="chat-bubble-model"><span class="ai-avatar">✨ AURA:</span><br>{output}</div>', unsafe_allow_html=True)
            final_reply = output
        else:
            st.markdown('<span class="ai-avatar">✨ AURA:</span>', unsafe_allow_html=True)
            final_reply = st.write_stream(output)
        
        if sources:
            source_string = ", ".join(sources)
            final_reply += f"\n\n*Sources: {source_string}*"
            
        db.save_chat_turn(st.session_state.session_id, "model", final_reply, app_mode)
        st.rerun()