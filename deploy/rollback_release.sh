#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "rollback_release.sh must run as root" >&2
  exit 2
fi

APP_ROOT="${BOB_APP_ROOT:-/opt/bob}"
TARGET_SHA="${1:-}"
if [[ ! "$TARGET_SHA" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "usage: rollback_release.sh <40-character-release-sha>" >&2
  exit 3
fi

TARGET="$APP_ROOT/releases/$TARGET_SHA"
if [[ ! -d "$TARGET" ]]; then
  echo "release not installed: $TARGET" >&2
  exit 4
fi
if [[ ! -f "$TARGET/bob_api_server.py" || ! -f "$TARGET/requirements.txt" ]]; then
  echo "release is incomplete: $TARGET" >&2
  exit 5
fi

ln -sfn "$TARGET" "$APP_ROOT/current"
echo "Bob current release now points to $TARGET_SHA"

if [[ "${BOB_RESTART_AFTER_ROLLBACK:-0}" == "1" ]]; then
  systemctl restart bob-api.service
  if systemctl is-enabled --quiet chatgpt-bridge.service; then
    systemctl restart chatgpt-bridge.service
  fi
  echo "Bob services restarted by explicit BOB_RESTART_AFTER_ROLLBACK=1"
else
  echo "Services were not restarted. Set BOB_RESTART_AFTER_ROLLBACK=1 only after readiness checks."
fi
