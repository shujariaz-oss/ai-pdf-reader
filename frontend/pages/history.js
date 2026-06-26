import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '../utils/api';

export default function History() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const res = await api.get('/api/history');
      setHistory(res.data);
    } catch (err) {
      alert('Failed to fetch archival histories.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

  const deleteItem = async (id) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await api.delete(`/api/document/${id}`);
      fetchHistory();
    } catch (err) {
      alert('Deletion sequence failed.');
    }
  };

  return (
    <div className="min-h-screen p-6 max-w-5xl mx-auto">
      <header className="flex justify-between items-center mb-10 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Historical Translation Registry</h1>
          <Link href="/" className="text-indigo-600 font-semibold text-sm hover:underline mt-1 block">← Return to primary workspace</Link>
        </div>
      </header>

      {loading ? (
        <p className="text-center text-slate-500 py-12">Retrieving data registries...</p>
      ) : history.length === 0 ? (
        <div className="text-center py-16 bg-white border rounded-2xl shadow-sm">
          <p className="text-slate-400 font-medium mb-3">No parsed documents found inside history context.</p>
        </div>
      ) : (
        <div className="bg-white shadow-sm border rounded-2xl overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b text-slate-500 text-xs uppercase font-bold">
                <th className="p-4">Parsed File Title</th>
                <th className="p-4">Execution Timestamp</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y text-slate-700 text-sm font-medium">
              {history.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50/50">
                  <td className="p-4 text-slate-900 font-semibold max-w-xs truncate">{doc.filename}</td>
                  <td className="p-4 text-slate-400 font-normal">{new Date(doc.created_at).toLocaleString()}</td>
                  <td className="p-4 text-right space-x-3">
                    <button onClick={() => deleteItem(doc.id)} className="text-rose-600 hover:text-rose-800 underline text-xs bg-transparent border-0 cursor-pointer">Purge</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
