# quickwit-mcp

MCP server exposing a curated surface of the [Quickwit](https://quickwit.io) search REST API to LLM agents over Streamable HTTP transport.

## Tools

| Tool | Description |
|------|-------------|
| `list_indexes()` | All indexes on the cluster |
| `describe_index(index_id)` | Schema, size, doc count, splits |
| `search(index_id, query, ...)` | Query with optional timestamps, max_hits, sort |
| `count(index_id, query, ...)` | Hit count without fetching documents |
| `tail(index_id, n?, query?, sort_by?, timestamp_field?)` | Most recent N documents from an index |
| `aggregate(index_id, query, agg_field, ...)` | Top-N term aggregation for a field |
| `histogram(index_id, query, interval?, ...)` | Time-bucketed hit counts (date_histogram) |
| `parse_query(query, search_fields?)` | Parsed query AST |
| `search_plan(index_id, query, ...)` | Execution plan |
| `find_new_error_patterns(index_id, ...)` | Error types present now but not in previous window |
| `summarize_error_patterns(index_id, ...)` | Top error patterns + deterministic deltas |
| `investigate_service_logs(index_id, ...)` | Log-based likely cause summary |
| `health()` | Connectivity check with latency |

One server = one Quickwit cluster. Deploy twice (logs + tracing) as separate pods.

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `QUICKWIT_URL` | `http://localhost:7280` | Quickwit base URL (no trailing `/api/v1`) |
| `QUICKWIT_HTTP_TIMEOUT` | `30` | HTTP timeout in seconds |
| `QUICKWIT_MAX_RETRIES` | `3` | Number of connection retries on failure |
| `QUICKWIT_MCP_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
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

# Test aggregations
QUICKWIT_URL=http://localhost:7280 python smoke_test.py --index otel-logs-v0_7 --query 'severity_text:ERROR' --agg-field service_name

# Test histogram
QUICKWIT_URL=http://localhost:7280 python smoke_test.py --index otel-logs-v0_7 --query '*' --histogram timestamp_nanos
```

## Deploying

Use the published image and run it next to Quickwit with `QUICKWIT_URL` pointing at your searcher.

Image:
- `ghcr.io/kraftaa/quickwit-mcp-server:<tag>`

Release automation:
- GitHub Actions publishes container images to GHCR on tag push (`v*`).
- GitHub Actions publishes package releases to PyPI on tag push (`v*`) via Trusted Publisher.

One server talks to one Quickwit cluster. If you have multiple clusters (e.g. separate logs and traces), run one instance per cluster with different `QUICKWIT_URL` values.

## Kubernetes quickstart

See the ready-to-apply examples in [`kube/`](kube/):
- `kube/namespace.yaml`
- `kube/quickwit-mcp-single.yaml`
- `kube/quickwit-mcp-logs.yaml`
- `kube/quickwit-mcp-tracing.yaml`
- `kube/README.md`

Apply (single cluster):

```bash
kubectl apply -f kube/namespace.yaml
kubectl apply -f kube/quickwit-mcp-single.yaml
kubectl -n mcp rollout status deploy/quickwit-mcp
```

Apply (logs + tracing):

```bash
kubectl apply -f kube/namespace.yaml
kubectl apply -f kube/quickwit-mcp-logs.yaml
kubectl apply -f kube/quickwit-mcp-tracing.yaml
kubectl -n mcp rollout status deploy/quickwit-logs-mcp-server
kubectl -n mcp rollout status deploy/quickwit-tracing-mcp-server
```

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
- `aggregate` to group results by field (e.g. errors by service_name)
- `histogram` to see error rate over time
- `health` to check cluster connectivity before running queries

## Quickwit version support

Written against Quickwit 0.8.x REST API and cross-checked against current 0.9 main-branch API source:
- Core `list_indexes`, `describe_index`, and `search` paths remain stable.
- `/{index}/search/stream` is removed in 0.9 and intentionally not exposed here.
- `parse-query` and `search-plan` are exposed as optional preflight tools.
- Aggregations use the Elasticsearch-compatible aggregation syntax supported since 0.7.

## License

MIT. See [LICENSE](LICENSE).
