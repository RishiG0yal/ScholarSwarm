import re


def flesch_kincaid(text: str) -> dict:
    if not text or not text.strip():
        return {"score": 0.0, "grade_level": "Unknown", "label": "Unknown"}

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    num_sentences = max(len(sentences), 1)

    words = re.findall(r'\b[a-zA-Z]+\b', text)
    num_words = max(len(words), 1)

    num_syllables = sum(_count_syllables(w) for w in words)

    reading_ease = (
        206.835
        - 1.015 * (num_words / num_sentences)
        - 84.6 * (num_syllables / num_words)
    )
    reading_ease = max(0.0, min(100.0, reading_ease))

    grade = (
        0.39 * (num_words / num_sentences)
        + 11.8 * (num_syllables / num_words)
        - 15.59
    )
    grade = max(1.0, grade)

    return {
        "score": round(reading_ease, 1),
        "grade_level": round(grade, 1),
        "label": _grade_label(reading_ease),
    }


def _count_syllables(word: str) -> int:
    word = word.lower().rstrip("e")
    vowels = re.findall(r'[aeiou]+', word)
    return max(1, len(vowels))


def _grade_label(score: float) -> str:
    if score >= 70:
        return "High School"
    elif score >= 50:
        return "Undergraduate"
    elif score >= 30:
        return "Graduate"
    return "Expert"
