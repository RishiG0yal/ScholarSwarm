import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function SummaryCard({ summary, eli5Summary, readingLevel, readabilityScore }) {
  const [showEli5, setShowEli5] = useState(false);

  const hasEli5 = eli5Summary && eli5Summary !== summary && eli5Summary.length > 20;

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          AI Summary
        </h2>
        {hasEli5 && (
          <button
            onClick={() => setShowEli5(!showEli5)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium
              ${showEli5
                ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-400"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-300"}`}
          >
            {showEli5 ? "🎓 Academic" : "🧒 ELI5"}
          </button>
        )}
      </div>

      <div className="prose prose-invert prose-sm max-w-none
        prose-p:text-gray-200 prose-p:leading-relaxed prose-p:my-1
        prose-strong:text-white prose-ul:text-gray-200 prose-li:my-0.5
      ">
        <ReactMarkdown>{showEli5 ? eli5Summary : summary}</ReactMarkdown>
      </div>

      {showEli5 && readingLevel && (
        <p className="text-xs text-gray-600 mt-3 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-500/50" />
          Simplified for a {readingLevel.toLowerCase()} audience
          {readabilityScore > 0 && ` · Readability score: ${readabilityScore}/100`}
        </p>
      )}
    </div>
  );
}
