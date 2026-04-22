# Kubernetes Examples

This folder contains generic manifests for running `quickwit-mcp` in Kubernetes.

Files:
- `namespace.yaml`: Namespace example (`mcp`).
- `quickwit-mcp-single.yaml`: Single MCP instance + Service.
- `quickwit-mcp-logs.yaml`: Logs MCP instance + Service.
- `quickwit-mcp-tracing.yaml`: Tracing MCP instance + Service.

Update placeholders before apply:
- `image: ghcr.io/kraftaa/quickwit-mcp-server:<tag>`
- Quickwit DNS names in `QUICKWIT_URL`, for example:
  - `http://<quickwit-searcher-service>.<quickwit-namespace>.svc.cluster.local:7280`
  - `http://<quickwit-logs-searcher-service>.<quickwit-namespace>.svc.cluster.local:7280`
  - `http://<quickwit-tracing-searcher-service>.<quickwit-namespace>.svc.cluster.local:7280`

Apply examples:

```bash
kubectl apply -f kube/namespace.yaml
kubectl apply -f kube/quickwit-mcp-single.yaml
```

or dual cluster:

```bash
kubectl apply -f kube/namespace.yaml
kubectl apply -f kube/quickwit-mcp-logs.yaml
kubectl apply -f kube/quickwit-mcp-tracing.yaml
```

Verify MCP handshake:

```bash
kubectl -n mcp run tmp-curl --rm -it --restart=Never --image=curlimages/curl -- \
  curl -i -N \
    -H "Accept: application/json, text/event-stream" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}' \
    http://quickwit-mcp.mcp.svc.cluster.local:3020/mcp
```
