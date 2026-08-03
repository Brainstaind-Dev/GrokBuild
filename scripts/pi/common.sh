#!/usr/bin/env bash
# Shared helpers for Pi host verify + Embodi standup scripts.
# shellcheck disable=SC2034

set -o pipefail

if [[ -n "${BASH_VERSION:-}" ]]; then
  # Prefer fail-fast in callers; common.sh only defines helpers.
  :
fi

# Colors when stdout is a TTY
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_RED=$'\033[31m'
  C_CYAN=$'\033[36m'
  C_BOLD=$'\033[1m'
else
  C_RESET="" C_GREEN="" C_YELLOW="" C_RED="" C_CYAN="" C_BOLD=""
fi

ok()   { printf '%s[OK]%s   %s\n'   "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '%s[WARN]%s %s\n'   "$C_YELLOW" "$C_RESET" "$*"; }
fail() { printf '%s[FAIL]%s %s\n'   "$C_RED" "$C_RESET" "$*"; }
info() { printf '%s[INFO]%s %s\n'   "$C_CYAN" "$C_RESET" "$*"; }
hdr()  { printf '\n%s==> %s%s\n'    "$C_BOLD" "$*" "$C_RESET"; }

# Resolve repo root from this file: scripts/pi/common.sh → repo root
script_dir() {
  local src="${BASH_SOURCE[0]}"
  while [[ -L "$src" ]]; do
    local dir
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  cd -P "$(dirname "$src")" && pwd
}

repo_root() {
  # scripts/pi → ../..
  local d
  d="$(script_dir)"
  cd "$d/../.." && pwd
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

# Debian/Ubuntu/RPi OS package installed?
pkg_installed() {
  local pkg="$1"
  if have_cmd dpkg-query; then
    dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"
  else
    return 1
  fi
}

# Python import in a given interpreter
py_import_ok() {
  local py="$1"
  local mod="$2"
  "$py" -c "import $mod" >/dev/null 2>&1
}
