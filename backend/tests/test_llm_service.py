import unittest
from unittest.mock import AsyncMock, patch

from models.schemas import ExtractionResult
from services.llm import LLMService


class LLMServiceStructuredParsingTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_structured_accepts_parsed_payloads(self):
        llm = LLMService()
        parsed_payload = {
            "claims": [
                {
                    "claim": "The model achieved 92% accuracy.",
                    "type": "finding",
                    "page": 3,
                    "chunk_id": "chunk_1",
                    "confidence": "high",
                    "is_conflicting": False,
                }
            ]
        }

        with patch.object(llm, "generate", AsyncMock(return_value=parsed_payload)):
            result = await llm.generate_structured(
                prompt="extract claims",
                response_model=ExtractionResult,
            )

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(len(result.claims), 1)
        self.assertEqual(result.claims[0].claim, "The model achieved 92% accuracy.")


if __name__ == "__main__":
    unittest.main()
