-- Create Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create Translations Table
CREATE TABLE IF NOT EXISTS translations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    target_lang VARCHAR(10) NOT NULL,
    translated_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create Self-Learning Corrections Memory Table
CREATE TABLE IF NOT EXISTS corrections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    original_text TEXT NOT NULL,
    corrected_translation TEXT NOT NULL,
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_translations_document ON translations(document_id);
CREATE INDEX IF NOT EXISTS idx_corrections_lookup ON corrections(target_lang);
