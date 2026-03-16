#!/usr/bin/env bash
# dev.sh — start/stop backend and frontend for local development
#
# Usage:
#   ./dev.sh start    # start both backend (:8000) and frontend (:5173)
#   ./dev.sh stop     # stop both
#   ./dev.sh restart  # stop then start
#   ./dev.sh status   # show running processes
#   ./dev.sh logs     # tail logs from both services

set -euo pipefail

# ── Colour helpers (defined first so _ensure_node22 can use them) ─────────────
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

# ── Auto-load nvm and switch to Node 22 if needed ────────────────────────────
_load_nvm() {
  # Source nvm if not already loaded
  if ! command -v nvm &>/dev/null; then
    local nvm_dir="${NVM_DIR:-$HOME/.nvm}"
    if [[ -s "$nvm_dir/nvm.sh" ]]; then
      # shellcheck source=/dev/null
      source "$nvm_dir/nvm.sh"
    fi
  fi
}

_ensure_node22() {
  _load_nvm
  local node_major
  node_major=$(node -e "process.stdout.write(process.versions.node.split('.')[0])" 2>/dev/null || echo "0")
  if (( node_major < 22 )); then
    if command -v nvm &>/dev/null; then
      yellow "  · Node $node_major detected — switching to Node 22 via nvm…"
      nvm use 22
    fi
  fi
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
LOG_DIR="$REPO_ROOT/.dev-logs"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# ── Helpers ──────────────────────────────────────────────────────────────────

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  if is_running "$pid_file"; then
    local pid
    pid=$(cat "$pid_file")
    kill "$pid" 2>/dev/null || true
    # Wait up to 5s for graceful exit
    local i=0
    while kill -0 "$pid" 2>/dev/null && (( i < 10 )); do
      sleep 0.5; (( i++ ))
    done
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$pid_file"
    green "  ✓ $name stopped"
  else
    yellow "  · $name was not running"
    rm -f "$pid_file"
  fi
}

check_prereqs() {
  local ok=true

  if ! command -v uv &>/dev/null; then
    red "  ✗ uv not found — install from https://docs.astral.sh/uv/"
    ok=false
  fi

  # Try to switch to Node 22 via nvm before checking
  _ensure_node22

  if ! command -v node &>/dev/null; then
    red "  ✗ node not found — install Node 22 via nvm: nvm install 22 && nvm use 22"
    ok=false
  else
    local node_major
    node_major=$(node -e "process.stdout.write(process.versions.node.split('.')[0])")
    if (( node_major < 22 )); then
      red "  ✗ Node $node_major detected — need Node 22+. Install with: nvm install 22"
      ok=false
    fi
  fi

  if ! command -v npm &>/dev/null; then
    red "  ✗ npm not found"
    ok=false
  fi

  [[ "$ok" == true ]]
}

# ── Start ─────────────────────────────────────────────────────────────────────

start_backend() {
  if is_running "$BACKEND_PID_FILE"; then
    yellow "  · backend already running (pid $(cat "$BACKEND_PID_FILE"))"
    return
  fi

  bold "  Starting backend…"

  # Ensure deps are installed
  (cd "$BACKEND_DIR" && uv sync --quiet)

  # Create data dir
  mkdir -p "$REPO_ROOT/data"

  # Start uvicorn in background
  (
    cd "$BACKEND_DIR"
    DATA_DIR="$REPO_ROOT/data" \
    CORS_ORIGINS="http://localhost:5173" \
    uv run uvicorn app.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --reload \
      >> "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
  )

  # Wait for it to be ready
  local i=0
  while (( i < 20 )); do
    if curl -sf http://localhost:8000/health &>/dev/null; then
      green "  ✓ backend ready at http://localhost:8000"
      return
    fi
    sleep 0.5; (( i++ ))
  done
  yellow "  ⚠ backend started but /health not yet responding — check $BACKEND_LOG"
}

start_frontend() {
  if is_running "$FRONTEND_PID_FILE"; then
    yellow "  · frontend already running (pid $(cat "$FRONTEND_PID_FILE"))"
    return
  fi

  bold "  Starting frontend…"

  # Install deps if node_modules is missing or package.json is newer
  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    (cd "$FRONTEND_DIR" && npm install --silent)
  fi

  (
    cd "$FRONTEND_DIR"
    VITE_API_BASE_URL="http://localhost:8000" \
    npm run dev -- --port 5173 \
      >> "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )

  # Wait for Vite to be ready
  local i=0
  while (( i < 20 )); do
    if curl -sf http://localhost:5173 &>/dev/null; then
      green "  ✓ frontend ready at http://localhost:5173"
      return
    fi
    sleep 0.5; (( i++ ))
  done
  yellow "  ⚠ frontend started but not yet responding — check $FRONTEND_LOG"
}

cmd_start() {
  bold "code-graph dev — starting services"
  echo ""

  if ! check_prereqs; then
    echo ""
    red "Fix the above issues and retry."
    exit 1
  fi

  mkdir -p "$LOG_DIR"

  start_backend
  start_frontend

  echo ""
  bold "Logs:"
  echo "  backend  → $BACKEND_LOG"
  echo "  frontend → $FRONTEND_LOG"
  echo ""
  echo "Run './dev.sh stop' to shut down."
}

# ── Stop ──────────────────────────────────────────────────────────────────────

cmd_stop() {
  bold "code-graph dev — stopping services"
  echo ""
  stop_service "backend"  "$BACKEND_PID_FILE"
  stop_service "frontend" "$FRONTEND_PID_FILE"
  echo ""
}

# ── Status ────────────────────────────────────────────────────────────────────

cmd_status() {
  bold "code-graph dev — status"
  echo ""
  if is_running "$BACKEND_PID_FILE"; then
    green "  ✓ backend  running (pid $(cat "$BACKEND_PID_FILE"))  http://localhost:8000"
  else
    red   "  ✗ backend  not running"
  fi
  if is_running "$FRONTEND_PID_FILE"; then
    green "  ✓ frontend running (pid $(cat "$FRONTEND_PID_FILE"))  http://localhost:5173"
  else
    red   "  ✗ frontend not running"
  fi
  echo ""
}

# ── Logs ──────────────────────────────────────────────────────────────────────

cmd_logs() {
  if [[ ! -d "$LOG_DIR" ]]; then
    yellow "No logs yet — run './dev.sh start' first."
    exit 0
  fi
  bold "Tailing logs (Ctrl-C to stop)…"
  echo ""
  tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

case "${1:-}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_stop; echo ""; cmd_start ;;
  status)  cmd_status ;;
  logs)    cmd_logs ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
