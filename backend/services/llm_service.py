"""
Unified LLM Service — Async client supporting Groq and Google Gemini.
Provides a consistent interface for both agents regardless of the underlying provider.
"""

import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger("rag_pipeline.services.llm")


def _extract_wait_time(resp: Optional[httpx.Response], fallback: float) -> float:
    """Extract wait seconds from HTTP response headers or JSON error message."""
    if not resp:
        return fallback

    # 1. Check Retry-After header
    retry_after = resp.headers.get("retry-after")
    if retry_after:
        try:
            return float(retry_after) + 1.0
        except ValueError:
            pass

    # 2. Parse "try again in X.Xs" from Groq JSON response
    try:
        data = resp.json()
        msg = data.get("error", {}).get("message", "")
        import re
        match = re.search(r"try again in (\d+\.?\d*)s", msg, re.IGNORECASE)
        if match:
            return float(match.group(1)) + 1.5
    except Exception:
        pass

    return fallback


class LLMService:
    """Unified LLM client supporting Groq and Gemini providers."""

    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider.strip().lower()
        self.api_key = api_key.strip().strip('"').strip("'")
        self.model = model.strip().strip('"').strip("'")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> str:
        if self.provider == "gemini":
            return await self._generate_gemini(
                system_prompt, user_prompt, temperature, max_tokens, response_format
            )
        else:
            return await self._generate_groq(
                system_prompt, user_prompt, temperature, max_tokens, response_format
            )

    async def _generate_groq(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        """Call Groq's OpenAI-compatible chat completions API with smart 429 retry."""
        client = await self._get_client()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            body["response_format"] = {"type": "json_object"}

        max_retries = 6
        for attempt in range(max_retries):
            try:
                logger.info(f"Groq request (attempt {attempt + 1}/{max_retries}) → model={self.model}")
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=body,
                )

                if resp.status_code == 429 and attempt < max_retries - 1:
                    wait_sec = _extract_wait_time(resp, fallback=(attempt + 1) * 5.0)
                    logger.warning(
                        f"Groq 429 Rate Limit hit. Waiting {wait_sec:.1f}s before retry (attempt {attempt + 1}/{max_retries})..."
                    )
                    import asyncio
                    await asyncio.sleep(wait_sec)
                    continue

                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(
                    f"Groq response ← tokens={data.get('usage', {}).get('total_tokens', '?')}"
                )
                return content

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_sec = _extract_wait_time(e.response, fallback=(attempt + 1) * 5.0)
                    logger.warning(
                        f"Groq 429 Rate Limit exception. Waiting {wait_sec:.1f}s before retry (attempt {attempt + 1}/{max_retries})..."
                    )
                    import asyncio
                    await asyncio.sleep(wait_sec)
                    continue
                logger.error(f"Groq API error: {e.response.status_code} — {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Groq request failed: {e}")
                raise

    async def _generate_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        """Call Google Gemini's generateContent API."""
        client = await self._get_client()

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

        body: dict = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if response_format == "json":
            body["generationConfig"]["responseMimeType"] = "application/json"

        logger.info(f"Gemini request → model={self.model}")

        try:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.info("Gemini response ← OK")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API error: {e.response.status_code} — {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            raise


def create_llm_service(provider: str, api_key: str, model: str) -> LLMService:
    """Factory function to create an LLM service instance."""
    if not api_key:
        raise ValueError(f"API key is required for LLM provider '{provider}'")
    return LLMService(provider=provider, api_key=api_key, model=model)
