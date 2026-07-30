import { useState } from "react";
import API_BASE from "../config";
import ReactMarkdown from "react-markdown";

const SUGGESTIONS = [
  "What is the main contribution?",
  "What datasets were used?",
  "What are the key results?",
  "How does this compare to prior work?",
];

export default function AskPaper({ resultId, title }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAsk = async () => {
    if (!question.trim() || !resultId) return;
    setLoading(true);
    setAnswer(null);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result_id: resultId, question: question.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Could not get answer.");
      }
      setAnswer(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 sm:p-6">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        💬 Ask This Paper
      </h2>

      <div className="flex flex-wrap gap-2 mb-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setQuestion(s)}
            className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-1.5 rounded-full text-gray-400 hover:text-gray-200 transition-all"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask anything about this paper..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-500 transition-colors"
        />
        <button
          onClick={handleAsk}
          disabled={!question.trim() || loading}
          className="px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-800 disabled:text-gray-600 rounded-xl text-sm font-medium transition-all"
        >
          {loading
            ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
            : "Ask"}
        </button>
      </div>

      {answer && (
        <div className="mt-4 bg-gray-800/60 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center flex-wrap gap-2 mb-2">
            <span className="text-xs text-violet-400 font-medium">🤖 ScholarSwarm</span>
            {answer.source_page && (
              <span className="text-xs text-gray-600 bg-gray-900 px-2 py-0.5 rounded-full">
                Source: Page {answer.source_page}
              </span>
            )}
            {answer.pages_searched?.length > 1 && (
              <span className="text-xs text-gray-700">
                (searched pages {answer.pages_searched.join(", ")})
              </span>
            )}
          </div>
          <div className="prose prose-invert prose-sm max-w-none
            prose-p:text-gray-200 prose-p:leading-relaxed prose-p:my-1
            prose-strong:text-white prose-strong:font-semibold
            prose-ul:text-gray-200 prose-ul:my-1 prose-ul:pl-4
            prose-ol:text-gray-200 prose-ol:my-1 prose-ol:pl-4
            prose-li:my-0.5 prose-li:text-gray-200
            prose-headings:text-gray-100 prose-headings:font-semibold
            prose-code:text-violet-300 prose-code:bg-gray-900 prose-code:px-1 prose-code:rounded
          ">
            <ReactMarkdown>{answer.answer}</ReactMarkdown>
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
    </section>
  );
}
