"""
PaperVerify — Gemini LLM service with retry, timeout, and structured output.
"""
import asyncio
import json
import re
import time
from typing import Type

from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, ValidationError

from config import GEMINI_API_KEY, GEMINI_MODEL, AGENT_TIMEOUT_SECONDS, AGENT_MAX_RETRIES
from utils.logging_util import logger


class AgentError(Exception):
    """Raised when an agent call fails for non-timeout reasons."""
    pass


class AgentTimeoutError(Exception):
    """Raised when an agent call exceeds the timeout after retries."""
    pass


class MissingApiKeyError(AgentError):
    """Raised when the Gemini API key is missing."""
    pass


class LLMService:
    """Wrapper around the Gemini API with retry and timeout logic."""

    def __init__(self):
        self._client = None
        self._call_timestamps: list[float] = []

    @property
    def client(self) -> genai.Client:
        """Lazy-init the Gemini client."""
        if self._client is None:
            if not GEMINI_API_KEY:
                raise MissingApiKeyError(
                    "GEMINI_API_KEY not set. Please add it to backend/.env "
                    "(get a free key from https://aistudio.google.com/)"
                )
            self._client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info(f"Gemini client initialized (model: {GEMINI_MODEL})")
        return self._client

    async def _rate_limit(self):
        """Simple rate limiter: max 25 requests per minute."""
        now = time.time()
        # Remove timestamps older than 60 seconds
        self._call_timestamps = [t for t in self._call_timestamps if now - t < 60]
        if len(self._call_timestamps) >= 25:
            wait_time = 60 - (now - self._call_timestamps[0])
            if wait_time > 0:
                logger.info(f"Rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        self._call_timestamps.append(time.time())

    async def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Type[BaseModel] | None = None,
    ) -> str:
        """
        Call Gemini with retry and timeout.

        Args:
            prompt: The user prompt content.
            system_instruction: System-level instructions for the model.
            response_schema: Optional Pydantic model to enforce structured JSON output.

        Returns:
            The model's response text.

        Raises:
            AgentTimeoutError: If the call times out after retries.
            AgentError: If the call fails for other reasons.
        """
        await self._rate_limit()

        config_kwargs = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if response_schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = GenerateContentConfig(**config_kwargs) if config_kwargs else None

        last_error = None
        for attempt in range(1 + AGENT_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=AGENT_TIMEOUT_SECONDS,
                )

                if response is None:
                    raise AgentError("Empty response from Gemini API")

                parsed_payload = getattr(response, "parsed", None)
                if parsed_payload is not None:
                    if isinstance(parsed_payload, BaseModel):
                        return parsed_payload.model_dump_json()
                    if isinstance(parsed_payload, (dict, list)):
                        return json.dumps(parsed_payload)

                response_text = getattr(response, "text", None)
                if response_text:
                    return response_text

                raise AgentError("Empty response from Gemini API")

            except asyncio.TimeoutError:
                last_error = AgentTimeoutError(
                    f"Gemini API call timed out after {AGENT_TIMEOUT_SECONDS}s "
                    f"(attempt {attempt + 1}/{1 + AGENT_MAX_RETRIES})"
                )
                logger.warning(str(last_error))

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    logger.warning(f"Rate limited by API, waiting 10s...")
                    await asyncio.sleep(10)
                    last_error = e
                    continue

                if attempt < AGENT_MAX_RETRIES:
                    logger.warning(f"Gemini API error (attempt {attempt + 1}): {e}")
                    last_error = e
                    await asyncio.sleep(2)
                else:
                    raise AgentError(f"Gemini API failed: {e}") from e

        if isinstance(last_error, AgentTimeoutError):
            raise last_error
        raise AgentError(f"Gemini API failed after retries: {last_error}")

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        system_instruction: str = "",
    ) -> BaseModel:
        """
        Call Gemini and parse the response into a Pydantic model.

        Returns:
            An instance of the response_model.
        """
        raw = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=response_model,
        )

        if isinstance(raw, response_model):
            return raw

        if isinstance(raw, BaseModel):
            return raw

        if isinstance(raw, dict):
            return response_model.model_validate(raw)

        if isinstance(raw, (list, tuple)):
            return response_model.model_validate(raw)

        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")

        if isinstance(raw, str):
            text = raw.strip()
            if text.startswith("```"):
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
                if match:
                    text = match.group(1).strip()

            try:
                return response_model.model_validate_json(text)
            except ValidationError:
                try:
                    parsed = json.loads(text)
                    return response_model.model_validate(parsed)
                except (json.JSONDecodeError, ValidationError) as exc:
                    raise AgentError(
                        f"Could not parse structured LLM response as {response_model.__name__}: {exc}"
                    ) from exc

        raise AgentError(
            f"Unsupported structured LLM response type: {type(raw).__name__}"
        )


# Global singleton
llm_service = LLMService()
