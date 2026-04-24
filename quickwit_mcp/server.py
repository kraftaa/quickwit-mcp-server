import os
import time
from collections import Counter
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


def _join_and(*parts: str | None) -> str:
    tokens = [p.strip() for p in parts if p and p.strip()]
    if not tokens:
        return "*"
    if len(tokens) == 1:
        return tokens[0]
    return " AND ".join(f"({token})" for token in tokens)


def _window_bounds(
    window_minutes: int,
    now_timestamp: int | None = None,
) -> tuple[int, int, int, int]:
    if window_minutes <= 0:
        raise ValueError("window_minutes must be > 0")
    end_current = int(now_timestamp if now_timestamp is not None else time.time())
    start_current = end_current - (window_minutes * 60)
    start_previous = start_current - (window_minutes * 60)
    end_previous = start_current
    return start_current, end_current, start_previous, end_previous


async def _search_raw(
    index_id: str,
    query: str,
    start_timestamp: int | None,
    end_timestamp: int | None,
    max_hits: int,
    sort_by: str | None = None,
) -> dict[str, Any]:
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


def _extract_hits(response: dict[str, Any]) -> list[dict[str, Any]]:
    raw_hits = response.get("hits", [])
    if not isinstance(raw_hits, list):
        return []
    output: list[dict[str, Any]] = []
    for hit in raw_hits:
        if isinstance(hit, dict):
            if isinstance(hit.get("json"), dict):
                output.append(hit["json"])
            elif isinstance(hit.get("_source"), dict):
                output.append(hit["_source"])
            else:
                output.append(hit)
    return output


def _value_at_path(doc: dict[str, Any], path: str) -> Any:
    current: Any = doc
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize_pattern(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        token = value.strip()
    else:
        token = str(value).strip()
    if not token:
        return None
    return token[:240]


def _pattern_counts(response: dict[str, Any], field_path: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for hit in _extract_hits(response):
        pattern = _normalize_pattern(_value_at_path(hit, field_path))
        if pattern:
            counts[pattern] += 1
    return counts


def _response_hit_count(response: dict[str, Any]) -> int:
    value = response.get("num_hits")
    if isinstance(value, int):
        return value
    return len(_extract_hits(response))


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
    return await _search_raw(
        index_id=index_id,
        query=query,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        max_hits=max_hits,
        sort_by=sort_by,
    )


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


@mcp.tool()
async def find_new_error_patterns(
    index_id: str,
    service_query: str | None = None,
    window_minutes: int = 15,
    pattern_field: str = "message",
    error_query: str = "ERROR OR Exception OR timeout",
    max_hits: int = 500,
    now_timestamp: int | None = None,
) -> dict[str, Any]:
    """Find error patterns present in the current window but absent in the previous window."""
    start_current, end_current, start_previous, end_previous = _window_bounds(
        window_minutes=window_minutes,
        now_timestamp=now_timestamp,
    )
    query = _join_and(service_query, error_query)
    current = await _search_raw(
        index_id=index_id,
        query=query,
        start_timestamp=start_current,
        end_timestamp=end_current,
        max_hits=max_hits,
    )
    previous = await _search_raw(
        index_id=index_id,
        query=query,
        start_timestamp=start_previous,
        end_timestamp=end_previous,
        max_hits=max_hits,
    )
    current_counts = _pattern_counts(current, pattern_field)
    previous_counts = _pattern_counts(previous, pattern_field)
    new_patterns = [
        {
            "pattern": pattern,
            "current_count": count,
            "previous_count": previous_counts.get(pattern, 0),
        }
        for pattern, count in current_counts.most_common()
        if previous_counts.get(pattern, 0) == 0
    ]
    return {
        "window_minutes": window_minutes,
        "pattern_field": pattern_field,
        "query": query,
        "current_window": {"start_timestamp": start_current, "end_timestamp": end_current},
        "previous_window": {
            "start_timestamp": start_previous,
            "end_timestamp": end_previous,
        },
        "new_error_patterns": new_patterns,
    }


@mcp.tool()
async def summarize_error_patterns(
    index_id: str,
    service_query: str | None = None,
    window_minutes: int = 15,
    pattern_field: str = "message",
    error_query: str = "ERROR OR Exception OR timeout",
    top_k: int = 5,
    max_hits: int = 500,
    now_timestamp: int | None = None,
) -> dict[str, Any]:
    """Summarize top error patterns for current and previous windows with deterministic deltas."""
    if top_k <= 0:
        raise ValueError("top_k must be > 0")
    start_current, end_current, start_previous, end_previous = _window_bounds(
        window_minutes=window_minutes,
        now_timestamp=now_timestamp,
    )
    query = _join_and(service_query, error_query)
    current = await _search_raw(
        index_id=index_id,
        query=query,
        start_timestamp=start_current,
        end_timestamp=end_current,
        max_hits=max_hits,
    )
    previous = await _search_raw(
        index_id=index_id,
        query=query,
        start_timestamp=start_previous,
        end_timestamp=end_previous,
        max_hits=max_hits,
    )
    current_counts = _pattern_counts(current, pattern_field)
    previous_counts = _pattern_counts(previous, pattern_field)
    top_current = []
    for pattern, count in current_counts.most_common(top_k):
        previous_count = previous_counts.get(pattern, 0)
        top_current.append(
            {
                "pattern": pattern,
                "current_count": count,
                "previous_count": previous_count,
                "delta": count - previous_count,
            }
        )
    return {
        "window_minutes": window_minutes,
        "pattern_field": pattern_field,
        "query": query,
        "current_window": {"start_timestamp": start_current, "end_timestamp": end_current},
        "previous_window": {
            "start_timestamp": start_previous,
            "end_timestamp": end_previous,
        },
        "top_patterns": top_current,
        "totals": {
            "current_hits": _response_hit_count(current),
            "previous_hits": _response_hit_count(previous),
        },
    }


@mcp.tool()
async def investigate_service_logs(
    index_id: str,
    service_query: str,
    window_minutes: int = 15,
    pattern_field: str = "message",
    error_query: str = "ERROR OR Exception OR timeout",
    max_hits: int = 500,
    now_timestamp: int | None = None,
) -> dict[str, Any]:
    """Deterministic service investigation based on log deltas between current and previous windows."""
    start_current, end_current, start_previous, end_previous = _window_bounds(
        window_minutes=window_minutes,
        now_timestamp=now_timestamp,
    )
    total_query = _join_and(service_query)
    error_filter = _join_and(service_query, error_query)

    current_total = await _search_raw(
        index_id=index_id,
        query=total_query,
        start_timestamp=start_current,
        end_timestamp=end_current,
        max_hits=1,
    )
    previous_total = await _search_raw(
        index_id=index_id,
        query=total_query,
        start_timestamp=start_previous,
        end_timestamp=end_previous,
        max_hits=1,
    )
    current_errors = await _search_raw(
        index_id=index_id,
        query=error_filter,
        start_timestamp=start_current,
        end_timestamp=end_current,
        max_hits=max_hits,
    )
    previous_errors = await _search_raw(
        index_id=index_id,
        query=error_filter,
        start_timestamp=start_previous,
        end_timestamp=end_previous,
        max_hits=max_hits,
    )

    current_total_hits = _response_hit_count(current_total)
    previous_total_hits = _response_hit_count(previous_total)
    current_error_hits = _response_hit_count(current_errors)
    previous_error_hits = _response_hit_count(previous_errors)

    current_error_rate = (
        (current_error_hits / current_total_hits) if current_total_hits > 0 else 0.0
    )
    previous_error_rate = (
        (previous_error_hits / previous_total_hits) if previous_total_hits > 0 else 0.0
    )
    error_rate_delta = current_error_rate - previous_error_rate

    current_patterns = _pattern_counts(current_errors, pattern_field)
    previous_patterns = _pattern_counts(previous_errors, pattern_field)
    timeout_delta = 0
    for pattern, count in current_patterns.items():
        token = pattern.lower()
        if "timeout" in token or "timed out" in token:
            timeout_delta += count - previous_patterns.get(pattern, 0)

    if error_rate_delta > 0 and timeout_delta > 0:
        likely_cause = "dependency issue likely (error rate and timeout patterns increased)"
    elif error_rate_delta > 0:
        likely_cause = "regression likely (error rate increased)"
    elif error_rate_delta <= 0 and timeout_delta > 0:
        likely_cause = "performance instability likely (timeouts increased without error-rate growth)"
    else:
        likely_cause = "no strong degradation signal detected"

    top_patterns = []
    for pattern, count in current_patterns.most_common(5):
        previous_count = previous_patterns.get(pattern, 0)
        top_patterns.append(
            {
                "pattern": pattern,
                "current_count": count,
                "previous_count": previous_count,
                "delta": count - previous_count,
            }
        )

    return {
        "service_query": service_query,
        "window_minutes": window_minutes,
        "current_window": {"start_timestamp": start_current, "end_timestamp": end_current},
        "previous_window": {
            "start_timestamp": start_previous,
            "end_timestamp": end_previous,
        },
        "metrics": {
            "error_rate": {
                "previous": previous_error_rate,
                "current": current_error_rate,
                "delta": error_rate_delta,
            },
            "error_hits": {"previous": previous_error_hits, "current": current_error_hits},
            "total_hits": {"previous": previous_total_hits, "current": current_total_hits},
        },
        "top_error_patterns": top_patterns,
        "likely_cause": likely_cause,
    }


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
