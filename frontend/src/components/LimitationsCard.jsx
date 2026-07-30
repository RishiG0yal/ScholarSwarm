export default function LimitationsCard({ limitations }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 sm:p-6">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        ⚠️ Limitations & Constraints
      </h2>
      <ul className="space-y-2.5">
        {limitations.map((item, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="w-5 h-5 rounded-full bg-yellow-500/10 border border-yellow-500/25 flex items-center justify-center text-xs text-yellow-400 flex-shrink-0 mt-0.5">
              {i + 1}
            </span>
            <span className="text-gray-300 text-sm leading-relaxed">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
