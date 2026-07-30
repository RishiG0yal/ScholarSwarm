import os
import re
import base64
import fitz
from dotenv import load_dotenv

load_dotenv()

GEMINI_VISION_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


def extract_equations(file_bytes: bytes) -> list:
    text_equations = _extract_inline_equations(file_bytes)
    gemini_equations = _extract_via_gemini(file_bytes)
    seen = {eq["latex"] for eq in text_equations}
    for eq in gemini_equations:
        if eq["latex"] not in seen:
            text_equations.append(eq)
            seen.add(eq["latex"])
    return text_equations[:15]


def _extract_inline_equations(file_bytes: bytes) -> list:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    equations = []
    patterns = [
        r'\$\$[^$]{4,}\$\$',                          # $$block math$$ (min 4 chars)
        r'\$[^$]{4,}\$',                               # $inline math$ (min 4 chars)
        r'\\begin\{equation\}.*?\\end\{equation\}',    # LaTeX equation environment
        r'\\begin\{align\}.*?\\end\{align\}',          # LaTeX align environment
        # Tightened: requires operator AND number/variable on both sides
        r'[A-Za-z_]\w*\s*=\s*(?:[\d\.\-]+|\\[a-zA-Z]+|\w+\s*[\+\-\*\/\^]\s*\w+)',
    ]
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        seen_on_page = set()
        for pattern in patterns:
            for match in re.findall(pattern, text, re.DOTALL):
                cleaned = match.strip()
                # Skip if too short, too long, or pure prose
                if len(cleaned) < 4 or len(cleaned) > 300:
                    continue
                if cleaned in seen_on_page:
                    continue
                # Skip if it looks like prose (contains common words)
                lower = cleaned.lower()
                if any(word in lower for word in [" the ", " and ", " with ", " for ", " that ", " this "]):
                    continue
                seen_on_page.add(cleaned)
                equations.append({
                    "page": page_num + 1,
                    "latex": cleaned,
                    "description": "",
                    "source": "regex",
                })
    doc.close()
    return equations[:10]


def _extract_via_gemini(file_bytes: bytes) -> list:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return []

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return []

    client = genai.Client(api_key=api_key)
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    equations = []

    for page_num in range(min(4, len(doc))):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")

        prompt = (
            f"This is page {page_num + 1} of a research paper. "
            "Find all mathematical equations on this page. "
            "For each equation return exactly two lines:\n"
            "LATEX: <the equation in LaTeX>\n"
            "DESC: <one sentence explaining what this equation represents>\n"
            "Separate each equation with ---\n"
            "If no equations are present, return NONE."
        )

        for model_id in GEMINI_VISION_MODELS:
            try:
                from google.genai import types as gtypes
                response = client.models.generate_content(
                    model=model_id,
                    contents=[
                        gtypes.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                        prompt,
                    ],
                )
                raw = response.text.strip()
                if not raw or raw.upper() == "NONE":
                    break

                for block in raw.split("---"):
                    block = block.strip()
                    if not block:
                        continue
                    latex = ""
                    desc = ""
                    for line in block.splitlines():
                        if line.startswith("LATEX:"):
                            latex = line[6:].strip()
                        elif line.startswith("DESC:"):
                            desc = line[5:].strip()
                    if latex and len(latex) > 3:
                        equations.append({
                            "page": page_num + 1,
                            "latex": latex,
                            "description": desc,
                            "source": "gemini",
                        })
                break
            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
                    continue
                break

    doc.close()
    return equations
