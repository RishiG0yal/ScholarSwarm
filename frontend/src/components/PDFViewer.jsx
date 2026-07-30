import { useState, useEffect, useRef, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import API_BASE from "../config";

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

function highlightPattern(text, pattern) {
  if (!pattern || !text) return text;
  const words = pattern
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(w => w.length > 3);
  if (!words.length) return text;
  const regex = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return text.split(regex).map((part, i) =>
    regex.test(part)
      ? <mark key={i} style={{ backgroundColor: "#fbbf24", color: "#000", borderRadius: "2px", padding: "0 1px" }}>{part}</mark>
      : part
  );
}

export default function PDFViewer({ resultId, totalPages, isOpen, onClose, targetPage, highlightText }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(targetPage || 1);
  const [scale, setScale] = useState(1.2);
  const [pageRendered, setPageRendered] = useState(false);
  const containerRef = useRef(null);
  const pdfUrl = `${API_BASE}/pdf/${resultId}`;

  useEffect(() => {
    if (targetPage) setCurrentPage(targetPage);
  }, [targetPage]);

  useEffect(() => {
    if (!pageRendered || !highlightText || !containerRef.current) return;
    applyHighlight();
  }, [pageRendered, highlightText, currentPage]);

  const applyHighlight = useCallback(() => {
    if (!containerRef.current || !highlightText) return;
    const textLayer = containerRef.current.querySelector(".react-pdf__Page__textContent");
    if (!textLayer) return;

    const spans = textLayer.querySelectorAll("span");
    const searchWords = highlightText
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter(w => w.length > 3);

    let firstMatch = null;
    spans.forEach(span => {
      const text = span.textContent?.toLowerCase() || "";
      const isMatch = searchWords.some(word => text.includes(word));
      if (isMatch) {
        span.style.backgroundColor = "rgba(251,191,36,0.5)";
        span.style.borderRadius = "2px";
        span.style.outline = "1px solid rgba(251,191,36,0.8)";
        if (!firstMatch) firstMatch = span;
      } else {
        span.style.backgroundColor = "";
        span.style.outline = "";
      }
    });

    if (firstMatch) {
      firstMatch.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightText]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  const onPageRenderSuccess = () => {
    setPageRendered(true);
    setTimeout(applyHighlight, 100);
  };

  const goToPage = (page) => {
    const clamped = Math.max(1, Math.min(page, numPages || totalPages));
    setCurrentPage(clamped);
    setPageRendered(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      <div className="w-full max-w-2xl bg-gray-900 border-l border-gray-700 flex flex-col h-full shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-gray-200">📄 PDF Viewer</span>
            {highlightText && (
              <span className="text-xs bg-yellow-500/20 border border-yellow-500/30 text-yellow-300 px-2 py-0.5 rounded-full">
                🔍 Highlighting source
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors text-lg">✕</button>
        </div>

        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-950/40 flex-shrink-0">
          <div className="flex items-center gap-2">
            <button onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1}
              className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 disabled:opacity-40 rounded-lg">←</button>
            <div className="flex items-center gap-1">
              <input type="number" value={currentPage} min={1} max={numPages || totalPages}
                onChange={(e) => goToPage(parseInt(e.target.value) || 1)}
                className="w-12 text-center text-xs bg-gray-800 border border-gray-700 rounded px-1 py-1 text-gray-200 focus:outline-none focus:border-violet-500" />
              <span className="text-xs text-gray-500">/ {numPages || totalPages}</span>
            </div>
            <button onClick={() => goToPage(currentPage + 1)} disabled={currentPage >= (numPages || totalPages)}
              className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 disabled:opacity-40 rounded-lg">→</button>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => setScale(s => Math.max(0.6, s - 0.2))} className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded-lg">−</button>
            <span className="text-xs text-gray-500 w-10 text-center">{Math.round(scale * 100)}%</span>
            <button onClick={() => setScale(s => Math.min(2.5, s + 0.2))} className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded-lg">+</button>
          </div>
        </div>

        {highlightText && (
          <div className="px-4 py-2 bg-yellow-500/10 border-b border-yellow-500/20 flex-shrink-0">
            <p className="text-xs text-yellow-300 leading-relaxed">
              <span className="font-semibold">🔍 Looking for: </span>
              <span className="italic">"{highlightText.slice(0, 120)}{highlightText.length > 120 ? "…" : ""}"</span>
            </p>
          </div>
        )}

        <div ref={containerRef} className="flex-1 overflow-auto flex justify-center bg-gray-950 py-4">
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            loading={
              <div className="flex items-center justify-center py-20 text-gray-500">
                <span className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mr-2" />
                Loading PDF...
              </div>
            }
            error={
              <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                <span className="text-3xl mb-3">⚠️</span>
                <p className="text-sm">Could not load PDF.</p>
                <p className="text-xs mt-1">PDF viewer requires a real upload (not demo mode).</p>
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={false}
              onRenderSuccess={onPageRenderSuccess}
              className="shadow-2xl"
            />
          </Document>
        </div>

        <div className="px-4 py-2 border-t border-gray-800 flex-shrink-0">
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-xs text-gray-600 mr-1">Jump:</span>
            {Array.from({ length: Math.min(numPages || totalPages, 15) }, (_, i) => i + 1).map(p => (
              <button key={p} onClick={() => goToPage(p)}
                className={`text-xs px-1.5 py-0.5 rounded transition-colors ${currentPage === p ? "bg-violet-600 text-white" : "bg-gray-800 hover:bg-gray-700 text-gray-400"}`}>
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
