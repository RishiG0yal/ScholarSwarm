import { useState, useEffect } from "react";
import API_BASE from "../config";

export default function SimilarPapers({ title }) {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!title || title === "Unknown Title") { setLoading(false); return; }
    fetch(`${API_BASE}/similar?title=${encodeURIComponent(title)}`)
      .then((r) => r.json())
      .then((d) => { setPapers(d.papers || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [title]);

  if (loading) return <div className="text-center py-6 text-gray-600 text-sm">Loading similar papers...</div>;
  if (!papers.length) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        📚 Similar Papers (Semantic Scholar)
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {papers.map((p, i) => (
          <a
            key={i}
            href={p.url}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 hover:border-violet-500/40 hover:bg-gray-800/60 transition-all group"
          >
            <p className="text-sm font-medium text-gray-200 group-hover:text-violet-300 transition-colors leading-snug line-clamp-2 mb-2">
              {p.title}
            </p>
            <p className="text-xs text-gray-500 mb-2 truncate">{p.authors}</p>
            <div className="flex items-center gap-2">
              {p.year && <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded-full">{p.year}</span>}
              {p.citation_count > 0 && <span className="text-xs text-gray-600">📎 {p.citation_count}</span>}
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
