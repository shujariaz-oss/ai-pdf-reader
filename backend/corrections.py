import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import get_db_connection

def split_into_sentences(text: str) -> list:
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    return [s.strip() for s in sentences if s.strip()]

def find_learned_correction(original_sentence: str, target_lang: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT original_text, corrected_translation FROM corrections WHERE target_lang = %s",
        (target_lang,)
    )
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not records:
        return None
        
    for row in records:
        if row['original_text'].strip().lower() == original_sentence.strip().lower():
            return row['corrected_translation']
            
    corpus = [row['original_text'] for row in records]
    corpus.append(original_sentence)
    
    try:
        vectorizer = TfidfVectorizer().fit_transform(corpus)
        vectors = vectorizer.toarray()
        
        input_vector = vectors[-1].reshape(1, -1)
        historical_vectors = vectors[:-1]
        
        similarities = cosine_similarity(input_vector, historical_vectors)[0]
        best_match_idx = similarities.argmax()
        
        if similarities[best_match_idx] >= 0.90:
            return records[best_match_idx]['corrected_translation']
    except Exception:
        return None
        
    return None
