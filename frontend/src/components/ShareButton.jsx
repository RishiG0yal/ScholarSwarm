import { useState } from "react";

export default function ShareButton({ resultId }) {
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    if (!resultId) return;
    const url = `${window.location.origin}/brief/${resultId}`;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (!resultId) return null;

  return (
    <button
      onClick={handleShare}
      className={`flex items-center gap-2 text-sm px-4 py-2 border rounded-xl transition-all
        ${copied
          ? "bg-green-500/10 border-green-500/40 text-green-400"
          : "bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-300"}`}
    >
      {copied ? "✅ Copied!" : "🔗 Share Brief"}
    </button>
  );
}
