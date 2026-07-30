import os
import base64
import fitz
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150
MAX_FIGURES = 6
MAX_FIGURE_BYTES = 800 * 1024  # 800KB

GEMINI_VISION_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


def extract_and_analyze_figures(file_bytes: bytes, paper_title: str = "") -> list:
    figures = _extract_figures_from_pages(file_bytes)
    if not figures:
        return []

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return [
            {
                "page": f["page"],
                "index": f["index"],
                "ext": "png",
                "description": "Figure analysis unavailable (no Gemini API key).",
                "width": f["width"],
                "height": f["height"],
            }
            for f in figures
        ]

    client = genai.Client(api_key=api_key)
    results = []

    for fig in figures[:MAX_FIGURES]:
        try:
            description = _analyze_with_gemini(client, fig, paper_title)
        except Exception:
            description = "Figure could not be analyzed."

        results.append({
            "page": fig["page"],
            "index": fig["index"],
            "ext": "png",
            "description": description,
            "width": fig["width"],
            "height": fig["height"],
            "base64": fig.get("base64", ""),
        })

    return results


def _extract_figures_from_pages(file_bytes: bytes) -> list:
    """
    Render each page as an image and detect which pages contain figures.
    This captures both raster images AND vector graphics/charts.
    Uses a simple heuristic: pages with large drawing areas likely have figures.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    figures = []
    fig_index = 1

    for page_num, page in enumerate(doc):
        # Check if page has significant drawing content (figures/charts)
        drawings = page.get_drawings()
        images = page.get_images(full=True)

        has_vector_figure = len(drawings) > 20  # pages with many draw commands = figure
        has_raster_image = len(images) > 0

        if not has_vector_figure and not has_raster_image:
            continue

        # Render page at moderate DPI to capture everything
        pix = page.get_pixmap(dpi=120)
        w, h = pix.width, pix.height

        if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
            continue

        img_bytes = pix.tobytes("png")
        if len(img_bytes) > MAX_FIGURE_BYTES:
            # Reduce DPI if too large
            pix = page.get_pixmap(dpi=80)
            img_bytes = pix.tobytes("png")

        if len(img_bytes) > MAX_FIGURE_BYTES:
            continue

        figures.append({
            "page": page_num + 1,
            "index": fig_index,
            "base64": base64.b64encode(img_bytes).decode(),
            "width": pix.width,
            "height": pix.height,
        })
        fig_index += 1

    doc.close()

    # Limit to pages most likely to have actual figures (not just text pages)
    return figures[:MAX_FIGURES]


def _analyze_with_gemini(client: genai.Client, fig: dict, paper_title: str) -> str:
    image_bytes = base64.b64decode(fig["base64"])

    prompt = (
        f"This is page {fig['page']} of a research paper"
        + (f" titled '{paper_title}'" if paper_title else "") + ". "
        "This page contains figures, charts, or diagrams. "
        "Identify and describe the main figure or chart on this page in 2-4 sentences. "
        "Include: the type of visualization, what the axes or components represent, "
        "and the key finding or insight shown. If it's a full text page with no figure, say 'No figure found.'"
    )

    for model_id in GEMINI_VISION_MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt,
                ],
            )
            desc = response.text.strip()
            if "No figure found" in desc:
                return None
            return desc
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
                continue
            raise

    raise Exception("All Gemini vision models quota exhausted.")
