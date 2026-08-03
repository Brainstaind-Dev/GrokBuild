#!/usr/bin/env bash
#
# Step 1 (run first on the Raspberry Pi):
#   Verify OS tooling and libraries needed for Embodi / ReflexKernel.
#   Does NOT install packages — only reports readiness.
#
# Usage:
#   chmod +x scripts/pi/01_verify_host.sh scripts/pi/02_standup_embodi.sh
#   ./scripts/pi/01_verify_host.sh
#   ./scripts/pi/01_verify_host.sh --strict    # treat WARNs as failure
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

STRICT=0
for arg in "$@"; do
  case "$arg" in
    --strict|-s) STRICT=1 ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
  esac
done

FAILS=0
WARNS=0

bump_fail() { FAILS=$((FAILS + 1)); fail "$*"; }
bump_warn() {
  WARNS=$((WARNS + 1))
  warn "$*"
  if [[ "$STRICT" -eq 1 ]]; then
    FAILS=$((FAILS + 1))
  fi
}

hdr "Embodi Pi host verification"
info "Host: $(hostname 2>/dev/null || echo unknown)"
info "Date: $(date -Is 2>/dev/null || date)"
info "User: $(whoami)  UID=$(id -u)"

# ---------------------------------------------------------------------------
hdr "Architecture & OS"
# ---------------------------------------------------------------------------
ARCH="$(uname -m 2>/dev/null || echo unknown)"
case "$ARCH" in
  aarch64|arm64)
    ok "Architecture: $ARCH (expected for Pi 5 64-bit)"
    ;;
  armv7l|armhf)
    bump_warn "Architecture: $ARCH — 32-bit; prefer Raspberry Pi OS 64-bit (aarch64) for Embodi"
    ;;
  *)
    bump_warn "Architecture: $ARCH — scripts target Raspberry Pi (aarch64)"
    ;;
esac

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  ok "OS: ${PRETTY_NAME:-$NAME $VERSION_ID}"
  if [[ "${ID:-}" == "debian" || "${ID:-}" == "raspbian" || "${ID_LIKE:-}" == *debian* ]]; then
    ok "Debian-family package manager expected (dpkg/apt)"
  else
    bump_warn "Non-Debian OS; package checks may not apply"
  fi
else
  bump_warn "/etc/os-release missing"
fi

# ---------------------------------------------------------------------------
hdr "Core CLI tools"
# ---------------------------------------------------------------------------
for cmd in git python3 pip3; do
  if have_cmd "$cmd"; then
    ver="$($cmd --version 2>&1 | head -n1)"
    ok "$cmd → $ver"
  else
    bump_fail "Missing command: $cmd"
  fi
done

if python3 -c "import venv" 2>/dev/null; then
  ok "python3 venv module available"
else
  bump_fail "python3 venv missing (install: sudo apt install python3-venv)"
fi

if have_cmd python3; then
  PYV="$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
  # Require 3.9+
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)'; then
    ok "Python version $PYV (>= 3.9)"
  else
    bump_fail "Python $PYV is too old; need >= 3.9"
  fi
fi

# ---------------------------------------------------------------------------
hdr "Build toolchain (for numpy/native wheels)"
# ---------------------------------------------------------------------------
for cmd in gcc make; do
  if have_cmd "$cmd"; then
    ok "$cmd present"
  else
    bump_fail "Missing: $cmd (install: sudo apt install build-essential)"
  fi
done

if pkg_installed build-essential; then
  ok "deb package: build-essential"
else
  bump_warn "deb package build-essential not reported installed"
fi

if pkg_installed python3-dev; then
  ok "deb package: python3-dev"
else
  bump_fail "deb package python3-dev missing (needed for some pip wheels)"
fi

if pkg_installed libopenblas-dev; then
  ok "deb package: libopenblas-dev"
else
  bump_warn "libopenblas-dev missing (recommended for numpy performance)"
fi

# ---------------------------------------------------------------------------
hdr "I2C / GPIO (future hardware path)"
# ---------------------------------------------------------------------------
for pkg in i2c-tools python3-smbus python3-lgpio python3-gpiozero; do
  if pkg_installed "$pkg"; then
    ok "deb package: $pkg"
  else
    bump_warn "deb package missing: $pkg (needed later for sensors/GPIO)"
  fi
done

if have_cmd i2cdetect; then
  ok "i2cdetect available"
else
  bump_warn "i2cdetect not on PATH"
fi

if [[ -e /dev/i2c-1 ]]; then
  ok "/dev/i2c-1 present"
  if [[ -r /dev/i2c-1 ]]; then
    ok "/dev/i2c-1 readable by $(whoami)"
  else
    bump_warn "/dev/i2c-1 not readable — add user to 'i2c' group and re-login"
  fi
else
  bump_warn "/dev/i2c-1 not found — enable I2C: sudo raspi-config → Interface Options → I2C"
fi

if [[ -e /dev/gpiomem ]] || [[ -d /sys/class/gpio ]]; then
  ok "GPIO interface present"
else
  bump_warn "GPIO interface not obvious (may still work via lgpio)"
fi

# Group membership hints
if have_cmd groups; then
  G="$(groups)"
  info "Groups: $G"
  echo "$G" | grep -qw i2c || bump_warn "user not in 'i2c' group (sudo usermod -aG i2c \$USER)"
  echo "$G" | grep -qw gpio || bump_warn "user not in 'gpio' group (optional; sudo usermod -aG gpio \$USER)"
fi

# ---------------------------------------------------------------------------
hdr "Audio (optional mic path)"
# ---------------------------------------------------------------------------
if pkg_installed libportaudio2; then
  ok "deb package: libportaudio2"
else
  bump_warn "libportaudio2 missing (needed only if using sounddevice/audio extras)"
fi
if pkg_installed portaudio19-dev; then
  ok "deb package: portaudio19-dev"
else
  bump_warn "portaudio19-dev missing (build sounddevice from source if needed)"
fi

# ---------------------------------------------------------------------------
hdr "Network / optional remote Saddle"
# ---------------------------------------------------------------------------
if have_cmd curl; then
  ok "curl present"
else
  bump_warn "curl missing (handy for health checks)"
fi
if have_cmd ss || have_cmd netstat; then
  ok "socket tools present (ss/netstat)"
else
  bump_warn "ss/netstat missing (optional)"
fi

# ---------------------------------------------------------------------------
hdr "Git repository context"
# ---------------------------------------------------------------------------
ROOT="$(repo_root)"
info "Repo root (detected): $ROOT"
if [[ -d "$ROOT/.git" ]]; then
  ok "Git metadata present"
  if have_cmd git; then
    BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    COMMIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    ok "Branch: $BRANCH  Commit: $COMMIT"
    if git -C "$ROOT" remote get-url origin >/dev/null 2>&1; then
      info "origin: $(git -C "$ROOT" remote get-url origin)"
    fi
    # Dirty tree is OK but note it
    if [[ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]]; then
      bump_warn "Working tree has local changes (git status)"
    else
      ok "Working tree clean"
    fi
  fi
else
  bump_fail "Not a git clone at $ROOT — clone GrokBuild before standup"
fi

# Expected top-level pieces
for rel in EmbodI/ReflexKernel SensoryCortex HIAgent; do
  if [[ -d "$ROOT/$rel" ]]; then
    ok "Present: $rel"
  else
    bump_warn "Missing directory: $rel (pull latest master after desktop push)"
  fi
done

# ---------------------------------------------------------------------------
hdr "Summary"
# ---------------------------------------------------------------------------
info "Fails: $FAILS   Warns: $WARNS   Strict: $STRICT"
if [[ "$FAILS" -eq 0 ]]; then
  ok "Host looks ready for Embodi standup."
  info "Next: ./scripts/pi/02_standup_embodi.sh"
  exit 0
else
  fail "Host verification failed ($FAILS). Fix packages/groups then re-run."
  info "Suggested install (if still missing):"
  cat <<'EOF'
  sudo apt update
  sudo apt install -y git python3-pip python3-venv python3-dev \
    build-essential libopenblas-dev \
    i2c-tools python3-smbus \
    libportaudio2 portaudio19-dev \
    python3-lgpio python3-gpiozero
  sudo usermod -aG i2c,gpio "$USER"
  # then log out/in; enable I2C via raspi-config if /dev/i2c-1 missing
EOF
  exit 1
fi
