import PaperHeader from "./PaperHeader";
import SummaryCard from "./SummaryCard";
import ClaimCard from "./ClaimCard";
import LimitationsCard from "./LimitationsCard";
import FlashCard from "./FlashCard";
import ConceptMap from "./ConceptMap";
import TableViewer from "./TableViewer";
import FigureCard from "./FigureCard";
import SimilarPapers from "./SimilarPapers";
import AskPaper from "./AskPaper";
import ExportButton from "./ExportButton";
import ShareButton from "./ShareButton";

export default function Dashboard({ data, fileName }) {
  return (
    <div className="space-y-6">
      <PaperHeader data={data} fileName={fileName} />

      <div className="flex flex-wrap gap-3">
        <ExportButton data={data} />
        <ShareButton resultId={data.result_id} />
      </div>

      <SummaryCard
        summary={data.summary}
        eli5Summary={data.eli5_summary}
        readingLevel={data.reading_level}
        readabilityScore={data.readability_score}
      />

      {data.claims?.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Core Claims · {data.verified_count} verified · {data.flagged_count} flagged
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.claims.map((claim, i) => <ClaimCard key={i} claim={claim} />)}
          </div>
        </section>
      )}

      {data.limitations?.length > 0 && <LimitationsCard limitations={data.limitations} />}

      <div className="grid gap-6 lg:grid-cols-2">
        {data.flashcards?.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Study Flashcards
            </h2>
            <div className="space-y-3">
              {data.flashcards.map((card, i) => (
                <FlashCard key={i} front={card.front} back={card.back} index={i} />
              ))}
            </div>
          </section>
        )}
        {data.key_terms?.length > 0 && <ConceptMap terms={data.key_terms} title={data.title} />}
      </div>

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

      {data.figures?.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Figures & Charts ({data.figures.length})
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.figures.map((fig, i) => <FigureCard key={i} figure={fig} />)}
          </div>
        </section>
      )}

      <AskPaper resultId={data.result_id} title={data.title} />
      <SimilarPapers title={data.title} />
    </div>
  );
}
