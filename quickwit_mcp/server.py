import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

QUICKWIT_URL = os.environ.get("QUICKWIT_URL", "http://localhost:7280").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("QUICKWIT_HTTP_TIMEOUT", "30"))

mcp = FastMCP(
    "quickwit",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_PORT", "3020")),
)

_client = httpx.AsyncClient(base_url=QUICKWIT_URL, timeout=HTTP_TIMEOUT)


@mcp.tool()
async def list_indexes() -> list[dict[str, Any]]:
    """List all Quickwit indexes on this cluster."""
    r = await _client.get("/api/v1/indexes")
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def describe_index(index_id: str) -> dict[str, Any]:
    """Return metadata for a Quickwit index: schema, size, doc count, splits."""
    r = await _client.get(f"/api/v1/indexes/{index_id}/describe")
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def search(
    index_id: str,
    query: str,
    start_timestamp: int | None = None,
    end_timestamp: int | None = None,
    max_hits: int = 20,
    sort_by: str | None = None,
) -> dict[str, Any]:
    """Run a Quickwit search query against an index.

    `query` is Quickwit's native query language (e.g. 'field:value AND other:*').
    `start_timestamp`/`end_timestamp` are UNIX seconds and filter on the index's
    timestamp field.
    `max_hits` caps the number of returned hits (default 20).
    `sort_by` is a field name, optionally prefixed with '-' for descending.
    """
    body: dict[str, Any] = {"query": query, "max_hits": max_hits}
    if start_timestamp is not None:
        body["start_timestamp"] = start_timestamp
    if end_timestamp is not None:
        body["end_timestamp"] = end_timestamp
    if sort_by is not None:
        body["sort_by"] = sort_by
    r = await _client.post(f"/api/v1/{index_id}/search", json=body)
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def parse_query(
    query: str,
    search_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Parse a query into Quickwit's AST without running a search."""
    body: dict[str, Any] = {"query": query}
    if search_fields:
        body["search_field"] = search_fields
    r = await _client.post("/api/v1/parse-query", json=body)
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def search_plan(
    index_id: str,
    query: str,
    start_timestamp: int | None = None,
    end_timestamp: int | None = None,
    max_hits: int = 20,
    sort_by: str | None = None,
) -> dict[str, Any]:
    """Return a Quickwit search execution plan without running the search."""
    body: dict[str, Any] = {"query": query, "max_hits": max_hits}
    if start_timestamp is not None:
        body["start_timestamp"] = start_timestamp
    if end_timestamp is not None:
        body["end_timestamp"] = end_timestamp
    if sort_by is not None:
        body["sort_by"] = sort_by
    r = await _client.post(f"/api/v1/{index_id}/search-plan", json=body)
    r.raise_for_status()
    return r.json()


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
