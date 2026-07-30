import { useState, useEffect } from "react";

const STEPS = [
  { label: "Extracting text from document",         icon: "📄", duration: 2000  },
  { label: "Parsing tables and figures",            icon: "📊", duration: 4000  },
  { label: "Analyzing figures with Vision AI",      icon: "🖼️", duration: 12000 },
  { label: "Agent 1: Extracting claims & summary",  icon: "🧠", duration: 45000 },
  { label: "Agent 2: Verifying every claim",        icon: "🔍", duration: 30000 },
  { label: "Agent 3: Simplifying for readability",  icon: "✨", duration: 8000  },
];

const TOTAL_ESTIMATED = STEPS.reduce((s, step) => s + step.duration, 0);

export default function ProgressSteps({ fileName }) {
  const [active, setActive] = useState(0);
  const [done, setDone] = useState([]);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startTime = Date.now();

    // Real elapsed time ticker
    const ticker = setInterval(() => {
      setElapsed(Date.now() - startTime);
    }, 500);

    // Step activations — based on estimated cumulative time
    let cumulativeDelay = 0;
    const timers = [];

    STEPS.forEach((step, i) => {
      const activateAt = cumulativeDelay;
      const doneAt = cumulativeDelay + step.duration;

      timers.push(setTimeout(() => setActive(i), activateAt));

      // Don't auto-complete the last step — let the API response do that
      if (i < STEPS.length - 1) {
        timers.push(setTimeout(() => setDone((d) => [...d, i]), doneAt));
      }

      cumulativeDelay += step.duration;
    });

    return () => {
      clearInterval(ticker);
      timers.forEach(clearTimeout);
    };
  }, []);

  // Progress = elapsed / estimated, capped at 95%
  const progress = Math.min(Math.round((elapsed / TOTAL_ESTIMATED) * 100), 95);
  const elapsedSec = Math.round(elapsed / 1000);

  return (
    <div className="flex flex-col items-center justify-center py-20 px-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 text-violet-400 text-sm font-medium bg-violet-500/10 border border-violet-500/20 px-4 py-2 rounded-full mb-4">
            <span className="animate-pulse w-2 h-2 bg-violet-400 rounded-full" />
            Running 3-Agent Pipeline
          </div>
          <h2 className="text-2xl font-bold mb-1">Analyzing your paper</h2>
          <p className="text-gray-500 text-sm truncate max-w-sm mx-auto">{fileName}</p>
          <p className="text-gray-600 text-xs mt-1">
            Estimated ~90 seconds · {elapsedSec}s elapsed
          </p>
        </div>

        <div className="space-y-2.5">
          {STEPS.map((step, i) => {
            const isDone = done.includes(i);
            const isActive = active === i && !isDone;
            return (
              <div
                key={i}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-500
                  ${isDone ? "bg-gray-800/60 border-gray-700/40"
                    : isActive ? "bg-violet-500/10 border-violet-500/30"
                    : i < active ? "bg-gray-800/30 border-gray-800/30 opacity-60"
                    : "bg-transparent border-transparent opacity-30"}`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0
                  ${isDone ? "bg-green-500/20 text-green-400"
                    : isActive ? "bg-violet-500/20"
                    : "bg-gray-800 text-gray-600"}`}
                >
                  {isDone ? "✓" : isActive
                    ? <span className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin inline-block" />
                    : step.icon}
                </div>
                <span className={`text-sm font-medium flex-1
                  ${isDone ? "text-green-400" : isActive ? "text-violet-300" : "text-gray-600"}`}>
                  {step.label}
                </span>
                {isDone && <span className="text-xs text-green-600 flex-shrink-0">Done</span>}
                {isActive && (
                  <span className="text-xs text-violet-500 flex-shrink-0">
                    ~{Math.round(step.duration / 1000)}s
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-6">
          <div className="flex justify-between text-xs text-gray-600 mb-1.5">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-500 to-cyan-500 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
