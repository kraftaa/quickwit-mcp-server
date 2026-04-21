# quickwit-mcp

MCP server exposing a curated surface of the [Quickwit](https://quickwit.io) search REST API to LLM agents over Streamable HTTP transport.

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

## Deploying

Use the published image and run it next to Quickwit with `QUICKWIT_URL` pointing at your searcher.

Image:
- `ghcr.io/kraftaa/quickwit-mcp-server:<tag>`

One server talks to one Quickwit cluster. If you have multiple clusters (e.g. separate logs and traces), run one instance per cluster with different `QUICKWIT_URL` values.

## Using from an MCP client

Example MCP client config:

```json
{
  "mcp": {
    "quickwit_cluster_a": {
      "type": "remote",
      "url": "http://<mcp-service-name>.<mcp-namespace>.svc.cluster.local:3020/mcp",
      "enabled": true
    },
    "quickwit_cluster_b": {
      "type": "remote",
      "url": "http://<mcp-service-name>.<mcp-namespace>.svc.cluster.local:3020/mcp",
      "enabled": true
    }
  }
}
```

Then ask your client to call tools like:
- `list_indexes`
- `describe_index`
- `search` with `start_timestamp` / `end_timestamp` for time windows (e.g. last 5 minutes, last 24 hours)

## Quickwit version support

Written against Quickwit 0.8.x REST API and cross-checked against current 0.9 main-branch API source:
- Core `list_indexes`, `describe_index`, and `search` paths remain stable.
- `/{index}/search/stream` is removed in 0.9 and intentionally not exposed here.
- `parse-query` and `search-plan` are exposed as optional preflight tools.

## License

MIT. See [LICENSE](LICENSE).
