"""
PDF Export Service — Generates downloadable PDF reports from Agent 2 validation results.
Uses fpdf2 for PDF generation with styled sections, tables, and status badges.
"""

import os
import logging
from datetime import datetime

from fpdf import FPDF

from backend.models.schemas import Agent2Output, ValidationStatus

logger = logging.getLogger("rag_pipeline.services.pdf_export")


def _safe_text(text: str) -> str:
    """Sanitize text for FPDF output — replace unsupported characters with ASCII equivalents."""
    if not text:
        return ""

    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": " - ",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "*", "\u25cf": "*",
        "\u00b0": " deg",
        "\u2212": "-",
        "\u2192": "->", "\u2190": "<-",
        "\u2713": "[v]", "\u2717": "[x]",
    }
    for uni, ascii_char in replacements.items():
        text = text.replace(uni, ascii_char)

    # Encode to latin-1, replacing any remaining non-latin-1 characters with ?
    return text.encode("latin-1", errors="replace").decode("latin-1")


class RAGReportPDF(FPDF):
    """Custom PDF class with headers, footers, and RAG report styling."""

    def __init__(self, filename: str, run_id: str):
        super().__init__()
        self.document_name = filename
        self.run_id = run_id
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Analysis of the Papers", align="L")
        self.cell(0, 8, _safe_text(self.document_name), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_pdf_report(
    agent2_output: Agent2Output,
    reports_dir: str,
    run_id: str,
) -> str:
    """
    Generate a comprehensive PDF report from Agent 2's validation results.

    Args:
        agent2_output: Complete validation output from Agent 2.
        reports_dir: Directory to save the PDF.
        run_id: Unique pipeline run identifier.

    Returns:
        Absolute path to the generated PDF file.
    """
    os.makedirs(reports_dir, exist_ok=True)
    pdf_filename = f"Analysis_of_the_Papers_{run_id}.pdf"
    pdf_path = os.path.join(reports_dir, pdf_filename)

    pdf = RAGReportPDF(filename=agent2_output.filename, run_id=run_id)
    pdf.alias_nb_pages()

    # ── Title Page ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(40)

    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 15, "Analysis of the Papers", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, _safe_text(f"Document: {agent2_output.filename}"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    now = datetime.now().strftime("%B %d, %Y at %H:%M")
    pdf.cell(0, 8, f"Generated: {now}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Run ID: {run_id}", align="C", new_x="LMARGIN", new_y="NEXT")

    # Summary box
    pdf.ln(15)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(0, 0, 0)
    box_y = pdf.get_y()
    pdf.rect(30, box_y, 150, 40, style="DF")

    pdf.set_xy(35, box_y + 5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(140, 8, "Summary", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(35, box_y + 15)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(45, 7, f"Total Claims: {agent2_output.total_claims_reviewed}", align="C")
    pdf.cell(45, 7, f"Verified: {agent2_output.verified_count}", align="C")
    pdf.cell(45, 7, f"Flagged: {agent2_output.flagged_count}", align="C")

    pdf.set_xy(35, box_y + 25)
    pdf.cell(140, 7, f"Unsupported: {agent2_output.unsupported_count}", align="C")

    # ── Claims Detail Section ──────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 12, "Detailed Claim Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    for idx, result in enumerate(agent2_output.results):
        claim = result.original_claim
        claim_num = idx + 1

        # Check if we need a new page (leave room for content)
        if pdf.get_y() > 230:
            pdf.add_page()

        # ── Claim Header ──
        status_color = _status_color(result.validation_status)
        pdf.set_fill_color(*status_color)
        pdf.set_draw_color(0, 0, 0)

        header_y = pdf.get_y()
        pdf.rect(10, header_y, 190, 10, style="DF")

        pdf.set_xy(12, header_y + 1)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(255, 255, 255) if result.validation_status != ValidationStatus.VERIFIED else pdf.set_text_color(0, 0, 0)
        status_label = result.validation_status.value.replace("_", " ").upper()
        header_title = _safe_text(f"Claim {claim_num}: [{claim.claim_type.upper()}] - {status_label}")
        pdf.cell(0, 8, header_title)

        pdf.set_y(header_y + 12)
        pdf.set_text_color(0, 0, 0)

        # ── Claim Text ──
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Claim:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _safe_text(claim.claim_text))
        pdf.ln(2)

        # ── Coordinates ──
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(30, 6, "Source: ")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, _safe_text(claim.coordinates), new_x="LMARGIN", new_y="NEXT")

        # ── Verbatim Snippet ──
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Verbatim:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 9)
        pdf.set_fill_color(240, 240, 240)
        snippet = _safe_text(claim.verbatim_snippet[:300])
        pdf.multi_cell(0, 4.5, f'"{snippet}"', fill=True)
        pdf.ln(2)

        # ── Internal Critique ──
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Internal Validation:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _safe_text(result.internal_critique))
        pdf.ln(2)

        # ── Web Consensus ──
        if result.web_consensus:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Web Consensus:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, _safe_text(result.web_consensus))
            pdf.ln(2)

        # ── Modern Updates ──
        if result.modern_updates:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Modern Updates (post-2021):", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, _safe_text(result.modern_updates))
            pdf.ln(2)

        # ── Web Sources ──
        if result.web_findings:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Web Sources ({len(result.web_findings)}):", new_x="LMARGIN", new_y="NEXT")

            for fi, finding in enumerate(result.web_findings[:5]):
                if pdf.get_y() > 260:
                    pdf.add_page()
                pdf.set_font("Helvetica", "", 9)
                support = "Supports" if finding.supports_claim else ("Contradicts" if finding.supports_claim is False else "Neutral")
                pdf.cell(0, 5, _safe_text(f"  [{fi+1}] {finding.source_title[:80]} ({support})"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(0, 0, 180)
                pdf.cell(0, 4, _safe_text(f"      {finding.source_url[:90]}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

        # Separator
        pdf.ln(5)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    # ── Save PDF ──
    pdf.output(pdf_path)
    logger.info(f"PDF report saved: {pdf_path}")
    return pdf_path


def _status_color(status: ValidationStatus) -> tuple[int, int, int]:
    """Return RGB color tuple for validation status badges."""
    if status == ValidationStatus.VERIFIED:
        return (0, 200, 0)  # Green
    elif status == ValidationStatus.DISCREPANCY:
        return (255, 165, 0)  # Orange
    elif status == ValidationStatus.UNSUPPORTED:
        return (220, 50, 50)  # Red
    return (150, 150, 150)  # Gray
