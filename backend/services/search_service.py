"""
Unified Search Service — Async client supporting Tavily and SerpAPI.
Enforces temporal filtering (post-cutoff year) and academic domain prioritization.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger("rag_pipeline.services.search")


class SearchService:
    """Unified search client supporting Tavily and SerpAPI."""

    # Academic and authoritative domains to prioritize
    PRIORITY_DOMAINS = [
        "pubmed.ncbi.nlm.nih.gov",
        "arxiv.org",
        "scholar.google.com",
        "nature.com",
        "sciencedirect.com",
        "springer.com",
        "wiley.com",
        "ncbi.nlm.nih.gov",
    ]

    def __init__(self, provider: str, api_key: str, cutoff_year: int = 2021):
        self.provider = provider.strip().lower()
        self.api_key = api_key.strip().strip('"').strip("'")
        self.cutoff_year = cutoff_year
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict]:
        """
        Execute a constrained web search for a specific claim.

        Args:
            query: The search query (derived from a specific claim).
            max_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: title, url, snippet, domain, published_date
        """
        # Append temporal filter to query
        temporal_query = f"{query} after:{self.cutoff_year}"

        if self.provider == "serpapi":
            return await self._search_serpapi(temporal_query, max_results)
        else:
            return await self._search_tavily(temporal_query, max_results)

    async def _search_tavily(self, query: str, max_results: int) -> list[dict]:
        """Search using Tavily AI Search API."""
        client = await self._get_client()

        body = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_domains": self.PRIORITY_DOMAINS,
            "include_answer": False,
        }

        logger.info(f"Tavily search → '{query[:80]}...'")

        try:
            resp = await client.post(
                "https://api.tavily.com/search",
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", []):
                domain = _extract_domain(item.get("url", ""))
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:500],
                    "domain": domain,
                    "published_date": item.get("published_date"),
                })

            logger.info(f"Tavily ← {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily API error: {e.response.status_code} — {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    async def _search_serpapi(self, query: str, max_results: int) -> list[dict]:
        """Search using SerpAPI (Google search results)."""
        client = await self._get_client()

        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "num": max_results,
            "gl": "us",
            "hl": "en",
        }

        logger.info(f"SerpAPI search → '{query[:80]}...'")

        try:
            resp = await client.get(
                "https://serpapi.com/search.json",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("organic_results", []):
                domain = _extract_domain(item.get("link", ""))
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")[:500],
                    "domain": domain,
                    "published_date": item.get("date"),
                })

            logger.info(f"SerpAPI ← {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"SerpAPI error: {e.response.status_code} — {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []


def _extract_domain(url: str) -> str:
    """Extract domain from a URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def create_search_service(
    provider: str, api_key: str, cutoff_year: int = 2021
) -> SearchService:
    """Factory function to create a search service instance."""
    if not api_key:
        raise ValueError(f"API key is required for search provider '{provider}'")
    return SearchService(provider=provider, api_key=api_key, cutoff_year=cutoff_year)
