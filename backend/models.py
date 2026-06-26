from pydantic import BaseModel

class TranslationRequest(BaseModel):
    doc_id: str
    target_lang: str

class CorrectionRequest(BaseModel):
    original_text: str
    corrected_translation: str
    target_lang: str
