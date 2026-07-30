import { useState } from "react";

export default function ClaimCard({ claim }) {
  const [expanded, setExpanded] = useState(false);
  const conf = Math.round((claim.confidence || 0) * 100);

  const status = claim.verified
    ? { label: "Verified", icon: "✅", color: "text-green-400", bg: "bg-green-500/8 border-green-500/20", bar: "bg-green-500" }
    : conf > 55
    ? { label: "Uncertain", icon: "⚠️", color: "text-yellow-400", bg: "bg-yellow-500/8 border-yellow-500/20", bar: "bg-yellow-500" }
    : { label: "Flagged", icon: "❌", color: "text-red-400", bg: "bg-red-500/8 border-red-500/20", bar: "bg-red-500" };

  const hasSource = claim.source_quote || claim.critique;
  const isRealCritique = claim.critique && !claim.critique.includes("processing error") && !claim.critique.includes("rate limit");

  return (
    <div className={`border rounded-xl p-4 space-y-3 ${status.bg}`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <span className={`text-xs font-semibold ${status.color} flex items-center gap-1.5 flex-shrink-0`}>
          {status.icon} {status.label}
        </span>
        <span className="text-xs text-gray-600 bg-gray-800/80 px-2 py-0.5 rounded-full flex-shrink-0">
          Page {claim.page}
        </span>
      </div>

      {/* Claim text */}
      <p className="text-gray-200 text-sm leading-relaxed">{claim.text}</p>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>Confidence</span>
          <span className={status.color}>{conf}%</span>
        </div>
        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full ${status.bar} rounded-full transition-all duration-700`}
            style={{ width: `${conf}%` }}
          />
        </div>
      </div>

      {/* Expandable source */}
      {hasSource && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
          >
            {expanded ? "▲ Hide source" : "▼ Show source text"}
          </button>
          {expanded && (
            <div className="space-y-2 pt-1">
              {claim.source_quote && (
                <div className="bg-gray-900/80 rounded-lg p-3 border border-gray-700/60">
                  <p className="text-xs text-gray-500 mb-1.5 font-medium">Source quote</p>
                  <p className="text-xs text-gray-300 italic leading-relaxed">"{claim.source_quote}"</p>
                </div>
              )}
              {isRealCritique && (
                <div className="bg-gray-900/80 rounded-lg p-3 border border-gray-700/60">
                  <p className="text-xs text-gray-500 mb-1.5 font-medium">Critic note</p>
                  <p className="text-xs text-gray-400 leading-relaxed">{claim.critique}</p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
