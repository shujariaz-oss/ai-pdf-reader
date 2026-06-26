import { useState } from 'react';
import api from '../utils/api';

export default function Uploader({ onUploadSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setError('Please select a valid PDF file.');
      return;
    }

    setError('');
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onUploadSuccess(res.data.doc_id, res.data.extracted_text);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred during file extraction.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-8 border-4 border-dashed border-slate-300 rounded-2xl bg-white text-center shadow-sm hover:border-indigo-400 transition-all">
      {loading ? (
        <div className="flex flex-col items-center justify-center space-y-3 py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p className="text-slate-600 font-medium">Extracting text & applying multi-lingual OCR structural lookup...</p>
        </div>
      ) : (
        <label className="cursor-pointer block py-12">
          <span className="text-indigo-600 font-semibold text-lg block mb-1">Click to upload your target PDF file</span>
          <span className="text-slate-400 text-sm">Supports native structural text and completely scanned flat images</span>
          <input type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
        </label>
      )}
      {error && <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
    </div>
  );
}
