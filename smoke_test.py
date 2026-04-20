#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from typing import Any

from quickwit_mcp import server


def _extract_index_id(item: Any) -> str | None:
    if isinstance(item, dict):
        value = item.get("index_id")
        if isinstance(value, str) and value:
            return value
    return None


async def _run(args: argparse.Namespace) -> int:
    try:
        indexes = await server.list_indexes()
        print(f"list_indexes: OK ({len(indexes)} indexes)")

        index_id = args.index
        if index_id is None:
            if not indexes:
                print("No indexes found. Pass --index after creating one.")
                return 2
            extracted = _extract_index_id(indexes[0])
            if not extracted:
                print("Unable to infer index_id from list_indexes response. Pass --index.")
                return 2
            index_id = extracted
            print(f"Using first index: {index_id}")

        desc = await server.describe_index(index_id)
        print("describe_index: OK")
        print(json.dumps(desc, indent=2)[:1200])

        parsed = await server.parse_query(args.query)
        print("parse_query: OK")
        print(json.dumps(parsed, indent=2)[:1200])

        plan = await server.search_plan(
            index_id=index_id,
            query=args.query,
            start_timestamp=args.start_timestamp,
            end_timestamp=args.end_timestamp,
            max_hits=args.max_hits,
            sort_by=args.sort_by,
        )
        print("search_plan: OK")
        print(json.dumps(plan, indent=2)[:1200])

        result = await server.search(
            index_id=index_id,
            query=args.query,
            start_timestamp=args.start_timestamp,
            end_timestamp=args.end_timestamp,
            max_hits=args.max_hits,
            sort_by=args.sort_by,
        )
        print("search: OK")
        print(json.dumps(result, indent=2)[:2000])
        return 0
    except Exception as exc:
        print(f"smoke_test failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        await server._client.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test quickwit-mcp request paths against a live Quickwit instance."
    )
    parser.add_argument("--index", help="Quickwit index ID to query.")
    parser.add_argument("--query", default="*", help="Quickwit query string.")
    parser.add_argument("--max-hits", type=int, default=3, help="max_hits for search requests.")
    parser.add_argument("--sort-by", help="Quickwit sort expression, e.g. -timestamp.")
    parser.add_argument("--start-timestamp", type=int, help="Start timestamp (unix seconds).")
    parser.add_argument("--end-timestamp", type=int, help="End timestamp (unix seconds).")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
