import { useState } from 'react';
import Link from 'next/link';
import Uploader from '../components/Uploader';
import TranslationPanel from '../components/TranslationPanel';

export default function Home() {
  const [currentDocId, setCurrentDocId] = useState(null);
  const [currentSourceText, setCurrentSourceText] = useState('');

  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto">
      <header className="flex justify-between items-center mb-12 border-b pb-5">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">Self-Learning Reader & Translator</h1>
          <p className="text-slate-500 text-sm mt-0.5">Custom translation memory alignment engine framework.</p>
        </div>
        <Link href="/history" className="bg-slate-900 hover:bg-slate-800 text-white font-medium px-5 py-2.5 rounded-xl shadow-sm">
          View History Ledger
        </Link>
      </header>

      <main className="space-y-8">
        {!currentDocId ? (
          <Uploader onUploadSuccess={(id, text) => { setCurrentDocId(id); setCurrentSourceText(text); }} />
        ) : (
          <div>
            <div className="flex justify-between items-center bg-indigo-50 border border-indigo-100 rounded-xl p-4 mb-6">
              <span className="text-indigo-800 text-sm font-semibold">✓ Document successfully loaded into memory matrix.</span>
              <button onClick={() => { setCurrentDocId(null); setCurrentSourceText(''); }} className="text-indigo-600 text-xs font-bold underline">Process Another Document</button>
            </div>
            <TranslationPanel docId={currentDocId} sourceText={currentSourceText} />
          </div>
        )}
      </main>
    </div>
  );
}
