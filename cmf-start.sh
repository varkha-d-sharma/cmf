#!/bin/bash
###
# Copyright (2026) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

# Re-execute with bash if invoked via 'sh cmf-start.sh'
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
# cmf-start.sh
#
# Starts the CMF server stack quietly and tells you when each service is ready.
# Run this instead of 'docker compose up' for a clean, user-friendly experience.
# Make sure environment variables are set correctly before running the script.
# It will automatically take environment variables from the .env file if present.
# 
# Usage:
#   sh ./cmf-start.sh            # start all services
#   sh ./cmf-start.sh --no-build # skip rebuilding images (faster if nothing changed)

set -u

# ── ANSI colors (disabled automatically when not running in a terminal) ───────
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; DIM=''; NC=''
fi

# ── Paths ─────────────────────────────────────────────────────────────────────
COMPOSE_FILE="docker-compose-server.yml"
ENV_FILE=".env"

# ── Load .env for port overrides ──────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

NGINX_HTTP_PORT="${NGINX_HTTP_PORT:-80}"
MCP_EXTERNAL_PORT="${MCP_EXTERNAL_PORT:-8382}"
SERVICE_WAIT_TIMEOUT="${SERVICE_WAIT_TIMEOUT:-300}"   # seconds before giving up

# Derive base URL from REACT_APP_CMF_API_URL (set in .env), fall back to localhost
CMF_BASE_URL="${REACT_APP_CMF_API_URL:-http://localhost:${NGINX_HTTP_PORT}}"
CMF_BASE_URL="${CMF_BASE_URL%/}"   # strip any trailing slash

# Extract just the hostname/IP for building the MCP URL
CMF_HOST=$(echo "$CMF_BASE_URL" | sed 's|https\?://||' | cut -d: -f1 | cut -d/ -f1)

# ── Spinner ───────────────────────────────────────────────────────────────────
_SPIN_PID=""

_spin_loop() {
    local msg="$1"
    local chars=('|' '/' '-' '\')
    local i=0
    while true; do
        printf "\r  %s  %s  " "${chars[$i]}" "$msg"
        i=$(( (i + 1) % 4 ))
        sleep 0.12
    done
}

spinner_start() {
    _spin_loop "$1" &
    _SPIN_PID=$!
    disown "$_SPIN_PID" 2>/dev/null || true
}

spinner_stop() {
    if [ -n "$_SPIN_PID" ]; then
        kill "$_SPIN_PID" 2>/dev/null || true
        _SPIN_PID=""
        printf "\r\033[2K"   # erase the spinner line
    fi
}

# ── Cleanup on any exit ───────────────────────────────────────────────────────
_cleanup() { spinner_stop; }
trap '_cleanup' EXIT INT TERM

# ── Logging ───────────────────────────────────────────────────────────────────
log_step()  { echo -e "  ${YELLOW}▸${NC}  $*"; }
log_ok()    { echo -e "  ${GREEN}${BOLD}✔${NC}  $*"; }
log_warn()  { echo -e "  ${YELLOW}${BOLD}!${NC}  $*"; }
log_error() { echo -e "  ${RED}${BOLD}✖${NC}  $*"; }
log_info()  { echo -e "     ${DIM}$*${NC}"; }
log_url()   { echo -e "     ${BOLD}→${NC}  ${BLUE}$*${NC}"; }

# ── Summary box helpers ───────────────────────────────────────────────────────
# Inner content width = 61 chars; total row = 67 (  + ║ + space + 61 + space + ║)
_HR="═══════════════════════════════════════════════════════════════"  # 63 ═
_box_top() { echo -e "  ${BOLD}╔${_HR}╗${NC}"; }
_box_sep() { echo -e "  ${BOLD}╠${_HR}╣${NC}"; }
_box_bot() { echo -e "  ${BOLD}╚${_HR}╝${NC}"; }
_box_row() { printf "  ${BOLD}║${NC} %-61s ${BOLD}║${NC}\n" "$1"; }
_svc_row() {
    local ok="$1" label="$2" url="$3"
    if [ "$ok" = "true" ]; then
        local pad=$(( 43 - ${#url} ))
        [ "$pad" -lt 0 ] && pad=0
        printf "  ${BOLD}║${NC} ${GREEN}${BOLD}✔${NC}  %-10s  →  ${BLUE}%s${NC}%${pad}s ${BOLD}║${NC}\n" \
            "$label" "$url" ""
    else
        local msg="timed out (${SERVICE_WAIT_TIMEOUT}s)"
        local pad=$(( 43 - ${#msg} ))
        [ "$pad" -lt 0 ] && pad=0
        printf "  ${BOLD}║${NC} ${RED}${BOLD}✖${NC}  %-10s  →  ${DIM}%s${NC}%${pad}s ${BOLD}║${NC}\n" \
            "$label" "$msg" ""
    fi
}

# ── Wait until an HTTP endpoint returns any response ─────────────────────────
# Returns 0 (success) as soon as the server replies with any HTTP status code.
# A code of "000" means the connection was refused / timed out.
wait_for_http() {
    local url="$1"
    local timeout="${2:-$SERVICE_WAIT_TIMEOUT}"
    local elapsed=0
    local interval=4
    while [ "$elapsed" -lt "$timeout" ]; do
        local code
        code=$(curl -s --max-time 4 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || true)
        # Any real HTTP status (1xx–5xx) means the server is up
        if [[ "$code" =~ ^[1-9][0-9]{2}$ ]]; then
            return 0
        fi
        sleep "$interval"
        elapsed=$(( elapsed + interval ))
    done
    return 1
}

# ── Parse arguments ───────────────────────────────────────────────────────────
BUILD_FLAG="--build"
for arg in "$@"; do
    case "$arg" in
        --no-build) BUILD_FLAG="" ;;
        --help|-h)
            echo "Usage: $0 [--no-build]"
            echo "  --no-build   Skip rebuilding Docker images (faster if nothing changed)"
            exit 0 ;;
        *) log_error "Unknown option: $arg"; exit 1 ;;
    esac
done

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "  ${BOLD}║         CMF  Server  Launcher            ║${NC}"
echo -e "  ${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running."
    log_info  "Please start Docker Desktop (or the Docker daemon) and try again."
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "docker-compose-server.yml not found in the current directory."
    log_info  "Please run this script from the cmf directory:"
    log_info  "  cd /path/to/cmf"
    log_info  "  ./cmf-start.sh"
    exit 1
fi

if ! command -v curl > /dev/null 2>&1; then
    log_error "'curl' is required but not installed."
    exit 1
fi

# ── Start containers ──────────────────────────────────────────────────────────
log_step "Starting CMF services..."
if [ -n "$BUILD_FLAG" ]; then
    log_info "(First run may take several minutes while Docker builds images.)"
fi
echo ""

COMPOSE_LOG="$(mktemp)"
spinner_start "Launching containers, please wait..."

if ! docker compose -f "$COMPOSE_FILE" up -d $BUILD_FLAG > "$COMPOSE_LOG" 2>&1; then
    spinner_stop
    log_error "Docker Compose failed to start the services."
    echo ""
    echo -e "  ${YELLOW}── Error details ───────────────────────────────${NC}"
    tail -25 "$COMPOSE_LOG" | sed 's/^/    /'
    echo -e "  ${YELLOW}────────────────────────────────────────────────${NC}"
    echo ""
    log_info "Full log saved to: $COMPOSE_LOG"
    exit 1
fi

rm -f "$COMPOSE_LOG"
spinner_stop
log_ok "Containers are running."
echo ""

# ── Service result tracking ───────────────────────────────────────────────────
SERVER_OK=false; UI_OK=false; MCP_OK=false

# ── Wait for CMF Server ───────────────────────────────────────────────────────
spinner_start "Waiting for CMF Server to become ready..."
if wait_for_http "${CMF_BASE_URL}/api/" "$SERVICE_WAIT_TIMEOUT"; then
    spinner_stop
    SERVER_OK=true
    log_ok "CMF Server is ready!"
    log_url "${CMF_BASE_URL}/api/"
else
    spinner_stop
    log_warn "CMF Server did not respond within ${SERVICE_WAIT_TIMEOUT}s."
    log_info "Check logs:  docker compose -f docker-compose-server.yml logs server"
fi
echo ""

# ── Wait for UI ───────────────────────────────────────────────────────────────
spinner_start "Waiting for CMF UI to become ready..."
if wait_for_http "${CMF_BASE_URL}/" "$SERVICE_WAIT_TIMEOUT"; then
    spinner_stop
    UI_OK=true
    log_ok "CMF UI is ready!"
    log_url "${CMF_BASE_URL}"
else
    spinner_stop
    log_warn "CMF UI did not respond within ${SERVICE_WAIT_TIMEOUT}s."
    log_info "Check logs:  docker compose -f docker-compose-server.yml logs ui"
fi
echo ""

# ── Wait for MCP Server ───────────────────────────────────────────────────────
spinner_start "Waiting for MCP Server to become ready..."
if wait_for_http "http://${CMF_HOST}:${MCP_EXTERNAL_PORT}/health" "$SERVICE_WAIT_TIMEOUT"; then
    spinner_stop
    MCP_OK=true
    log_ok "MCP Server is ready!"
    log_url "http://${CMF_HOST}:${MCP_EXTERNAL_PORT}"
else
    spinner_stop
    log_warn "MCP Server did not respond within ${SERVICE_WAIT_TIMEOUT}s."
    log_info "Check logs:  docker compose -f docker-compose-server.yml logs mcp"
fi

# ── Summary box ──────────────────────────────────────────────────────────────
echo ""
_box_top
_box_row "                   Service Access Summary"
_box_sep
_svc_row "$SERVER_OK" "CMF Server" "${CMF_BASE_URL}/api/"
_svc_row "$UI_OK"     "CMF UI"     "${CMF_BASE_URL}"
_svc_row "$MCP_OK"    "MCP Server" "http://${CMF_HOST}:${MCP_EXTERNAL_PORT}"
_box_sep
_box_row "  Stop:   docker compose -f docker-compose-server.yml down"
_box_row "  Manual: docker compose -f docker-compose-server.yml up -d"
_box_bot
echo ""
