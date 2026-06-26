import { useState, useEffect } from 'react';
import api from '../utils/api';

export default function TranslationPanel({ docId, sourceText }) {
  const [language, setLanguage] = useState('Hindi');
  const [translatedText, setTranslatedText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sentences, setSentences] = useState([]);
  const [translatedSentences, setTranslatedSentences] = useState([]);
  const [editingIndex, setEditingIndex] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [savedStatus, setSavedStatus] = useState({});

  const cleanSplit = (text) => {
    if (!text) return [];
    // Using standard split pattern and native JavaScript .trim()
    return text.split(/(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s/).filter(s => s.trim());
  };

  useEffect(() => {
    if (sourceText) setSentences(cleanSplit(sourceText));
  }, [sourceText]);

  useEffect(() => {
    if (translatedText) setTranslatedSentences(cleanSplit(translatedText));
  }, [translatedText]);

  const handleTranslate = async () => {
    setLoading(true);
    try {
      const res = await api.post('/api/translate', { doc_id: docId, target_lang: language });
      setTranslatedText(res.data.translated_text);
    } catch (err) {
      alert('Translation process failed.');
    } finally {
      setLoading(false);
    }
  };

  const saveCorrection = async (index) => {
    try {
      await api.post('/api/correction', {
        original_text: sentences[index],
        corrected_translation: editValue,
        target_lang: language
      });
      const updated = [...translatedSentences];
      updated[index] = editValue;
      setTranslatedSentences(updated);
      setEditingIndex(null);
      setSavedStatus(prev => ({ ...prev, [index]: true }));
    } catch (err) {
      alert('Failed to save correction to memory pipeline.');
    }
  };

  return (
    <div className="mt-8 bg-white shadow-md rounded-2xl p-6 border border-slate-100">
      <div className="flex items-center justify-between gap-4 mb-6 pb-4 border-b">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1">Target Language</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-48 bg-slate-50 border rounded-lg p-2 font-medium">
            <option value="Hindi">Hindi (हिन्दी)</option>
            <option value="Tamil">Tamil (தமிழ்)</option>
            <option value="Bengali">Bengali (বাংলা)</option>
            <option value="Spanish">Spanish (Español)</option>
            <option value="French">French (Français)</option>
          </select>
        </div>
        <button onClick={handleTranslate} disabled={loading} className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-6 py-2.5 rounded-xl disabled:bg-indigo-300">
          {loading ? 'Processing Pipeline...' : 'Execute Translation'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-50 rounded-xl p-4 max-h-[60vh] overflow-y-auto">
          <h3 className="font-bold text-slate-700 mb-3 border-b pb-1">Original Extracted Text</h3>
          <div className="space-y-3">
            {sentences.map((s, idx) => (
              <p key={idx} className={`p-2 rounded text-slate-800 leading-relaxed ${editingIndex === idx ? 'bg-indigo-50 border-l-4 border-indigo-500' : ''}`}>{s}</p>
            ))}
          </div>
        </div>

        <div className="bg-slate-50 rounded-xl p-4 max-h-[60vh] overflow-y-auto">
          <h3 className="font-bold text-slate-700 mb-3 border-b pb-1">Interactive Translated Output (Click to Teach)</h3>
          <div className="space-y-3">
            {translatedSentences.length === 0 ? (
              <p className="text-slate-400 text-sm italic py-4">Trigger translation execution to view output sentences.</p>
            ) : (
              translatedSentences.map((s, idx) => (
                <div key={idx} className="group relative bg-white border rounded-lg p-3 hover:shadow-sm">
                  {editingIndex === idx ? (
                    <div className="space-y-2">
                      <textarea value={editValue} onChange={(e) => setEditValue(e.target.value)} className="w-full p-2 border rounded text-base" rows={3} />
                      <div className="flex space-x-2 justify-end">
                        <button onClick={() => setEditingIndex(null)} className="px-3 py-1 text-xs text-slate-500">Cancel</button>
                        <button onClick={() => saveCorrection(idx)} className="px-3 py-1 text-xs bg-green-600 text-white rounded">Save & Teach AI</button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <p className="text-slate-800 leading-relaxed pr-8">{s}</p>
                      <div className="absolute right-2 top-2 flex space-x-1">
                        {savedStatus[idx] && <span className="text-emerald-600 bg-emerald-50 text-[10px] font-bold px-1.5 py-0.5 rounded border border-emerald-200">Learned Memory</span>}
                        <button onClick={() => { setEditingIndex(idx); setEditValue(s); }} className="opacity-0 group-hover:opacity-100 text-indigo-600 hover:bg-indigo-50 p-1 rounded transition-all">✏️</button>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
