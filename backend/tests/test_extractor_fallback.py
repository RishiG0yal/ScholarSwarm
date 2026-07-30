import unittest
from unittest.mock import AsyncMock, patch

from models.schemas import Chunk
from pipeline.extractor import extract_claims
from services.llm import MissingApiKeyError


class ExtractorFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_claims_falls_back_when_api_key_missing(self):
        chunks = [
            Chunk(
                chunk_id="chunk-1",
                text="This study found that the new method improved accuracy by 12%. The authors note a limitation in the small sample size.",
                page_number=2,
                section_guess="Methods",
            )
        ]

        with patch(
            "pipeline.extractor.llm_service.generate_structured",
            new=AsyncMock(side_effect=MissingApiKeyError("missing api key")),
        ):
            claims = await extract_claims(chunks, is_short_paper=True)

        self.assertTrue(claims)
        self.assertEqual(claims[0].chunk_id, "chunk-1")
        self.assertEqual(claims[0].page, 2)


if __name__ == "__main__":
    unittest.main()
