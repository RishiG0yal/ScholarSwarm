import io
import re
import pdfplumber

MAX_ROWS_PER_TABLE = 50
MAX_CELL_LENGTH = 150
MIN_USEFUL_COLS = 2
MAX_AVG_CELL_LEN = 80
MAX_CELL_LEN_THRESHOLD = 200


def extract_tables_from_pdf(file_bytes: bytes) -> list:
    tables = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for t_idx, raw_table in enumerate(page.extract_tables()):
                    result = _process_table(raw_table, page_num, t_idx)
                    if result:
                        tables.append(result)
    except Exception:
        return []
    return tables


def _process_table(table, page_num: int, t_idx: int) -> dict | None:
    if not table or len(table) < 2:
        return None

    headers = [_clean_cell(c) for c in table[0]]

    # Need at least 2 non-empty columns
    non_empty_headers = [h for h in headers if h]
    if len(non_empty_headers) < MIN_USEFUL_COLS and len(headers) < MIN_USEFUL_COLS:
        return None

    # Skip if any header looks like prose or code
    for h in headers:
        if len(h) > 80:
            return None
        if _looks_like_code_or_prose(h):
            return None

    rows = []
    all_cells = []
    for row in table[1:MAX_ROWS_PER_TABLE + 1]:
        cleaned = [_clean_cell(c) for c in row]
        if any(cleaned):
            rows.append(cleaned)
            all_cells.extend([c for c in cleaned if c])

    if not rows:
        return None

    # Require at least 30% of cells to have content
    total_cells = sum(len(row) for row in rows)
    filled_cells = sum(1 for row in rows for c in row if c.strip())
    if total_cells > 0 and filled_cells / total_cells < 0.3:
        return None

    # Reject tables where cells contain code or long prose
    if all_cells:
        avg_len = sum(len(c) for c in all_cells) / len(all_cells)
        max_len = max(len(c) for c in all_cells)

        if avg_len > MAX_AVG_CELL_LEN:
            return None
        if max_len > MAX_CELL_LEN_THRESHOLD:
            return None

        # Reject if any cell looks like code or conversation
        for cell in all_cells:
            if _looks_like_code_or_prose(cell):
                return None

    return {
        "page": page_num + 1,
        "table_index": t_idx + 1,
        "headers": headers,
        "rows": rows,
        "raw_markdown": _to_markdown(headers, rows),
    }


def _looks_like_code_or_prose(text: str) -> bool:
    if not text:
        return False
    # Code indicators
    code_patterns = [
        r'def\s+\w+\s*\(',
        r'import\s+\w+',
        r'print\s*\(',
        r'#\s+\w+',
        r'\bfor\s+\w+\s+in\b',
        r'\bif\s+\w+.*:',
        r'<think>',
        r'</think>',
        r'<answer>',
        r'Step\d+\)',
        r'\(Step\d+\)',
    ]
    for pattern in code_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    # Long text without any numbers or short tokens = probably prose
    words = text.split()
    if len(words) > 15 and not any(c.isdigit() for c in text):
        return True
    return False


def _clean_cell(cell) -> str:
    if not cell:
        return ""
    text = str(cell).strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > MAX_CELL_LENGTH:
        text = text[:MAX_CELL_LENGTH] + "..."
    return text


def _to_markdown(headers: list, rows: list) -> str:
    if not headers:
        return ""
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    header_row = "| " + " | ".join(headers) + " |"
    data_rows = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_row, separator] + data_rows)
