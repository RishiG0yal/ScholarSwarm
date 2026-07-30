import { useState } from "react";
import API_BASE from "../config";

export default function CompareMode({ primaryData, onClose }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [compareData, setCompareData] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
      setCompareData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const findConflicts = () => {
    if (!compareData) return [];
    const conflicts = [];
    (primaryData.claims || []).forEach(pc => {
      (compareData.claims || []).forEach(cc => {
        const overlap = _wordOverlap(pc.text, cc.text);
        if (overlap > 0.3) {
          conflicts.push({ primary: pc, compare: cc, overlap, type: pc.verified && !cc.verified ? "conflict" : "related" });
        }
      });
    });
    return conflicts;
  };

  const sharedTerms = () => {
    if (!compareData) return [];
    const pt = new Set((primaryData.key_terms || []).map(t => t.term.toLowerCase()));
    return (compareData.key_terms || []).filter(t => pt.has(t.term.toLowerCase()));
  };

  return (
    <div className="fixed inset-0 z-50 bg-gray-950/95 backdrop-blur-sm overflow-auto">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white">⚖️ Paper Comparison</h2>
            {compareData && (
              <span className="text-xs bg-green-500/20 border border-green-500/30 text-green-400 px-2 py-1 rounded-full">
                Comparison ready
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors text-lg px-3 py-1 rounded-lg bg-gray-800">
            ✕ Close
          </button>
        </div>

        {/* Upload second paper */}
        {!compareData && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
              Upload Second Paper to Compare
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Comparing with: <span className="text-violet-400">{primaryData.title}</span>
            </p>
            <div className="flex gap-3 items-center">
              <input
                type="file"
                accept=".pdf,.pptx"
                onChange={e => setFile(e.target.files[0])}
                className="flex-1 text-sm text-gray-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-violet-600 file:text-white file:text-sm file:cursor-pointer hover:file:bg-violet-500"
              />
              <button
                onClick={handleUpload}
                disabled={!file || loading}
                className="px-5 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-800 disabled:text-gray-600 rounded-xl text-sm font-medium transition-all"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analyzing...
                  </span>
                ) : "Analyze & Compare"}
              </button>
            </div>
            {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
          </div>
        )}

        {compareData && (
          <>
            {/* Side by side summaries */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <PaperColumn title={primaryData.title} authors={primaryData.authors} summary={primaryData.summary} color="violet" label="Paper A" />
              <PaperColumn title={compareData.title} authors={compareData.authors} summary={compareData.summary} color="cyan" label="Paper B" />
            </div>

            {/* Conflicts & Relations */}
            {findConflicts().length > 0 && (
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 mb-4">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
                  🔄 Related Claims
                </h3>
                <div className="space-y-3">
                  {findConflicts().map((c, i) => (
                    <div key={i} className={`grid grid-cols-2 gap-3 p-3 rounded-xl border ${c.type === "conflict" ? "bg-red-500/5 border-red-500/20" : "bg-blue-500/5 border-blue-500/20"}`}>
                      <div>
                        <span className="text-xs text-violet-400 font-medium">Paper A</span>
                        <p className="text-xs text-gray-300 mt-1">{c.primary.text}</p>
                        <span className={`text-xs ${c.primary.verified ? "text-green-400" : "text-red-400"}`}>
                          {c.primary.verified ? "✅ Verified" : "❌ Flagged"}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-cyan-400 font-medium">Paper B</span>
                        <p className="text-xs text-gray-300 mt-1">{c.compare.text}</p>
                        <span className={`text-xs ${c.compare.verified ? "text-green-400" : "text-red-400"}`}>
                          {c.compare.verified ? "✅ Verified" : "❌ Flagged"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Shared key terms */}
            {sharedTerms().length > 0 && (
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 mb-4">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  🔑 Shared Key Concepts ({sharedTerms().length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {sharedTerms().map((t, i) => (
                    <span key={i} className="text-xs bg-violet-500/20 border border-violet-500/30 text-violet-300 px-2 py-1 rounded-full">
                      {t.term}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Combined limitations */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-violet-400 mb-3">Paper A Limitations</h3>
                <ul className="space-y-2">
                  {(primaryData.limitations || []).map((l, i) => (
                    <li key={i} className="text-xs text-gray-300 flex gap-2">
                      <span className="text-yellow-500 flex-shrink-0">•</span>{l}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-cyan-400 mb-3">Paper B Limitations</h3>
                <ul className="space-y-2">
                  {(compareData.limitations || []).map((l, i) => (
                    <li key={i} className="text-xs text-gray-300 flex gap-2">
                      <span className="text-yellow-500 flex-shrink-0">•</span>{l}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function PaperColumn({ title, authors, summary, color, label }) {
  const borderColor = color === "violet" ? "border-violet-500/30" : "border-cyan-500/30";
  const textColor = color === "violet" ? "text-violet-400" : "text-cyan-400";
  return (
    <div className={`bg-gray-900/60 border ${borderColor} rounded-2xl p-5`}>
      <span className={`text-xs font-semibold ${textColor} uppercase tracking-wider`}>{label}</span>
      <h3 className="text-sm font-bold text-white mt-1 mb-1 leading-snug">{title}</h3>
      <p className="text-xs text-gray-500 mb-3">{authors}</p>
      <p className="text-xs text-gray-300 leading-relaxed">{summary}</p>
    </div>
  );
}

function _wordOverlap(a, b) {
  if (!a || !b) return 0;
  const stopwords = new Set(["the","a","an","is","was","are","were","this","that","of","in","to","and","or"]);
  const wa = new Set(a.toLowerCase().split(/\W+/).filter(w => w.length > 3 && !stopwords.has(w)));
  const wb = new Set(b.toLowerCase().split(/\W+/).filter(w => w.length > 3 && !stopwords.has(w)));
  let overlap = 0;
  wa.forEach(w => { if (wb.has(w)) overlap++; });
  return overlap / Math.max(wa.size, wb.size, 1);
}
