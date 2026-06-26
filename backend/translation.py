from deep_translator import GoogleTranslator
from corrections import split_into_sentences, find_learned_correction

LANGUAGE_CODE_MAP = {
    "hindi": "hi",
    "tamil": "ta",
    "bengali": "bn",
    "spanish": "es",
    "french": "fr"
}

def translate_text(text: str, target_lang_name: str) -> str:
    lang_code = LANGUAGE_CODE_MAP.get(target_lang_name.lower(), "en")
    sentences = split_into_sentences(text)
    translated_segments = []
    
    translator = GoogleTranslator(source='auto', target=lang_code)
    
    for sentence in sentences:
        saved_correction = find_learned_correction(sentence, lang_code)
        
        if saved_correction:
            translated_segments.append(saved_correction)
        else:
            try:
                if len(sentence.strip()) > 0:
                    translation = translator.translate(sentence)
                    translated_segments.append(translation)
                else:
                    translated_segments.append(sentence)
            except Exception:
                translated_segments.append(sentence)
                
    return " ".join(translated_segments)
