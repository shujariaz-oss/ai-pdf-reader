import os
import io
import base64
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

def get_db_connection():
    if not DATABASE_URL:
        print("LOG ERROR: DATABASE_URL variable is empty!")
        raise HTTPException(status_code=500, detail="DATABASE_URL configuration missing.")
    return psycopg2.connect(DATABASE_URL)

class TranslationRequest(BaseModel):
    doc_id: str | None = None
    document_id: str | None = None
    id: str | None = None
    target_lang: str
    text: str | None = None
    source_text: str | None = None

class CorrectionRequest(BaseModel):
    original_text: str
    corrected_translation: str
    target_lang: str

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    print(f"\n[START] Received file upload request for: {file.filename}")
    file_bytes = await file.read()
    print(f"Read {len(file_bytes)} bytes from inbound payload.")
    
    try:
        print("Attempting to slice PDF pages into image sequences via pdf2image...")
        images = convert_from_bytes(file_bytes)
        print(f"Success! Fragmented PDF layout into {len(images)} separate pages.")
    except Exception as e:
        print(f"CRITICAL LOG ERROR: pdf2image compilation split failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process target PDF layout: {str(e)}")
    
    full_text = ""
    
    for i, img in enumerate(images):
        print(f"--- Processing Content Extraction Matrix for Page {i+1} ---")
        full_text += f"\n--- PAGE {i+1} ---\n"
        
        if GEMINI_API_KEY:
            try:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                print(f"Page {i+1} image optimized and encoded into Base64 format.")
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Transcribe all handwritten and printed layout text from this document page clearly and accurately. Keep contextual points together."},
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }]
                }
                
                print(f"Dispatching direct REST request payload to Google Core APIs for Page {i+1}...")
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                print(f"Google Server responded with HTTP status check: {response.status_code}")
                
                if response.status_code == 200:
                    res_data = response.json()
                    page_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    full_text += page_text + "\n"
                    print(f"Successfully extracted {len(page_text)} layout characters for Page {i+1}.")
                else:
                    print(f"API rejection notice on Page {i+1}: {response.text}")
                    full_text += f"[Gemini Cloud Core Error {response.status_code}: {response.text}]\n"
                    full_text += "--- Attempting Local Backup Engine ---\n"
                    full_text += fallback_tesseract(img)
                    
            except Exception as e:
                print(f"Pipeline intercept connection exception on Page {i+1}: {str(e)}")
                full_text += f"[Connection Interrupted: {str(e)}]\n"
                full_text += fallback_tesseract(img)
        else:
            print("LOG WARNING: GEMINI_API_KEY environment lookup variable is unassigned.")
            full_text += "[Gemini API Key missing in Server Settings]\n"
            full_text += fallback_tesseract(img)
            
    doc_id = "temp_pipeline_id"
    try:
        print("Syncing extracted document matrix into PostgreSQL tracking system...")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (file_name, source_text) VALUES (%s, %s) RETURNING id;",
            (file.filename, full_text)
        )
        doc_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()
        print(f"Database serialization successful. Generated tracking signature ID: {doc_id}")
    except Exception as db_err:
        print(f"Database logging pass-through notification: {str(db_err)}")
        pass

    print("[COMPLETE] Sending universal response payload matrix back to frontend UI tier.")
    return {
        "doc_id": str(doc_id),
        "document_id": str(doc_id),
        "id": str(doc_id),
        "source_text": full_text,
        "extracted_text": full_text,
        "text": full_text
    }

def fallback_tesseract(img):
    print("Executing fallback tesseract logic...")
    if not pytesseract:
        return "[Local Engine Utility Missing]"
    try:
        if os.path.exists('/usr/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
        max_size = 1500
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
        custom_config = r'--psm 11 --oem 3'
        return pytesseract.image_to_string(img, config=custom_config)
    except Exception as e:
        print(f"Fallback Tesseract component execution crash: {str(e)}")
        return f"[Local Engine Backup Failed: {str(e)}]"

@app.post("/api/translate")
async def translate_text(req: TranslationRequest):
    print(f"\n[START] Received translation request for target language: {req.target_lang}")
    
    # ADVANCED RESILIENCE: Check if direct payload text is provided before falling back to DB lookup
    source_text = req.source_text or req.text or ""
    target_id = req.doc_id or req.document_id or req.id
    
    print(f"Context Parameters -> ID: {target_id}, Direct Payload Text Length: {len(source_text)}")

    if not source_text and target_id:
        print(f"No direct inline text found. Pulling context from PostgreSQL database for ID: {target_id}")
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT source_text FROM documents WHERE id = %s;", (target_id,))
            row = cur.fetchone()
            if row:
                source_text = row[0]
                print(f"Database record sync complete. Loaded {len(source_text)} context characters.")
            else:
                print(f"Database lookup yielded no records for entry ID: {target_id}")
            cur.close()
            conn.close()
        except Exception as db_err:
            print(f"Database execution exception intercepted: {str(db_err)}")
            pass

    if not source_text:
        print("CRITICAL: Translation payload evaluation halted. Source text block context is entirely empty.")
        raise HTTPException(status_code=400, detail="No readable source context found for translation pipeline.")

    memory_context = ""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT original_text, corrected_translation FROM corrections WHERE target_lang = %s LIMIT 10;", (req.target_lang,))
        rows = cur.fetchall()
        if rows:
            memory_context = "Adhere strictly to style adjustments from these past corrections:\n"
            for r in rows:
                memory_context += f"Source: '{r[0]}' -> Output: '{r[1]}'\n"
        cur.close()
        conn.close()
    except Exception:
        pass

    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
            headers = {'Content-Type': 'application/json'}
            prompt = f"Translate the following text directly into {req.target_lang}. Preserve layout styling. Do not add chat preamble.\n{memory_context}\nText context:\n{source_text}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            print("Dispatching translation text sequence bundle to Google Gemini core...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            print(f"Google Core Server translation response code: {response.status_code}")
            
            if response.status_code == 200:
                res_data = response.json()
                translated_text = res_data['candidates'][0]['content']['parts'][0]['text']
                print(f"Translation successful. Generated {len(translated_text)} output units.")
                return {
                    "translated_text": translated_text,
                    "text": translated_text,
                    "translation": translated_text
                }
            else:
                print(f"Google Core rejected translation request: {response.text}")
                raise HTTPException(status_code=500, detail=f"Gemini API translation error code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Network processing core pipeline exception occurred: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Translation connection failure: {str(e)}")
    else:
        print("LOG ERROR: GEMINI_API_KEY target variable missing during compilation runtime.")
        return {
            "translated_text": "[API Activation Pending Environment Variable Verification]",
            "text": "[API Activation Pending]"
        }

@app.post("/api/correction")
async def save_correction(req: CorrectionRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO corrections (original_text, corrected_translation, target_lang) VALUES (%s, %s, %s);",
            (req.original_text, req.corrected_translation, req.target_lang)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "memory_saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory Sync failed: {str(e)}")
