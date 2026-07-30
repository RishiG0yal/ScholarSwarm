import { useState, useRef, useEffect } from "react";

export default function FlashCard({ front, back, index }) {
  const [flipped, setFlipped] = useState(false);
  const [height, setHeight] = useState(120);
  const frontRef = useRef(null);
  const backRef = useRef(null);

  useEffect(() => {
    const fh = frontRef.current?.scrollHeight || 0;
    const bh = backRef.current?.scrollHeight || 0;
    setHeight(Math.max(fh, bh, 120));
  }, [front, back]);

  return (
    <div
      className="flashcard-container cursor-pointer select-none w-full"
      style={{ height }}
      onClick={() => setFlipped(!flipped)}
    >
      <div
        className={`flashcard-inner ${flipped ? "flipped" : ""}`}
        style={{ height }}
      >
        {/* Front */}
        <div
          ref={frontRef}
          className="flashcard-face flashcard-front bg-gray-900/80 border border-gray-700 rounded-xl p-4 flex flex-col gap-2"
          style={{ height }}
        >
          <div className="flex items-center justify-between flex-shrink-0">
            <span className="text-xs text-violet-400 font-medium bg-violet-500/10 px-2 py-0.5 rounded-full">
              Q {index + 1}
            </span>
            <span className="text-xs text-gray-600">tap to flip →</span>
          </div>
          <p className="text-gray-200 text-sm font-medium leading-relaxed">{front}</p>
        </div>

        {/* Back */}
        <div
          ref={backRef}
          className="flashcard-face flashcard-back bg-violet-900/30 border border-violet-700/40 rounded-xl p-4 flex flex-col gap-2"
          style={{ height }}
        >
          <div className="flex items-center justify-between flex-shrink-0">
            <span className="text-xs text-cyan-400 font-medium bg-cyan-500/10 px-2 py-0.5 rounded-full">
              A {index + 1}
            </span>
            <span className="text-xs text-gray-600">← tap to flip</span>
          </div>
          <p className="text-gray-200 text-sm leading-relaxed">{back}</p>
        </div>
      </div>
    </div>
  );
}
