import httpx

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,citationCount,url"
TIMEOUT = 8.0


async def find_similar_papers(title: str, limit: int = 5) -> list:
    if not title or title == "Unknown Title":
        return []

    safe_title = title[:200].strip()
    params = {"query": safe_title, "fields": FIELDS, "limit": limit + 2}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/paper/search", params=params)
            if resp.status_code != 200:
                return []

            papers = resp.json().get("data", [])
            results = []

            for paper in papers:
                p_title = paper.get("title", "")
                if _titles_match(p_title, title):
                    continue

                authors = paper.get("authors", [])
                author_str = ", ".join(a.get("name", "") for a in authors[:3])
                if len(authors) > 3:
                    author_str += " et al."

                semantic_id = paper.get("paperId", "")
                url = paper.get("url") or (
                    f"https://www.semanticscholar.org/paper/{semantic_id}"
                    if semantic_id else "#"
                )

                results.append({
                    "title": p_title,
                    "authors": author_str,
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "url": url,
                })

                if len(results) >= limit:
                    break

            return results
    except Exception:
        return []


def _titles_match(t1: str, t2: str) -> bool:
    clean = lambda s: s.lower().strip().replace(" ", "")
    return clean(t1) == clean(t2) or clean(t1) in clean(t2) or clean(t2) in clean(t1)
