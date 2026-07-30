export default function PaperHeader({ data, fileName }) {
  const levelColor = {
    "High School": "text-green-400 bg-green-500/10 border-green-500/20",
    "Undergraduate": "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    "Graduate": "text-violet-400 bg-violet-500/10 border-violet-500/20",
    "Expert": "text-red-400 bg-red-500/10 border-red-500/20",
  }[data.reading_level] || "text-gray-400 bg-gray-500/10 border-gray-500/20";

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded">
              {data.file_type?.toUpperCase() || "PDF"}
            </span>
            <span className="text-xs text-gray-600 truncate">{fileName}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white leading-snug">{data.title}</h1>
          <p className="text-gray-400 text-sm mt-1">{data.authors}</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 mt-4">
        <Stat icon="📄" label={`${data.total_pages} pages`} />
        <Stat icon="📎" label={`${data.citations_count} citations`} />
        <Stat icon="✅" label={`${data.verified_count} verified`} color="text-green-400" />
        {data.flagged_count > 0 && (
          <Stat icon="⚠️" label={`${data.flagged_count} flagged`} color="text-yellow-400" />
        )}
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${levelColor}`}>
          📚 {data.reading_level}
        </span>
        {data.readability_score > 0 && (
          <span className="text-xs text-gray-500 bg-gray-800 px-2.5 py-1 rounded-full border border-gray-700">
            Readability: {data.readability_score}/100
          </span>
        )}
      </div>
    </div>
  );
}

function Stat({ icon, label, color = "text-gray-400" }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs ${color} bg-gray-800/80 px-2.5 py-1 rounded-full border border-gray-700`}>
      {icon} {label}
    </span>
  );
}
