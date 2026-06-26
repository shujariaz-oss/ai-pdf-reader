import os
import io
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

try:
    import google.generativeai as genai
except ImportError:
    genai = None

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

if GEMINI_API_KEY and genai:
    print("Initializing Gemini configuration...")
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY environment variable is missing or empty!")

def get_db_connection():
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL configuration is missing on the server tier.")
    return psycopg2.connect(DATABASE_URL)

class TranslationRequest(BaseModel):
    doc_id: str | None = None
    document_id: str | None = None
    id: str | None = None
    target_lang: str

class CorrectionRequest(BaseModel):
    original_text: str
    corrected_translation: str
    target_lang: str

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_bytes = await file.read()
    
    try:
        images = convert_from_bytes(file_bytes)
    except Exception as e:
        print(f"Poppler PDF conversion crash: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process target PDF layout: {str(e)}")
    
    full_text = ""
    
    for i, img in enumerate(images):
        full_text += f"\n--- PAGE {i+1} ---\n"
        
        if GEMINI_API_KEY and genai:
            try:
                # Direct PIL image native passing (highly stable)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([
                    "Transcribe all handwritten and printed layout text from this mindmap infographic accurately. Keep contextual points together grouped by proximity.",
                    img
                ])
                full_text += response.text + "\n"
            except Exception as gemini_err:
                # Print the exact error to Render log dashboard
                print(f"CRITICAL: Gemini Vision failed on page {i+1}. Error: {gemini_err}")
                full_text += fallback_tesseract(img)
        else:
            full_text += fallback_tesseract(img)
            
    doc_id = "temp_pipeline_id"
    try:
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
    except Exception as db_err:
        print(f"Database save skipped: {db_err}")

    return {
        "doc_id": str(doc_id),
        "document_id": str(doc_id),
        "id": str(doc_id),
        "source_text": full_text,
        "extracted_text": full_text,
        "text": full_text
    }

def fallback_tesseract(img):
    if not pytesseract:
        return "[Local Engine Missing]"
    try:
        # Explicitly configure default Linux system paths for Render environment
        if os.path.exists('/usr/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
            
        max_size = 1500
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCEZOS)
        custom_config = r'--psm 11 --oem 3'
        return pytesseract.image_to_string(img, config=custom_config)
    except Exception as e:
        return f"[Layout Reading Interrupted: {str(e)}]"

@app.post("/api/translate")
async def translate_text(req: TranslationRequest):
    target_id = req.doc_id or req.document_id or req.id
    if not target_id:
        raise HTTPException(status_code=422, detail="Missing document identification reference mapping.")

    source_text = ""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT source_text FROM documents WHERE id = %s;", (target_id,))
        row = cur.fetchone()
        if row:
            source_text = row[0]
        cur.close()
        conn.close()
    except Exception:
        pass

    if not source_text or "[Layout Reading Interrupted" in source_text:
        source_text = "Please fix the text extraction phase first before submitting translations."

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

    if GEMINI_API_KEY and genai:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Translate the following raw structural text directly into {req.target_lang}. Preserve line numbers and layout codes like ''. Do not add chat preamble.\n{memory_context}\nText context:\n{source_text}"
            response = model.generate_content(prompt)
            return {
                "translated_text": response.text,
                "text": response.text,
                "translation": response.text
            }
        except Exception as e:
            print(f"Gemini Translation Route Crash: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Translation failure: {str(e)}")
    else:
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
