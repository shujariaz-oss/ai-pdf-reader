from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import TranslationRequest, CorrectionRequest
from database import get_db_connection
from ocr import extract_text_from_pdf
from translation import translate_text, LANGUAGE_CODE_MAP

app = FastAPI(title="Self-Learning PDF Translator Core API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid extension file framework. Requires PDF.")
    
    try:
        file_bytes = await file.read()
        extracted_text = extract_text_from_pdf(file_bytes)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, extracted_text) VALUES (%s, %s) RETURNING id",
            (file.filename, extracted_text)
        )
        doc_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"doc_id": str(doc_id), "extracted_text": extracted_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Parser Error: {str(e)}")

@app.post("/api/translate")
async def trigger_translation(payload: TranslationRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT translated_text FROM translations WHERE document_id = %s AND target_lang = %s",
        (payload.doc_id, payload.target_lang)
    )
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        conn.close()
        return {"translated_text": existing['translated_text']}
        
    cursor.execute("SELECT extracted_text FROM documents WHERE id = %s", (payload.doc_id,))
    doc_record = cursor.fetchone()
    if not doc_record:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Target document container context not found.")
        
    try:
        computed_translation = translate_text(doc_record['extracted_text'], payload.target_lang)
        cursor.execute(
            "INSERT INTO translations (document_id, target_lang, translated_text) VALUES (%s, %s, %s)",
            (payload.doc_id, payload.target_lang, computed_translation)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"translated_text": computed_translation}
    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Translation Subsystem Error: {str(e)}")

@app.post("/api/correction")
async def save_correction(payload: CorrectionRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        target_code = LANGUAGE_CODE_MAP.get(payload.target_lang.lower(), payload.target_lang.lower())
        cursor.execute(
            "INSERT INTO corrections (original_text, corrected_translation, target_lang) VALUES (%s, %s, %s)",
            (payload.original_text.strip(), payload.corrected_translation.strip(), target_code)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history_ledger():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, created_at FROM documents ORDER BY created_at DESC")
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return records

@app.get("/api/document/{doc_id}")
async def get_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, extracted_text, created_at FROM documents WHERE id = %s", (doc_id,))
    doc = cursor.fetchone()
    if not doc:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")
    cursor.execute("SELECT target_lang, translated_text FROM translations WHERE document_id = %s", (doc_id,))
    translations = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"document": doc, "translations": {t['target_lang']: t['translated_text'] for t in translations}}

@app.delete("/api/document/{doc_id}")
async def delete_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success"}
