import streamlit as st
import uuid
from datetime import datetime
import database as db
from ai_agent import generate_response
from utils import extract_file_data

# ----------------------------------------------------
# 1. UI SETUP & ADVANCED PREMIUM THEMING (CSS)
# ----------------------------------------------------
st.set_page_config(page_title="AURA | Premium AI Workstation", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# Inject premium custom CSS for ultra-clean layouts, WhatsApp bubbles, and custom inputs
st.markdown("""
    <style>
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {background-color: #0F172A; border-right: 1px solid #1E293B;}
    
    /* Center welcome screen styling */
    .welcome-container {display: flex; flex-direction: column; align-items: center; justify-content: center; height: 35vh; text-align: center; color: #94A3B8;}
    .welcome-title {font-size: 2.8rem; font-weight: 800; color: #00D2FF; margin-bottom: 10px; letter-spacing: -0.5px;}
    .welcome-subtitle {font-size: 1.1rem; color: #64748B;}
    
    /* WhatsApp-style Professional Chat Bubbles */
    .chat-bubble-user {
        background-color: #1E293B; 
        color: #F8FAFC; 
        padding: 14px 18px; 
        border-radius: 18px 18px 2px 18px; 
        margin-bottom: 12px; 
        max-width: 75%; 
        float: right;
        clear: both;
        border: 1px solid #334155;
    }
    .chat-bubble-model {
        background-color: #0284C7; 
        color: #FFFFFF; 
        padding: 14px 18px; 
        border-radius: 18px 18px 18px 2px; 
        margin-bottom: 12px; 
        max-width: 75%; 
        float: left;
        clear: both;
    }
    .chat-container {
        width: 100%;
        overflow: auto;
    }
    
    /* Tighten gap between multi-line input tools */
    div[data-testid="stForm"] {
        border: 1px solid #334155 !important;
        background-color: #1E293B !important;
        border-radius: 16px !important;
        padding: 10px !important;
    }
    
    /* Custom spacing for question management row */
    .edit-hint {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: -8px;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session Triggers
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = ""

history = db.get_chat_history(st.session_state.session_id)

# ----------------------------------------------------
# 2. SIDEBAR: CHAT INTERACTION & MANAGEMENT HUB
# ----------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00D2FF; margin-bottom: 20px;'>✨ AURA WORKSPACE</h2>", unsafe_allow_html=True)
    
    if st.button("➕ Open New Conversation", use_container_width=True, type="primary"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.input_buffer = ""
        st.rerun()
        
    st.markdown("### 🕒 Recent Chats")
    recent_sessions = db.get_all_sessions()
    
    with st.container(height=280, border=False):
        if not recent_sessions:
            st.caption("No recent chat entries recorded.")
        else:
            for idx, s in enumerate(recent_sessions[:12]): 
                is_active = (s["session_id"] == st.session_state.session_id)
                
                # Expandable item layout for separate quick actions (Share, Download, Delete)
                with st.expander(f"{'🔷 ' if is_active else '💬 '} {s['title']}", expanded=is_active):
                    # Switch to this session
                    if not is_active:
                        if st.button("👁️ View Chat", key=f"view_{s['session_id']}_{idx}", use_container_width=True):
                            st.session_state.session_id = s["session_id"]
                            st.session_state.input_buffer = ""
                            st.rerun()
                    
                    # Action Buttons inside the specific active item
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
    st.markdown("### ⚙️ Engine Configurations")
    app_mode = st.selectbox("Operation Matrix", ["💬 Standard Chat", "📄 Ask Documents", "🎨 Generate Image"])
    
    with st.expander("🧠 Generation Hyperparameters"):
        persona = st.selectbox("AI Agent Persona", ["Helpful Assistant", "Expert Programmer", "Creative Writer", "Harsh Code Reviewer", "Sarcastic Robot"])
        temp = st.slider("Temperature (Creativity)", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
        top_k = st.slider("Top-K (Vocabulary Filter)", min_value=1, max_value=100, value=40, step=1)

# ----------------------------------------------------
# 3. MAIN INTERACTION CANVAS (WHATSAPP LAYOUT)
# ----------------------------------------------------
if not history:
    st.markdown("""
        <div class="welcome-container">
            <div class="welcome-title">AURA Intelligence Platform</div>
            <div class="welcome-subtitle">Your customizable multi-modal agent workspace. Type your prompt below to initialize.</div>
        </div>
    """, unsafe_allow_html=True)
else:
    # Render messages inside structured containers to allow clear edit injection options
    for index, msg in enumerate(history):
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        if msg.role == "user":
            st.markdown(f'<div class="chat-bubble-user">{msg.content}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Question editing line below the user prompt
            if st.button(f"✏️ Edit this Question", key=f"edit_trigger_{index}"):
                # Clean up metadata prefixes if present from previous attachments
                clean_prompt = msg.content.split("\n\n*(Attached Asset:")[0]
                st.session_state.input_buffer = clean_prompt
                st.toast("✏️ Question pulled back down into the input area for editing!")
                st.rerun()
        else:
            st.markdown(f'<div class="chat-bubble-model">{msg.content}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if msg.mode_used == "Ask Documents":
                st.caption("🔍 *Grounded from Chroma Vector Storage Data Matrix*")

st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. CUSTOM AUTO-EXPANDING BAR WITH '+' POPOVER
# ----------------------------------------------------
# Using a Streamlit Form to tightly control execution layout elements
with st.form(key="input_form", clear_on_submit=True):
    col_plus, col_text, col_sub = st.columns([1, 7, 1.5])
    
    with col_plus:
        # The exact requested '+' action layout popover menu
        plus_menu = st.popover("➕", use_container_width=True)
        with plus_menu:
            st.markdown("##### 📎 Attachment Hub")
            upload_choice = st.radio("Asset Type", ["Text Query Only", "Upload Image (PNG/JPG)", "Upload PDF Document"])
            uploaded_file = st.file_uploader("Choose validation asset file:", label_visibility="collapsed")
            
    with col_text:
        # Custom input area that handles multiline inputs seamlessly and grows based on contents
        user_query = st.text_area(
            "Enter Prompt Here",
            value=st.session_state.input_buffer,
            height=65,
            placeholder="Ask anything or modify your question context...",
            label_visibility="collapsed"
        )
        
    with col_sub:
        submit_action = st.form_submit_button("Send 🚀", use_container_width=True)

# ----------------------------------------------------
# 5. PIPELINE INFERENCE EXECUTION
# ----------------------------------------------------
if submit_action and user_query:
    # Clear out the scratchpad buffer state
    st.session_state.input_buffer = ""
    
    # Save the input turn to the database log
    save_text_representation = user_query + (f"\n\n*(Attached Asset: {uploaded_file.name})*" if (upload_choice != "Text Query Only" and uploaded_file) else "")
    db.save_chat_turn(st.session_state.session_id, "user", save_text_representation, app_mode)

    # Process and display the dynamic response stream
    with st.chat_message("model"):
        extracted_file = extract_file_data(uploaded_file) if (upload_choice != "Text Query Only") else None
        
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
            st.markdown(output)
            final_reply = output
        else:
            final_reply = st.write_stream(output)
        
        if sources:
            source_string = ", ".join(sources)
            final_reply += f"\n\n*Sources: {source_string}*"
            
        db.save_chat_turn(st.session_state.session_id, "model", final_reply, app_mode)
        st.rerun()
