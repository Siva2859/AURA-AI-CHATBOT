import os
import requests
import base64
import urllib.parse
import streamlit as st
from datetime import datetime
from google import genai
from google.genai import types
from database import query_rag_knowledge
from utils import extract_urls_and_scrape

@st.cache_resource
def get_ai_client():
    api_key = os.environ.get("GEMINI_API_KEY", st.secrets.get("GEMINI_API_KEY"))
    return genai.Client(api_key=api_key if api_key else "MOCK_KEY")

client = get_ai_client()

def generate_response(user_input, app_mode, extracted_file, audio_bytes, temp, top_k, history=None, persona="Helpful Assistant"):
    
    if "Standard" in app_mode:
        payload = []
        
        # --- THE CONTEXT WINDOW ---
        if history:
            context_string = "--- PREVIOUS CONVERSATION CONTEXT ---\n"
            for msg in history:
                if "![Generated Image]" not in msg.content:
                    context_string += f"{msg.role.upper()}: {msg.content}\n"
            context_string += "-------------------------------------\n\n"
            payload.append(context_string)
            
        payload.append(f"CURRENT USER MESSAGE: {user_input if user_input else 'Analyze the provided input.'}")
        
        if extracted_file:
            if extracted_file["type"] == "image":
                payload.append(extracted_file["data"])
            elif extracted_file["type"] == "text":
                payload[0] += extracted_file["data"]
                
        if audio_bytes:
            payload.append({"mime_type": "audio/wav", "data": audio_bytes})

        if user_input:
            scraped_text = extract_urls_and_scrape(user_input)
            if scraped_text:
                payload[0] += scraped_text
                
        current_time = datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")
        
        # Inject the Persona here!
        sys_prompt = f"You are a {persona}. The current date and time is {current_time}. Analyze any provided files, links, or voice messages carefully and respond in character."
        
        config = types.GenerateContentConfig(
            temperature=temp, 
            top_k=top_k, 
            system_instruction=sys_prompt,
            tools=[{"google_search": {}}] 
        )
        
        try:
            # Use STREAMING for a faster, ChatGPT-like feel
            response_stream = client.models.generate_content_stream(model='gemini-2.5-flash', contents=payload, config=config)
            
            # Create a generator to yield text word-by-word to Streamlit
            def generate_chunks():
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                        
            return generate_chunks(), []
        except Exception as e:
            return f"⚠️ **Error communicating with Gemini API:** {e}", []

    elif "Documents" in app_mode:
        context, sources = query_rag_knowledge(user_input)
        if not context:
            return "I couldn't find any relevant information in your uploaded documents. Please try rephrasing.", []
            
        sys_prompt = f"You are an expert data analyst and {persona}. Answer using ONLY the provided context.\n\n[CONTEXT]:\n{context}"
        config = types.GenerateContentConfig(temperature=0.2, system_instruction=sys_prompt)
        
        try:
            response_stream = client.models.generate_content_stream(model='gemini-2.5-flash', contents=user_input, config=config)
            def generate_chunks():
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
            return generate_chunks(), sources
        except Exception as e:
            return f"⚠️ **Error communicating with Gemini API:** {e}", []

    elif "Image" in app_mode:
        try:
            hf_api_key = os.environ.get("HF_API_KEY", st.secrets.get("HF_API_KEY"))
        except:
            hf_api_key = None
            
        if not hf_api_key:
            return "⚠️ **Error:** Missing Hugging Face API Key.", []
            
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {hf_api_key}"}
        payload = {"inputs": user_input}
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        except Exception as e:
            return f"⚠️ **Network/API Error:** {str(e)}", []
        
        if response.status_code == 200:
            encoded_img = base64.b64encode(response.content).decode("utf-8")
            reply_text = f"🎨 **Generated Image for:** *{user_input}*\n\n![Generated Image](data:image/jpeg;base64,{encoded_img})"
            return reply_text, [] # Images don't stream, they return as a standard string
        else:
            return f"⚠️ **API Error ({response.status_code}):** Model is loading. Try again in 30 seconds.", []