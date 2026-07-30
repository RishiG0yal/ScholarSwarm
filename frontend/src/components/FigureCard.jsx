import { useState } from "react";

export default function FigureCard({ figure }) {
  const [expanded, setExpanded] = useState(false);
  const hasImage = figure.base64 && figure.base64.length > 0;

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
      {/* Image */}
      <div
        className={`bg-gray-950 flex items-start justify-center cursor-pointer overflow-hidden transition-all duration-300 ${expanded ? "" : "max-h-96"}`}
        onClick={() => hasImage && setExpanded(!expanded)}
      >
        {hasImage ? (
          <img
            src={`data:image/png;base64,${figure.base64}`}
            alt={`Page ${figure.page} figure`}
            className="w-full object-contain object-top"
            style={expanded ? {} : { maxHeight: "384px" }}
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-700 py-12">
            <span className="text-4xl">🖼️</span>
            <span className="text-xs">Figure {figure.index}</span>
          </div>
        )}
      </div>

      {/* Caption */}
      <div className="p-4 border-t border-gray-800/60">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold text-gray-400">Page {figure.page}</span>
          {hasImage && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-violet-400 hover:text-violet-300 transition-colors flex items-center gap-1"
            >
              {expanded ? "▲ Collapse" : "▼ Expand full page"}
            </button>
          )}
        </div>
        {figure.description && figure.description !== "Figure could not be analyzed." && (
          <p className="text-xs text-gray-400 leading-relaxed">
            <span className="text-violet-400">🤖 </span>{figure.description}
          </p>
        )}
      </div>
    </div>
  );
}
