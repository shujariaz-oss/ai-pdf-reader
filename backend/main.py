import os
import io
import base64
import uuid
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from PIL import Image
from pdf2image import convert_from_bytes

try:
    import pytesseract
except ImportError:
    pytesseract = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# FAIL-SAFE IN-MEMORY CACHE
DOCUMENT_CACHE = {}

def safe_get_db_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception:
        return None

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    print(f"\n[UPLOAD] File Received: {file.filename}")
    file_bytes = await file.read()
    
    try:
        images = convert_from_bytes(file_bytes)
        print(f"[UPLOAD] PDF broken down into {len(images)} pages.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF pages: {str(e)}")
    
    full_text = ""
    
    for i, img in enumerate(images):
        full_text += f"\n--- PAGE {i+1} ---\n"
        
        if GEMINI_API_KEY:
            page_extracted = False
            # Updated 2026 Active Production Model List
            for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
                try:
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG')
                    base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": "Transcribe all text from this page accurately."},
                                {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}
                            ]
                        }]
                    }
                    response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=30)
                    if response.status_code == 200:
                        full_text += response.json()['candidates'][0]['content']['parts'][0]['text'] + "\n"
                        page_extracted = True
                        break
                except Exception:
                    continue
            
            if not page_extracted:
                full_text += fallback_tesseract(img)
        else:
            full_text += fallback_tesseract(img)
            
    generated_id = str(uuid.uuid4())[:8]
    DOCUMENT_CACHE[generated_id] = full_text
    print(f"[CACHE] Stored document under memory key: {generated_id}")
    
    conn = safe_get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO documents (file_name, source_text) VALUES (%s, %s) RETURNING id;", (file.filename, full_text))
            db_id = str(cur.fetchone()[0])
            conn.commit()
            cur.close()
            conn.close()
            DOCUMENT_CACHE[str(db_id)] = full_text
            generated_id = str(db_id)
        except Exception:
            pass

    return {
        "docId": str(generated_id), "doc_id": str(generated_id),
        "documentId": str(generated_id), "document_id": str(generated_id), "id": str(generated_id),
        "sourceText": full_text, "source_text": full_text,
        "extractedText": full_text, "extracted_text": full_text, "text": full_text
    }

def fallback_tesseract(img):
    if not pytesseract:
        return "[OCR Engine Offline]"
    try:
        if os.path.exists('/usr/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        return pytesseract.image_to_string(img)
    except Exception:
        return "[OCR Extraction Failed]"

@app.post("/api/translate")
async def translate_text(request: Request):
    print("\n[TRANSLATE] Inbound request intercepted.")
    try:
        body = await request.json()
    except Exception:
        body = {}

    target_lang = body.get("target_lang") or body.get("targetLang") or "English"
    source_text = body.get("source_text") or body.get("sourceText") or body.get("text") or body.get("extracted_text") or body.get("extractedText") or ""
    target_id = body.get("doc_id") or body.get("docId") or body.get("document_id") or body.get("documentId") or body.get("id")

    if not source_text and target_id:
        target_id_str = str(target_id)
        if target_id_str in DOCUMENT_CACHE:
            source_text = DOCUMENT_CACHE[target_id_str]
            print(f"[CACHE HIT] Found text for ID '{target_id_str}' in memory pool.")

    if not source_text and target_id:
        conn = safe_get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT source_text FROM documents WHERE id = %s;", (str(target_id),))
                row = cur.fetchone()
                if row:
                    source_text = row[0]
                cur.close()
                conn.close()
            except Exception:
                pass

    if not source_text:
        return {
            "translatedText": "[System Error: No source text found to translate. Try re-uploading the file.]",
            "translated_text": "[System Error: No source text found to translate. Try re-uploading the file.]",
            "text": "[Extraction Empty]"
        }

    if not GEMINI_API_KEY:
        return {
            "translatedText": "[Error: GEMINI_API_KEY environment variable is entirely missing from Render settings]",
            "translated_text": "[Error: GEMINI_API_KEY environment variable is entirely missing from Render settings]",
            "text": "[Missing API Key]"
        }

    translated_text = None
    api_errors = []

    # Updated 2026 Production Loop Core
    for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            prompt = f"Translate the following text directly into {target_lang}. Preserve layout styling. Do not add chat preamble.\n\nText:\n{source_text}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            
            response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=30)
            if response.status_code == 200:
                translated_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                break
            else:
                api_errors.append(f"[{model} Fail -> HTTP {response.status_code}: {response.text}]")
        except Exception as e:
            api_errors.append(f"[{model} Exception -> {str(e)}]")

    if translated_text:
        return {
            "translatedText": translated_text, "translated_text": translated_text,
            "translation": translated_text, "text": translated_text
        }
    else:
        # Aggregates and logs every single model attempt on the frontend interface
        combined_errors = " | ".join(api_errors)
        return {
            "translatedText": f"[Translation Gateway Error Details: {combined_errors}]",
            "translated_text": f"[Translation Gateway Error Details: {combined_errors}]",
            "text": "[Execution Failure]"
        }

@app.post("/api/correction")
async def save_correction(request: Request):
    try:
        body = await request.json()
        orig = body.get("original_text") or body.get("originalText")
        corr = body.get("corrected_translation") or body.get("correctedTranslation")
        lang = body.get("target_lang") or body.get("targetLang")
        
        conn = safe_get_db_connection()
        if conn and orig and corr and lang:
            cur = conn.cursor()
            cur.execute("INSERT INTO corrections (original_text, corrected_translation, target_lang) VALUES (%s, %s, %s);", (orig, corr, lang))
            conn.commit()
            cur.close()
            conn.close()
        return {"status": "memory_saved"}
    except Exception:
        return {"status": "bypass_saved"}
