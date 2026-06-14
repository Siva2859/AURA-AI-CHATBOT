import PyPDF2
from PIL import Image
import re
import requests
from bs4 import BeautifulSoup

def extract_file_data(uploaded_file):
    """Processes uploaded files and returns formatted text or Image objects for Gemini."""
    if not uploaded_file:
        return None

    try:
        # Handle Images
        if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
            return {"type": "image", "data": Image.open(uploaded_file)}
        
        # Handle PDFs
        elif uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            pdf_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
            formatted_text = f"\n\n--- CONTENT FROM ATTACHED PDF ({uploaded_file.name}) ---\n{pdf_text}"
            return {"type": "text", "data": formatted_text}
        
        # Handle Text files
        elif uploaded_file.type == "text/plain":
            txt_text = uploaded_file.getvalue().decode("utf-8")
            formatted_text = f"\n\n--- CONTENT FROM ATTACHED TEXT FILE ({uploaded_file.name}) ---\n{txt_text}"
            return {"type": "text", "data": formatted_text}
            
    except Exception as e:
        return {"type": "error", "data": str(e)}
    
    return None

def extract_urls_and_scrape(text):
    """Finds URLs in text, scrapes the websites, and returns the content."""
    if not text:
        return ""
        
    urls = re.findall(r'(https?://[^\s]+)', text)
    scraped_content = ""
    
    for url in urls:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'} 
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = ' '.join(soup.stripped_strings)
            scraped_content += f"\n\n--- SCRAPED DATA FROM {url} ---\n{page_text[:5000]}"
        except Exception as e:
            scraped_content += f"\n\n--- FAILED TO READ {url} ---\nError: {e}"
            
    return scraped_content