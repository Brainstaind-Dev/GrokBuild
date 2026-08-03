#!/usr/bin/env bash
#
# Step 2 (after 01_verify_host.sh):
#   Stand up the Embodi project on the Raspberry Pi:
#     - ensure repo layout
#     - create/refresh ReflexKernel venv
#     - pip install editable package + server/dev extras
#     - PYTHONPATH for SensoryCortex + HIAgent
#     - run pytest + kernel smoke
#     - optional: start Saddle server or print HIAgent hints
#
# Usage:
#   ./scripts/pi/02_standup_embodi.sh
#   ./scripts/pi/02_standup_embodi.sh --no-mcp
#   ./scripts/pi/02_standup_embodi.sh --with-xai
#   ./scripts/pi/02_standup_embodi.sh --start-saddle
#   ./scripts/pi/02_standup_embodi.sh --start-saddle --host 0.0.0.0 --port 8000
#   ./scripts/pi/02_standup_embodi.sh --skip-tests
#   ./scripts/pi/02_standup_embodi.sh --skip-verify
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

WITH_MCP=1
WITH_XAI=0
START_SADDLE=0
SKIP_TESTS=0
SKIP_VERIFY=0
SADDLE_HOST="0.0.0.0"
SADDLE_PORT="8000"
SADDLE_CONFIG=""
EXTRAS="dev,server"

for arg in "$@"; do
  case "$arg" in
    --with-mcp) WITH_MCP=1 ;;
    --no-mcp) WITH_MCP=0 ;;
    --with-xai) WITH_XAI=1 ;;
    --start-saddle) START_SADDLE=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --skip-verify) SKIP_VERIFY=1 ;;
    --host=*) SADDLE_HOST="${arg#*=}" ;;
    --port=*) SADDLE_PORT="${arg#*=}" ;;
    --config=*) SADDLE_CONFIG="${arg#*=}" ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *)
      # allow --host 0.0.0.0 style via shift pattern below
      :
      ;;
  esac
done

# Parse --host / --port / --config with separate values
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
  case "${args[$i]}" in
    --host)
      SADDLE_HOST="${args[$((i+1))]:-$SADDLE_HOST}"
      ;;
    --port)
      SADDLE_PORT="${args[$((i+1))]:-$SADDLE_PORT}"
      ;;
    --config)
      SADDLE_CONFIG="${args[$((i+1))]:-}"
      ;;
  esac
done

ROOT="$(repo_root)"
RK="$ROOT/EmbodI/ReflexKernel"
VENV="$RK/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

if [[ "$WITH_MCP" -eq 1 ]]; then
  EXTRAS="${EXTRAS},mcp"
fi

hdr "Embodi Pi standup"
info "Repo: $ROOT"
info "ReflexKernel: $RK"
info "Extras: .[$EXTRAS]"

# ---------------------------------------------------------------------------
# 0) Host verify
# ---------------------------------------------------------------------------
if [[ "$SKIP_VERIFY" -eq 0 ]]; then
  hdr "Running host verification (01_verify_host.sh)"
  if ! bash "${SCRIPT_DIR}/01_verify_host.sh"; then
    fail "Host verification failed. Fix issues or re-run with --skip-verify (not recommended)."
    exit 1
  fi
else
  warn "Skipping host verification (--skip-verify)"
fi

# ---------------------------------------------------------------------------
# 1) Layout
# ---------------------------------------------------------------------------
hdr "Repository layout"
if [[ ! -d "$RK" ]]; then
  fail "Missing EmbodI/ReflexKernel — is this a full GrokBuild clone? git pull?"
  exit 1
fi
ok "ReflexKernel present"
[[ -d "$ROOT/SensoryCortex" ]] && ok "SensoryCortex present" || warn "SensoryCortex missing (HI packages need it)"
[[ -d "$ROOT/HIAgent" ]] && ok "HIAgent present" || warn "HIAgent missing (optional on Pi)"

# ---------------------------------------------------------------------------
# 2) Venv
# ---------------------------------------------------------------------------
hdr "Python virtualenv"
if [[ ! -x "$PY" ]]; then
  info "Creating venv at $VENV"
  python3 -m venv "$VENV"
else
  ok "Existing venv: $VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
ok "Using: $($PY --version)"

info "Upgrading pip/setuptools/wheel"
"$PIP" install -q --upgrade pip setuptools wheel

# ---------------------------------------------------------------------------
# 3) Install ReflexKernel
# ---------------------------------------------------------------------------
hdr "Install ReflexKernel (editable)"
cd "$RK"
info "pip install -e \".[$EXTRAS]\""
"$PIP" install -e ".[${EXTRAS}]"

if [[ "$WITH_MCP" -eq 1 ]]; then
  # Ensure the *Model Context Protocol* SDK is present (FastMCP), not a
  # name-collision package that also registers as top-level "mcp".
  if ! "$PY" -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    warn "mcp.server.fastmcp missing after install — reinstalling official MCP SDK"
    "$PIP" uninstall -y mcp 2>/dev/null || true
    "$PIP" install -q "mcp>=1.2.0"
  fi
  if "$PY" -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    ok "MCP FastMCP import OK"
  else
    warn "MCP FastMCP still unavailable — MCP tests will skip; core tests should pass"
  fi
fi

if [[ "$WITH_XAI" -eq 1 ]]; then
  hdr "Optional: xAI SDK (HIAgent)"
  "$PIP" install -q xai-sdk
  if [[ -n "${XAI_API_KEY:-}" ]]; then
    ok "XAI_API_KEY is set in environment"
  else
    warn "xai-sdk installed but XAI_API_KEY is not set — export it before HIAgent"
  fi
fi

# Soft deps sometimes useful
if ! py_import_ok "$PY" pydantic_settings; then
  info "Installing pydantic-settings (SensoryCortex config)"
  "$PIP" install -q pydantic-settings || warn "pydantic-settings install failed (optional)"
fi

# ---------------------------------------------------------------------------
# 4) Environment for Cortex / HIAgent
# ---------------------------------------------------------------------------
hdr "Environment"
export PYTHONPATH="${ROOT}:${RK}/src${PYTHONPATH:+:$PYTHONPATH}"
ok "PYTHONPATH=$PYTHONPATH"

# Write activate helper for future shells
ENV_FILE="$ROOT/scripts/pi/env.pi.sh"
cat > "$ENV_FILE" <<EOF
# Generated by 02_standup_embodi.sh — source this in new shells on the Pi
#   source $(printf '%q' "$ENV_FILE")
export EMBODI_ROOT=$(printf '%q' "$ROOT")
export REFLEXKERNEL_ROOT=$(printf '%q' "$RK")
export PYTHONPATH="\${EMBODI_ROOT}:\${REFLEXKERNEL_ROOT}/src\${PYTHONPATH:+:\$PYTHONPATH}"
# shellcheck disable=SC1091
source $(printf '%q' "$VENV/bin/activate")
EOF
ok "Wrote shell helper: $ENV_FILE"
info "In new terminals:  source $ENV_FILE"

# ---------------------------------------------------------------------------
# 5) Import smoke
# ---------------------------------------------------------------------------
hdr "Import smoke"
"$PY" - <<'PY'
import sys
print("sys.path[0:3]", sys.path[0:3])
from reflexkernel.kernel import ReflexKernel
print("reflexkernel OK", ReflexKernel)
try:
    from SensoryCortex import SensoryCortex
    print("SensoryCortex OK", SensoryCortex)
except Exception as e:
    print("SensoryCortex WARN", type(e).__name__, e)
try:
    from HIAgent.config import load_config
    print("HIAgent OK", load_config)
except Exception as e:
    print("HIAgent WARN", type(e).__name__, e)
PY
ok "Import smoke finished"

# ---------------------------------------------------------------------------
# 6) Tests
# ---------------------------------------------------------------------------
if [[ "$SKIP_TESTS" -eq 0 ]]; then
  hdr "pytest (ReflexKernel core)"
  cd "$RK"
  "$PY" -m pytest tests/ -q --tb=line
  ok "ReflexKernel tests passed"

  if [[ -d "$ROOT/SensoryCortex/tests" ]]; then
    hdr "pytest (SensoryCortex)"
    cd "$ROOT"
    "$PY" -m pytest SensoryCortex/tests/ -q --tb=line || warn "SensoryCortex tests had failures"
  fi

  if [[ -d "$ROOT/HIAgent/tests" ]]; then
    hdr "pytest (HIAgent unit — no live xAI required for most)"
    cd "$ROOT"
    # feed/registry unit tests only if present; embedded smoke needs RK
    "$PY" -m pytest HIAgent/tests/test_feed_and_registry.py -q --tb=line || warn "HIAgent unit tests had failures"
  fi
else
  warn "Skipping tests (--skip-tests)"
fi

# ---------------------------------------------------------------------------
# 7) Kernel smoke (headless)
# ---------------------------------------------------------------------------
hdr "Kernel smoke (mcp_headless)"
cd "$RK"
"$PY" - <<'PY'
from pathlib import Path
from reflexkernel.kernel import ReflexKernel
cfg = Path("configs/mcp_headless.yaml")
k = ReflexKernel.from_config_path(str(cfg))
k.start()
actions = k.step()
st = k.get_state()
print("tick", st.get("tick"), "actions", len(actions), "running", st.get("running"))
k.stop()
print("kernel smoke OK")
PY
ok "Headless kernel step succeeded"

# ---------------------------------------------------------------------------
# 8) Optional Saddle
# ---------------------------------------------------------------------------
if [[ "$START_SADDLE" -eq 1 ]]; then
  hdr "Starting Saddle (foreground — Ctrl+C to stop)"
  CFG="${SADDLE_CONFIG:-$RK/configs/mcp_headless.yaml}"
  info "config=$CFG host=$SADDLE_HOST port=$SADDLE_PORT"
  info "Health (from another shell): curl -s http://127.0.0.1:${SADDLE_PORT}/health"
  cd "$RK"
  exec "$PY" -m scripts.server \
    --config "$CFG" \
    --host "$SADDLE_HOST" \
    --port "$SADDLE_PORT" \
    --log-level info
fi

# ---------------------------------------------------------------------------
hdr "Standup complete"
# ---------------------------------------------------------------------------
cat <<EOF

${C_GREEN}Embodi is ready on this Pi.${C_RESET}

Activate later:
  source ${ENV_FILE}

Quick commands:
  # Kernel smoke
  source ${ENV_FILE}
  cd ${RK}
  python -c "from reflexkernel.kernel import ReflexKernel; k=ReflexKernel.from_config_path('configs/mcp_headless.yaml'); k.start(); print(k.step()); k.stop()"

  # Saddle (LAN)
  source ${ENV_FILE}
  cd ${RK}
  python -m scripts.server --config configs/mcp_headless.yaml --host 0.0.0.0 --port 8000

  # HIAgent interactive (needs XAI_API_KEY + --with-xai install)
  source ${ENV_FILE}
  cd ${ROOT}
  python -m HIAgent interactive --backend embedded

Re-verify host only:
  ${SCRIPT_DIR}/01_verify_host.sh

Git updates (only update path):
  cd ${ROOT} && git pull --ff-only
  then re-run: ${SCRIPT_DIR}/02_standup_embodi.sh

EOF
ok "Done."
exit 0
