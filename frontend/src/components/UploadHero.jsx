import { useState, useRef } from "react";

const FEATURES = [
  "PDF & PPTX", "3-Agent Pipeline", "Claim Verification",
  "Table Extraction", "Vision AI", "Flashcards", "Ask the Paper", "Markdown Export",
];

export default function UploadHero({ onUpload, onDemo }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const inputRef = useRef(null);

  const isValid = (f) => f && (f.type === "application/pdf" || f.name.endsWith(".pptx"));

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (isValid(f)) setFile(f);
  };

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 text-violet-400 text-xs font-medium bg-violet-500/10 border border-violet-500/20 px-3 py-1.5 rounded-full mb-5">
          <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-pulse" />
          Groq · Gemini Vision · 3-Agent Pipeline
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold mb-4 bg-gradient-to-r from-violet-400 via-cyan-400 to-violet-400 bg-clip-text text-transparent leading-tight">
          Understand Any Research<br />Paper in 30 Seconds
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto">
          Upload a PDF or PPTX. Our AI reads the whole paper — text, tables, charts —
          then sends two agents to verify every claim before you see it.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 justify-center mb-8">
        {FEATURES.map((f) => (
          <span key={f} className="text-xs bg-gray-800/80 border border-gray-700 px-3 py-1 rounded-full text-gray-400">
            ✓ {f}
          </span>
        ))}
      </div>

      <div
        className={`w-full max-w-xl border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200
          ${dragging ? "border-violet-400 bg-violet-500/10 scale-[1.02]"
            : file ? "border-cyan-400 bg-cyan-500/10"
            : "border-gray-700 bg-gray-900/50 hover:border-violet-500 hover:bg-gray-800/50"}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.pptx"
          className="hidden"
          onChange={(e) => { const f = e.target.files[0]; if (isValid(f)) setFile(f); }}
        />
        {file ? (
          <div>
            <div className="text-4xl mb-3">{file.name.endsWith(".pptx") ? "📊" : "📄"}</div>
            <p className="text-cyan-300 font-semibold truncate max-w-xs mx-auto">{file.name}</p>
            <p className="text-gray-500 text-sm mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB · Ready</p>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="mt-3 text-xs text-gray-500 hover:text-gray-300 underline"
            >
              Remove
            </button>
          </div>
        ) : (
          <div>
            <div className="text-4xl mb-3">🗂️</div>
            <p className="text-gray-300 font-medium">Drag & drop a PDF or PPTX here</p>
            <p className="text-gray-600 text-sm mt-1">or click to browse · Max 20MB</p>
          </div>
        )}
      </div>

      <div className="flex gap-3 mt-5">
        <button
          onClick={() => file && onUpload(file)}
          disabled={!file}
          className={`px-8 py-3 rounded-xl font-semibold text-base transition-all duration-200
            ${file
              ? "bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 shadow-lg shadow-violet-500/20 hover:scale-105"
              : "bg-gray-800 text-gray-600 cursor-not-allowed"}`}
        >
          ⚡ Generate Brief
        </button>
        <button
          onClick={onDemo}
          className="px-5 py-3 rounded-xl font-semibold text-base bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 transition-all text-gray-300"
        >
          Try Demo
        </button>
      </div>
      <p className="text-gray-700 text-xs mt-4">Demo: "Attention Is All You Need" · Vaswani et al. 2017</p>
    </div>
  );
}
