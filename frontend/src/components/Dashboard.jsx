import { useState } from "react";
import PaperHeader from "./PaperHeader";
import SummaryCard from "./SummaryCard";
import ClaimCard from "./ClaimCard";
import LimitationsCard from "./LimitationsCard";
import FlashCard from "./FlashCard";
import TableViewer from "./TableViewer";
import FigureCard from "./FigureCard";
import SimilarPapers from "./SimilarPapers";
import AskPaper from "./AskPaper";
import ExportButton from "./ExportButton";
import ShareButton from "./ShareButton";

// Lazy load heavy components to prevent crashes from killing entire page
import { Suspense, lazy } from "react";
const ContextMapGraph = lazy(() => import("./ContextMapGraph"));
const CitationGraph = lazy(() => import("./CitationGraph"));
const PDFViewer = lazy(() => import("./PDFViewer"));
const CompareMode = lazy(() => import("./CompareMode"));

function SafeComponent({ children, fallback = null }) {
  try {
    return children;
  } catch {
    return fallback;
  }
}

export default function Dashboard({ data, fileName }) {
  const [pdfOpen, setPdfOpen] = useState(false);
  const [pdfPage, setPdfPage] = useState(1);
  const [pdfHighlight, setPdfHighlight] = useState(null);
  const [compareOpen, setCompareOpen] = useState(false);

  const isDemo = data.result_id === "demo1234";

  const handlePageClick = (page, sourceQuote) => {
    if (isDemo) return;
    setPdfPage(page);
    setPdfHighlight(sourceQuote || null);
    setPdfOpen(true);
  };

  return (
    <div className="space-y-6">
      <PaperHeader data={data} fileName={fileName} />

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        <ExportButton data={data} />
        <ShareButton resultId={data.result_id} />
        {!isDemo && (
          <button
            onClick={() => setPdfOpen(true)}
            className="flex items-center gap-2 text-sm px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-gray-300 transition-all"
          >
            📄 View PDF
          </button>
        )}
        <button
          onClick={() => setCompareOpen(true)}
          className="flex items-center gap-2 text-sm px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-gray-300 transition-all"
        >
          ⚖️ Compare Papers
        </button>
      </div>

      {/* Summary */}
      <SummaryCard
        summary={data.summary}
        eli5Summary={data.eli5_summary}
        readingLevel={data.reading_level}
        readabilityScore={data.readability_score}
      />

      {/* Claims */}
      {data.claims?.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Core Claims · {data.verified_count} verified · {data.flagged_count} flagged
            {!isDemo && <span className="text-gray-600 font-normal ml-2 text-xs">· Click page number to open PDF</span>}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.claims.map((claim, i) => (
              <ClaimCard
                key={i}
                claim={claim}
                onPageClick={!isDemo ? handlePageClick : null}
              />
            ))}
          </div>
        </section>
      )}

      {/* Limitations */}
      {data.limitations?.length > 0 && <LimitationsCard limitations={data.limitations} />}

      {/* Context Map */}
      <Suspense fallback={<div className="h-32 bg-gray-900/40 rounded-2xl border border-gray-800 flex items-center justify-center text-gray-600 text-sm">Loading Context Map...</div>}>
        <ContextMapGraph data={data} />
      </Suspense>

      {/* Flashcards + Key Terms col */}
      {data.flashcards?.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Study Flashcards
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.flashcards.map((card, i) => (
              <FlashCard key={i} front={card.front} back={card.back} index={i} />
            ))}
          </div>
        </section>
      )}

      {/* Tables */}
      {data.tables?.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Extracted Tables ({data.tables.length})
          </h2>
          <div className="space-y-4">
            {data.tables.map((table, i) => <TableViewer key={i} table={table} />)}
          </div>
        </section>
      )}

      {/* Figures */}
      {data.figures?.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Figures & Charts ({data.figures.length})
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {data.figures.map((fig, i) => <FigureCard key={i} figure={fig} />)}
          </div>
        </section>
      )}

      {/* Ask the Paper */}
      <AskPaper resultId={data.result_id} title={data.title} />

      {/* Citation Graph */}
      <Suspense fallback={null}>
        <CitationGraph title={data.title} citations={data.citations} />
      </Suspense>

      {/* Similar Papers */}
      <SimilarPapers title={data.title} />

      {/* PDF Viewer Drawer */}
      {!isDemo && pdfOpen && (
        <Suspense fallback={null}>
          <PDFViewer
            resultId={data.result_id}
            totalPages={data.total_pages}
            isOpen={pdfOpen}
            onClose={() => setPdfOpen(false)}
            targetPage={pdfPage}
            highlightText={pdfHighlight}
          />
        </Suspense>
      )}

      {/* Compare Mode */}
      {compareOpen && (
        <Suspense fallback={null}>
          <CompareMode
            primaryData={data}
            onClose={() => setCompareOpen(false)}
          />
        </Suspense>
      )}
    </div>
  );
}
