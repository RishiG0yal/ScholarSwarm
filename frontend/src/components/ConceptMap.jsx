import { useState } from "react";

const COLORS = [
  { bg: "bg-violet-500/20 border-violet-500/40", text: "text-violet-300", hover: "hover:bg-violet-500/35" },
  { bg: "bg-cyan-500/20 border-cyan-500/40", text: "text-cyan-300", hover: "hover:bg-cyan-500/35" },
  { bg: "bg-fuchsia-500/20 border-fuchsia-500/40", text: "text-fuchsia-300", hover: "hover:bg-fuchsia-500/35" },
  { bg: "bg-emerald-500/20 border-emerald-500/40", text: "text-emerald-300", hover: "hover:bg-emerald-500/35" },
  { bg: "bg-amber-500/20 border-amber-500/40", text: "text-amber-300", hover: "hover:bg-amber-500/35" },
  { bg: "bg-blue-500/20 border-blue-500/40", text: "text-blue-300", hover: "hover:bg-blue-500/35" },
  { bg: "bg-rose-500/20 border-rose-500/40", text: "text-rose-300", hover: "hover:bg-rose-500/35" },
  { bg: "bg-teal-500/20 border-teal-500/40", text: "text-teal-300", hover: "hover:bg-teal-500/35" },
];

export default function ConceptMap({ terms, title }) {
  const [active, setActive] = useState(null);

  if (!terms?.length) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Key Concepts
      </h2>
      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
        {/* Central node */}
        <div className="flex justify-center mb-5">
          <div className="bg-gradient-to-r from-violet-600/30 to-cyan-600/30 border border-violet-500/40 rounded-xl px-4 py-2 text-sm font-semibold text-white text-center max-w-xs">
            {title?.length > 55 ? title.slice(0, 55) + "…" : title}
          </div>
        </div>

        {/* Term bubbles */}
        <div className="flex flex-wrap gap-2 justify-center">
          {terms.map((term, i) => {
            const color = COLORS[i % COLORS.length];
            const isActive = active === i;
            return (
              <button
                key={i}
                onClick={() => setActive(isActive ? null : i)}
                className={`border rounded-xl px-3 py-2 text-xs font-medium transition-all duration-200 text-left
                  ${color.bg} ${color.text} ${color.hover}
                  ${isActive ? "ring-1 ring-white/20 scale-105" : "hover:scale-105"}`}
              >
                {term.term}
              </button>
            );
          })}
        </div>

        {/* Definition panel — shows below when a term is clicked */}
        {active !== null && terms[active] && (
          <div className="mt-4 bg-gray-800/60 border border-gray-700 rounded-xl p-4 transition-all">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className={`text-sm font-semibold mb-1 ${COLORS[active % COLORS.length].text}`}>
                  {terms[active].term}
                </p>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {terms[active].definition}
                </p>
              </div>
              <button
                onClick={() => setActive(null)}
                className="text-gray-600 hover:text-gray-400 text-xs flex-shrink-0"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {active === null && (
          <p className="text-center text-xs text-gray-700 mt-3">
            Click any term for its definition
          </p>
        )}
      </div>
    </section>
  );
}
