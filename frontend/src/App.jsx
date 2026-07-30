import { useState, useEffect } from "react";
import API_BASE from "./config";
import UploadHero from "./components/UploadHero";
import ProgressSteps from "./components/ProgressSteps";
import Dashboard from "./components/Dashboard";
import DEMO_DATA from "./demo-data";

export default function App() {
  const [state, setState] = useState("idle");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState("");
  const [serverWarm, setServerWarm] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(() => setServerWarm(true))
      .catch(() => setServerWarm(false));
  }, []);

  const handleUpload = async (file) => {
    setFileName(file.name);
    setState("loading");
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed.");
      }
      const data = await res.json();
      setResult(data);
      setState("done");
    } catch (err) {
      setError(err.message);
      setState("error");
    }
  };

  const handleDemo = () => {
    setFileName("attention-is-all-you-need.pdf");
    setResult(DEMO_DATA);
    setState("done");
  };

  const handleReset = () => {
    setState("idle");
    setResult(null);
    setError(null);
    setFileName("");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans">
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-violet-600 opacity-10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -right-40 w-96 h-96 bg-cyan-500 opacity-10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/3 w-64 h-64 bg-fuchsia-600 opacity-5 rounded-full blur-3xl" />
      </div>

      <header className="sticky top-0 z-50 border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-sm px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-cyan-500 rounded-lg flex items-center justify-center text-sm font-bold shadow-lg shadow-violet-500/20">
              S
            </div>
            <span className="text-lg font-bold tracking-tight">
              Scholar<span className="text-violet-400">Swarm</span>
            </span>
            <span className="hidden sm:inline text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full border border-gray-700">
              Multi-Agent Research Briefing
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-500">
              <span className={`w-1.5 h-1.5 rounded-full ${serverWarm ? "bg-green-400" : "bg-yellow-400 animate-pulse"}`} />
              {serverWarm ? "Server ready" : "Warming up..."}
            </div>
            {state === "done" && (
              <button onClick={handleReset} className="text-sm text-gray-400 hover:text-white transition-colors">
                ← New Paper
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        {state === "idle" && <UploadHero onUpload={handleUpload} onDemo={handleDemo} />}
        {state === "loading" && <ProgressSteps fileName={fileName} />}
        {state === "error" && (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-red-400 mb-2">Analysis Failed</h2>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">{error}</p>
            <button onClick={handleReset} className="px-6 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg transition-colors">
              Try Again
            </button>
          </div>
        )}
        {state === "done" && result && (
          <Dashboard data={result} fileName={fileName} onReset={handleReset} />
        )}
      </main>
    </div>
  );
}
