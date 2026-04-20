FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY quickwit_mcp ./quickwit_mcp
RUN pip install --no-cache-dir .

ENV MCP_HOST=0.0.0.0 MCP_PORT=3020
EXPOSE 3020
CMD ["quickwit-mcp"]
