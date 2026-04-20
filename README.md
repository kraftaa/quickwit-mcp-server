# quickwit-mcp

MCP server exposing a curated surface of the [Quickwit](https://quickwit.io) search REST API to LLM coding agents (Claude, Opencode). Talks Streamable HTTP transport.

## Tools

- `list_indexes()` → all indexes on the cluster
- `describe_index(index_id)` → schema, size, doc count, splits
- `search(index_id, query, start_timestamp?, end_timestamp?, max_hits?, sort_by?)` → hits
- `parse_query(query, search_fields?)` → parsed query AST
- `search_plan(index_id, query, start_timestamp?, end_timestamp?, max_hits?, sort_by?)` → execution plan

One server = one Quickwit cluster. Deploy twice (logs + tracing) as separate pods.

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `QUICKWIT_URL` | `http://localhost:7280` | Quickwit base URL (no trailing `/api/v1`) |
| `QUICKWIT_HTTP_TIMEOUT` | `30` | HTTP timeout in seconds |
| `MCP_HOST` | `0.0.0.0` | Bind host |
| `MCP_PORT` | `3020` | Bind port |

## Run locally

```bash
pip install -e .
QUICKWIT_URL=http://localhost:7280 quickwit-mcp
```

MCP Streamable HTTP endpoint: `http://localhost:3020/mcp`

Optional local smoke test (direct Quickwit calls via the same Python request code):

```bash
QUICKWIT_URL=http://localhost:7280 python smoke_test.py --index your-index-id --query '*'
```

## Docker

```bash
docker build -t quickwit-mcp:0.1.0 .
docker run --rm -p 3020:3020 -e QUICKWIT_URL=http://host.docker.internal:7280 quickwit-mcp:0.1.0
```

## Deploying

Build and push the image to any registry, then run it next to Quickwit with `QUICKWIT_URL` pointing at your searcher.

```bash
docker build -t quickwit-mcp-server:0.1.0 .
docker tag quickwit-mcp-server:0.1.0 <your-registry>/quickwit-mcp-server:0.1.0
docker push <your-registry>/quickwit-mcp-server:0.1.0
```

GitHub Actions is configured to publish to GHCR on tag push (`v*`) using:
- image name: `ghcr.io/<owner>/<repo>`
- platforms: `linux/amd64`, `linux/arm64`

Example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

One server talks to one Quickwit cluster. If you have multiple clusters (e.g. separate logs and traces), run one instance per cluster with different `QUICKWIT_URL` values.

## Quickwit version support

Written against Quickwit 0.8.x REST API and cross-checked against current 0.9 main-branch API source:
- Core `list_indexes`, `describe_index`, and `search` paths remain stable.
- `/{index}/search/stream` is removed in 0.9 and intentionally not exposed here.
- `parse-query` and `search-plan` are exposed as optional preflight tools.
