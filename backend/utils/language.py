"""
PaperVerify — Language detection utility.
"""
from langdetect import detect, DetectorFactory, LangDetectException

# Make detection deterministic
DetectorFactory.seed = 0


def detect_language(text: str) -> tuple[str, bool]:
    """
    Detect the language of the given text.

    Returns:
        (language_code, is_english) — e.g. ("en", True) or ("fr", False)
    """
    if not text or len(text.strip()) < 50:
        # Too little text to detect reliably
        return "en", True

    try:
        # Use the first ~5000 chars for detection
        sample = text[:5000]
        lang = detect(sample)
        return lang, lang == "en"
    except LangDetectException:
        # If detection fails, assume English
        return "en", True
