#!/bin/bash
# =============================================================================
# Armature Update Checker (check-update.sh)
# Non-blocking version checker with 24h TTL cache, 1h failure backoff,
# and POSIX semver comparison.
# =============================================================================

set -e

INSTALLED_VERSION="0.22.4"

# --- Upstream Configuration ---
UPSTREAM_MODE="github_raw"
GITHUB_RAW_INSTALLER="https://raw.githubusercontent.com/drinkspiller/armature-cdd/main/install.sh"

CACHE_DIR="${HOME}/.cache/armature"
CACHE_FILE="${CACHE_DIR}/update_check.json"
NOW="$(date +%s)"
TTL_SECONDS=86400
BACKOFF_SECONDS=3600

mkdir -p "${CACHE_DIR}" 2>/dev/null || exit 0

# --- Helper: Strict POSIX Semver Comparison (returns 0 if $1 > $2) ---
semver_gt() {
  local ver1="$1"
  local ver2="$2"
  awk -v v1="$ver1" -v v2="$ver2" 'BEGIN {
    split(v1, a, ".");
    split(v2, b, ".");
    for (i = 1; i <= 3; i++) {
      n1 = a[i] + 0;
      n2 = b[i] + 0;
      if (n1 > n2) exit 0;
      if (n1 < n2) exit 1;
    }
    exit 1;
  }'
}

# --- Helper: Read JSON field using awk ---
read_json_field() {
  local key="$1"
  local default_val="$2"
  if [[ ! -f "${CACHE_FILE}" ]]; then
    echo "${default_val}"
    return
  fi
  local val
  val="$(awk -F'"' -v k="$key" '$2 == k { print $4 }' "${CACHE_FILE}" 2>/dev/null || true)"
  if [[ -z "${val}" ]]; then
    echo "${default_val}"
  else
    echo "${val}"
  fi
}

# --- Helper: Write JSON cache atomically ---
write_cache() {
  local checked="$1"
  local notified="$2"
  local latest="$3"
  local backoff="$4"
  local tmp_file="${CACHE_FILE}.tmp.$$"
  cat > "${tmp_file}" <<EOF
{
  "last_checked_timestamp": "${checked}",
  "last_notified_timestamp": "${notified}",
  "latest_version": "${latest}",
  "backoff_until": "${backoff}"
}
EOF
  mv -f "${tmp_file}" "${CACHE_FILE}" 2>/dev/null || rm -f "${tmp_file}"
}

LAST_CHECKED="$(read_json_field "last_checked_timestamp" "0")"
LAST_NOTIFIED="$(read_json_field "last_notified_timestamp" "0")"
CACHED_LATEST="$(read_json_field "latest_version" "${INSTALLED_VERSION}")"
BACKOFF_UNTIL="$(read_json_field "backoff_until" "0")"

UPGRADE_CMD="curl -fsSL ${GITHUB_RAW_INSTALLER} | bash -s -- --update"

# 1. Check failure backoff window
if (( NOW < BACKOFF_UNTIL )); then
  exit 0
fi

# 2. If within 24h check TTL, use cached latest version
if (( NOW - LAST_CHECKED < TTL_SECONDS )); then
  UPSTREAM_VERSION="${CACHED_LATEST}"
else
  # 3. Perform upstream check with hard 2s timeout
  UPSTREAM_VERSION="$(curl -fsSL --max-time 2 "${GITHUB_RAW_INSTALLER}" 2>/dev/null | awk -F'"' '/^VERSION="/ { print $2; exit }' || true)"

  # Handle failure/timeout: set 1-hour backoff and exit silently
  if [[ -z "${UPSTREAM_VERSION}" ]]; then
    write_cache "${LAST_CHECKED}" "${LAST_NOTIFIED}" "${CACHED_LATEST}" "$(( NOW + BACKOFF_SECONDS ))"
    exit 0
  fi

  # Update cache with newly discovered upstream version
  LAST_CHECKED="${NOW}"
  CACHED_LATEST="${UPSTREAM_VERSION}"
  write_cache "${LAST_CHECKED}" "${LAST_NOTIFIED}" "${CACHED_LATEST}" "0"
fi

# 4. Evaluate if update is strictly greater and notification is due (once per 24h)
if semver_gt "${UPSTREAM_VERSION}" "${INSTALLED_VERSION}"; then
  if (( NOW - LAST_NOTIFIED >= TTL_SECONDS )); then
    LAST_NOTIFIED="${NOW}"
    write_cache "${LAST_CHECKED}" "${LAST_NOTIFIED}" "${UPSTREAM_VERSION}" "0"
    echo "UPDATE_AVAILABLE|${INSTALLED_VERSION}|${UPSTREAM_VERSION}|${UPGRADE_CMD}"
  fi
fi

exit 0
