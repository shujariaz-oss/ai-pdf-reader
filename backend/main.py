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

# Dual-cased insulation model to eliminate 422 schema mismatch crashes
class TranslationRequest(BaseModel):
    doc_id: str | None = None
    docId: str | None = None
    document_id: str | None = None
    documentId: str | None = None
    id: str | None = None
    target_lang: str | None = None
    targetLang: str | None = None
    text: str | None = None
    source_text: str | None = None
    sourceText: str | None = None
    extracted_text: str | None = None
    extractedText: str | None = None

class CorrectionRequest(BaseModel):
    original_text: str | None = None
    originalText: str | None = None
    corrected_translation: str | None = None
    correctedTranslation: str | None = None
    target_lang: str | None = None
    targetLang: str | None = None

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
                
                page_extracted = False
                # Cascading model verification loop for extraction
                for model in ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
                    try:
                        print(f"Attempting OCR processing with runtime matrix: {model}")
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
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
                        
                        response = requests.post(url, headers=headers, json=payload, timeout=30)
                        if response.status_code == 200:
                            res_data = response.json()
                            page_text = res_data['candidates'][0]['content']['parts'][0]['text']
                            full_text += page_text + "\n"
                            page_extracted = True
                            print(f"Successfully extracted page {i+1} using matrix: {model}")
                            break
                        else:
                            print(f"Model matrix operational reject ({model}): Status {response.status_code}")
                    except Exception as model_err:
                        print(f"Model matrix execution cycle failure ({model}): {str(model_err)}")
                
                if not page_extracted:
                    print(f"All cloud model components exhausted for page {i+1}. Deploying local engine fallback.")
                    full_text += fallback_tesseract(img)
                    
            except Exception as e:
                print(f"Pipeline intercept connection exception on Page {i+1}: {str(e)}")
                full_text += fallback_tesseract(img)
        else:
            print("LOG WARNING: GEMINI_API_KEY environment lookup variable is unassigned.")
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

    print("[COMPLETE] Sending complete response payload matrix back to frontend UI tier.")
    return {
        "docId": str(doc_id),
        "doc_id": str(doc_id),
        "documentId": str(doc_id),
        "document_id": str(doc_id),
        "id": str(doc_id),
        "sourceText": full_text,
        "source_text": full_text,
        "extractedText": full_text,
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
    print(f"\n[START] Received inbound translation request payload analysis.")
    
    # Normalize naming variables across both frontend casing standards
    target_lang = req.target_lang or req.targetLang
    source_text = req.source_text or req.sourceText or req.text or req.extracted_text or req.extractedText or ""
    target_id = req.doc_id or req.docId or req.document_id or req.documentId or req.id
    
    print(f"Context Parameters -> ID: {target_id}, Target Language: {target_lang}, Extraction Stream Unit Size: {len(source_text)}")

    if not target_lang:
        print("CRITICAL: Aborting pipeline. Destination language structural data missing.")
        raise HTTPException(status_code=400, detail="Missing target language parameter (target_lang or targetLang)")

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
        cur.execute("SELECT original_text, corrected_translation FROM corrections WHERE target_lang = %s LIMIT 10;", (target_lang,))
        rows = cur.fetchall()
        if rows:
            memory_context = "Adhere strictly to style adjustments from these past corrections:\n"
            for r in rows:
                memory_context += f"Source: '{r[0]}' -> Output: '{r[1]}'\n"
        cur.close()
        conn.close()
    except Exception:
        pass

    translated_text = None
    if GEMINI_API_KEY:
        # Multi-tiered fallback stack to clear runtime endpoint blocking
        for model in ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                print(f"Initiating translation engine path: {model}")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                headers = {'Content-Type': 'application/json'}
                prompt = f"Translate the following text directly into {target_lang}. Preserve layout styling. Do not add chat preamble.\n{memory_context}\nText context:\n{source_text}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    res_data = response.json()
                    translated_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    print(f"Translation logic compiled successfully via: {model}")
                    break
                else:
                    print(f"Model processing runtime rejected ({model}): Status {response.status_code}")
            except Exception as e:
                print(f"Model processing routing failure ({model}): {str(e)}")
                
    if translated_text:
        # Map output schemas to cover both camelCase and snake_case UI hooks
        return {
            "translatedText": translated_text,
            "translated_text": translated_text,
            "translation": translated_text,
            "text": translated_text
        }
    else:
        print("CRITICAL LOG ERROR: Core structural engine failure. All available model endpoints rejected payload.")
        raise HTTPException(status_code=500, detail="All Gemini translation model attempts exhausted or failed.")

@app.post("/api/correction")
async def save_correction(req: CorrectionRequest):
    orig = req.original_text or req.originalText
    corr = req.corrected_translation or req.correctedTranslation
    lang = req.target_lang or req.targetLang
    
    if not orig or not corr or not lang:
        raise HTTPException(status_code=400, detail="Missing required parameters for correction saving.")
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO corrections (original_text, corrected_translation, target_lang) VALUES (%s, %s, %s);",
            (orig, corr, lang)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "memory_saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory Sync failed: {str(e)}")
