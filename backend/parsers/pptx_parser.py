import io
from pptx import Presentation


def extract_text_from_pptx(file_bytes: bytes) -> dict:
    prs = Presentation(io.BytesIO(file_bytes))
    pages = {}
    full_text = ""

    for i, slide in enumerate(prs.slides):
        slide_text = ""
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        slide_text += text + "\n"
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes and notes != "Click to edit Master text styles":
                slide_text += f"\n[Speaker Notes: {notes}]\n"
        pages[i + 1] = slide_text
        full_text += slide_text + "\n"

    title = "Unknown Title"
    authors = "Unknown Authors"
    if prs.slides:
        texts = []
        for shape in prs.slides[0].shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    texts.append(t)
        if texts:
            title = texts[0]
        if len(texts) > 1:
            authors = texts[1]

    return {
        "pages": pages,
        "full_text": full_text.strip(),
        "title": title,
        "authors": authors,
        "total_pages": len(prs.slides),
        "file_type": "pptx",
    }
