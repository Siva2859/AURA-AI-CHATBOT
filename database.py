import streamlit as st
import chromadb
import uuid
import re
from sqlmodel import create_engine, Session, select
from models import ChatHistory

@st.cache_resource
def initialize_databases():
    engine = create_engine("sqlite:///advanced_bot_memory.db", connect_args={"check_same_thread": False})
    from models import ChatHistory 
    ChatHistory.metadata.create_all(engine)

    chroma_client = chromadb.PersistentClient(path="./chroma_rag_storage")
    collection = chroma_client.get_or_create_collection(name="user_knowledge_base")
    
    return engine, collection

engine, collection = initialize_databases()

def save_chat_turn(session_id: str, role: str, content: str, mode: str = "Standard"):
    with Session(engine) as session:
        turn = ChatHistory(session_id=session_id, role=role, content=content, mode_used=mode)
        session.add(turn)
        session.commit()

def get_chat_history(session_id: str, limit: int = 10):
    with Session(engine) as session:
        statement = select(ChatHistory).where(ChatHistory.session_id == session_id).order_by(ChatHistory.timestamp.desc()).limit(limit)
        results = session.exec(statement).all()
        return list(reversed(results))

def get_all_sessions():
    """Fetches unique sessions and uses the first user message as a clean chat title."""
    with Session(engine) as session:
        statement = select(ChatHistory.session_id).distinct()
        session_ids = session.exec(statement).all()

        sessions_info = []
        for s_id in session_ids:
            first_msg_stmt = select(ChatHistory).where(ChatHistory.session_id == s_id).order_by(ChatHistory.timestamp.asc()).limit(1)
            first_msg = session.exec(first_msg_stmt).first()

            if first_msg:
                # Clean title: Remove the hidden file attachment text
                raw_title = first_msg.content.replace("\n", " ")
                clean_title = re.sub(r'\*\(Included file:.*?\)\*', '', raw_title).strip()
                
                if not clean_title:
                    clean_title = "Attachment/File Upload"
                    
                title = clean_title[:25] + "..." if len(clean_title) > 25 else clean_title
                
                sessions_info.append({"session_id": s_id, "title": title, "timestamp": first_msg.timestamp})

        sessions_info.sort(key=lambda x: x["timestamp"], reverse=True)
        return sessions_info

def delete_session(session_id: str):
    with Session(engine) as session:
        statement = select(ChatHistory).where(ChatHistory.session_id == session_id)
        results = session.exec(statement).all()
        for res in results:
            session.delete(res)
        session.commit()

def add_document_to_rag(text: str, doc_name: str):
    doc_id = str(uuid.uuid4())
    collection.add(documents=[text], metadatas=[{"source": doc_name}], ids=[doc_id])

def query_rag_knowledge(query_text: str):
    results = collection.query(query_texts=[query_text], n_results=2)
    if results and results['documents'] and results['documents'][0]:
        context = "\n---\n".join(results['documents'][0])
        sources = [meta.get("source", "Unknown Document") for meta in results['metadatas'][0]] if results['metadatas'] else []
        return context, list(set(sources))
    return "", []