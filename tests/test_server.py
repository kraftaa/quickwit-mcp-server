import unittest
from unittest.mock import AsyncMock, patch

from quickwit_mcp import server


class TailToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tail_defaults_to_timestamp_desc_sort(self) -> None:
        with patch("quickwit_mcp.server._search_raw", new=AsyncMock(return_value={"hits": []})) as mocked:
            await server.tail(index_id="logs", n=3, query="*")
            mocked.assert_awaited_once_with(
                index_id="logs",
                query="*",
                start_timestamp=None,
                end_timestamp=None,
                max_hits=3,
                sort_by="-timestamp_nanos",
            )

    async def test_tail_respects_explicit_sort(self) -> None:
        with patch("quickwit_mcp.server._search_raw", new=AsyncMock(return_value={"hits": []})) as mocked:
            await server.tail(index_id="logs", n=5, query="severity_text:ERROR", sort_by="-timestamp")
            mocked.assert_awaited_once_with(
                index_id="logs",
                query="severity_text:ERROR",
                start_timestamp=None,
                end_timestamp=None,
                max_hits=5,
                sort_by="-timestamp",
            )

    async def test_tail_rejects_non_positive_n(self) -> None:
        with self.assertRaisesRegex(ValueError, "n must be > 0"):
            await server.tail(index_id="logs", n=0)


class PatternNormalizationTests(unittest.TestCase):
    def test_strip_ids_normalizes_dynamic_identifiers(self) -> None:
        raw = (
            "request 550e8400-e29b-41d4-a716-446655440000 failed for "
            "abcdef0123456789 on build 12345"
        )
        normalized = server._normalize_pattern(raw, strip_ids=True)
        self.assertEqual(
            normalized,
            "request <UUID> failed for <ID> on build <N>",
        )


if __name__ == "__main__":
    unittest.main()
