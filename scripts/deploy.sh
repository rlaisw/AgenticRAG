#!/usr/bin/env bash
set -euo pipefail

# AgenticRAG MCP — Universal Deployment Script
# Works on: Ubuntu 24.x, ARM64 (aarch64) and x64 (x86_64)
# Supports: custom install directory, optional Dify integration
# Usage: bash scripts/deploy.sh

REPO_URL="https://github.com/rlaisw/AgenticRAG.git"
PORT_SIDECAR=28080
PORT_SEARXNG=28888

echo "╔════════════════════════════════════════════════╗"
echo "║   AgenticRAG MCP — Universal Deployment          ║"
echo "╚════════════════════════════════════════════════╝"
echo

# --- Detect platform ---
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64)  PLATFORM="ARM64" ;;
  x86_64|amd64)   PLATFORM="x64" ;;
  *)              PLATFORM="UNKNOWN ($ARCH)" ;;
esac
echo "Detected platform: $PLATFORM"

# --- Ask for install directory ---
read -rp "Install directory [default: $HOME/kilocode/AgenticRAG]: " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-$HOME/kilocode/AgenticRAG}"
INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"
echo "Installing to: $INSTALL_DIR"

# --- Ask about Dify ---
read -rp "Set up Dify integration? (y/n) [default: n]: " SETUP_DIFY
SETUP_DIFY="${SETUP_DIFY:-n}"

# --- Confirm ---
echo
echo "Summary:"
echo "  Platform:     $PLATFORM"
echo "  Directory:    $INSTALL_DIR"
echo "  Dify:         $SETUP_DIFY"
echo "  Sidecar port: $PORT_SIDECAR (aligned)"
echo "  SearXNG port: $PORT_SEARXNG (aligned)"
read -rp "Proceed? (y/n): " CONFIRM
[ "$CONFIRM" != "y" ] && { echo "Aborted."; exit 1; }

# --- Step 1: Clone ---
echo "▶ Step 1: Cloning to $INSTALL_DIR ..."
if [ -d "$INSTALL_DIR" ]; then
  echo "  Directory exists — pulling latest instead"
  git -C "$INSTALL_DIR" pull origin main 2>/dev/null || true
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# --- Step 2: Install ---
echo "▶ Step 2: Installing Python package ..."
if ! command -v pipx >/dev/null 2>&1; then
  python3 -m pip install --user pipx 2>/dev/null || pip3 install pipx
fi
pipx install -e . --force 2>/dev/null || pip3 install -e .

# --- Step 3: Config ---
echo "▶ Step 3: Initializing config ..."
agentic-rag-mcp --init 2>/dev/null || python3 -m agentic_rag_mcp --init
echo "  Config: ~/.config/agentic-rag-mcp/config.toml"

# --- Step 4: Specialty profiles ---
PROFILES_FILE="$HOME/.config/agentic-rag-mcp/specialty_profiles.json"
if [ ! -f "$PROFILES_FILE" ]; then
  echo "▶ Step 4: Creating specialty profiles ..."
  cat > "$PROFILES_FILE" <<'EOF'
{
  "microsoft": {
    "sites": ["learn.microsoft.com", "techcommunity.microsoft.com"],
    "description": "Microsoft product documentation and community"
  },
  "huawei": {
    "sites": ["support.huawei.com", "forum.huawei.com"],
    "description": "Huawei networking and enterprise products"
  },
  "vibe_coding": {
    "sites": ["github.com", "stackoverflow.com", "docs.python.org"],
    "description": "Programming, dev tools, and code examples"
  },
  "ai": {
    "sites": ["arxiv.org", "huggingface.co", "openai.com"],
    "description": "AI research, models, and tools"
  }
}
EOF
  echo "  Created: $PROFILES_FILE (edit to customize)"
fi

# --- Step 5: Docker sidecar ---
echo "▶ Step 5: Building Docker image (auto-detects $PLATFORM) ..."
docker build -f dify/docker/mcp-server/Dockerfile -t agentic-rag-mcp:latest .

echo "▶ Step 6: Starting sidecar on aligned port $PORT_SIDECAR:$PORT_SIDECAR ..."
docker rm -f agentic-rag 2>/dev/null || true
docker run -d --name agentic-rag \
  -v "$HOME/.config/agentic-rag-mcp:/root/.config/agentic-rag-mcp" \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -p "$PORT_SIDECAR:$PORT_SIDECAR" \
  --restart always \
  agentic-rag-mcp:latest

echo "  Waiting for startup (first run downloads ~1.7 GB model) ..."
sleep 20

# --- Step 7: SearXNG ---
echo "▶ Step 7: Setting up SearXNG (for web_search) ..."
if [ ! -d "$HOME/searxng" ]; then
  mkdir -p "$HOME/searxng"
  cat > "$HOME/searxng/settings.yml" <<'EOF'
use_default_settings: true
server:
  secret_key: "change-me-to-random"
  limiter: false
search:
  formats:
    - html
    - json
EOF
fi

docker rm -f searxng 2>/dev/null || true
docker run -d --name searxng \
  -v "$HOME/searxng:/etc/searxng" \
  -e GRANIAN_PORT=$PORT_SEARXNG \
  -p "$PORT_SEARXNG:$PORT_SEARXNG" \
  --restart unless-stopped \
  searxng/searxng

# --- Step 8: Dify (optional) ---
if [ "$SETUP_DIFY" = "y" ]; then
  echo "▶ Step 8: Dify integration"
  echo "  1. Find Dify's networks: docker network ls"
  echo "  2. Connect: docker network connect <dify_network> agentic-rag"
  echo "  3. Connect: docker network connect <dify_network> searxng"
  echo "  4. Add to Dify's .env: SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=agentic-rag"
  echo "  5. Restart: docker compose up -d ssrf_proxy"
  echo "  6. Dify UI → Tools → MCP → Add Server:"
  echo "     URL: http://agentic-rag:$PORT_SIDECAR/mcp"
  echo "     Headers: none, DCR: unchecked"
  echo "  7. Import chatflow: $INSTALL_DIR/dify/Chatflow Basic (AgenticRAG Agent).yml"
fi

# --- Step 9: Verify ---
echo
echo "▶ Step 9: Verifying ..."
sleep 5

echo -n "  Sidecar healthz:    "
curl -s -m 10 "http://localhost:$PORT_SIDECAR/healthz" && echo " ✅" || echo " ❌"

echo -n "  SearXNG JSON API:    "
SEARXNG_STATUS=$(curl -s -m 10 "http://localhost:$PORT_SEARXNG/search?q=test&format=json" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
echo "$SEARXNG_STATUS $([ "$SEARXNG_STATUS" = "200" ] && echo '✅' || echo '❌ (check ~/searxng/settings.yml)')"

echo -n "  MCP tools:           "
TOOLS=$(curl -s -m 15 "http://localhost:$PORT_SIDECAR/mcp" \
  -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  2>/dev/null | grep -o '"name"' | wc -l)
echo "$TOOLS tools $([ "$TOOLS" -ge 13 ] && echo '✅' || echo '❌')"

echo
echo "╔════════════════════════════════════════════════╗"
echo "║   Deployment Complete!                            ║"
echo "╚════════════════════════════════════════════════╝"
echo "  Directory:     $INSTALL_DIR"
echo "  Platform:      $PLATFORM"
echo "  Sidecar:       http://localhost:$PORT_SIDECAR/healthz"
echo "  SearXNG:       http://localhost:$PORT_SEARXNG"
echo "  Config:        ~/.config/agentic-rag-mcp/config.toml"
echo "  Profiles:      ~/.config/agentic-rag-mcp/specialty_profiles.json"
echo "  Full runbook:  $INSTALL_DIR/DEPLOY.md"
