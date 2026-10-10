# AgenticRAG MCP sidecar for Dify.
# Build from the AgenticRAG repo ROOT (context must include pyproject.toml + src/):
#   docker build -f dify/docker/mcp-server/Dockerfile -t agentic-rag-mcp:latest .
# NOTE: ~6.7 GB — torch (via sentence-transformers) pulls CUDA wheels on both
#       arm64 and x86_64. For a much smaller image force CPU-only torch:
#       pip install --extra-index-url https://download.pytorch.org/whl/cpu .
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . uvicorn

# Bake the local embedding model so first-run answers are instant
# (all-MiniLM-L6-v2, ~90 MB; matches config default).
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('all-MiniLM-L6-v2')"

COPY dify/docker/mcp-server/server.py ./server.py

EXPOSE 28080
CMD ["python", "server.py"]
