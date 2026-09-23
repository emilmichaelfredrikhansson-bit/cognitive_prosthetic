#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "install_runtime.sh must run as root" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="${BOB_APP_ROOT:-/opt/bob}"
ENV_DIR="${BOB_ENV_DIR:-/etc/bob}"
STATE_DIR="${BOB_STATE_DIR:-/var/lib/bob}"
RUNTIME_USER="${BOB_RUNTIME_USER:-bob}"
RUNTIME_GROUP="${BOB_RUNTIME_GROUP:-bob}"
SYSTEMD_DIR="${BOB_SYSTEMD_DIR:-/etc/systemd/system}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if command -v apt-get >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq git python3-venv xvfb xauth >/dev/null
fi
command -v "$PYTHON_BIN" >/dev/null
command -v git >/dev/null
command -v xvfb-run >/dev/null

if ! getent group "$RUNTIME_GROUP" >/dev/null; then
  groupadd --system "$RUNTIME_GROUP"
fi
if ! id "$RUNTIME_USER" >/dev/null 2>&1; then
  useradd --system --gid "$RUNTIME_GROUP" --home-dir "$STATE_DIR" --shell /usr/sbin/nologin "$RUNTIME_USER"
fi

install -d -m 0755 -o root -g root "$APP_ROOT" "$APP_ROOT/releases"
install -d -m 0750 -o root -g "$RUNTIME_GROUP" "$STATE_DIR"
install -d -m 0700 -o "$RUNTIME_USER" -g "$RUNTIME_GROUP" "$STATE_DIR/chatgpt-profile"
install -d -m 0755 -o root -g root "$ENV_DIR"

if [[ -d "$ROOT_DIR/.git" ]]; then
  SOURCE_SHA="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  RELEASE_SHA="${BOB_RELEASE_SHA:-$SOURCE_SHA}"
else
  SOURCE_SHA=""
  RELEASE_SHA="${BOB_RELEASE_SHA:-}"
fi
if [[ -z "$RELEASE_SHA" || ! "$RELEASE_SHA" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "BOB_RELEASE_SHA must be a full 40-character Git commit SHA" >&2
  exit 3
fi
if [[ -n "$SOURCE_SHA" && "$SOURCE_SHA" != "$RELEASE_SHA" ]]; then
  echo "checkout SHA $SOURCE_SHA does not match requested BOB_RELEASE_SHA $RELEASE_SHA" >&2
  exit 4
fi

RELEASE_DIR="$APP_ROOT/releases/$RELEASE_SHA"
if [[ ! -d "$RELEASE_DIR" ]]; then
  install -d -m 0755 -o root -g root "$RELEASE_DIR"
  tar -C "$ROOT_DIR" \
    --exclude=.git \
    --exclude=chatgpt_profile \
    --exclude=default_profile \
    --exclude='*_profile' \
    --exclude='*.env' \
    --exclude=profile_config.txt \
    -cf - . | tar -C "$RELEASE_DIR" -xf -
  chown -R root:root "$RELEASE_DIR"
  chmod -R go-w "$RELEASE_DIR"
fi

if [[ ! -x "$APP_ROOT/venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$APP_ROOT/venv"
fi
"$APP_ROOT/venv/bin/python" -m pip install --disable-pip-version-check -r "$RELEASE_DIR/requirements.txt"
"$APP_ROOT/venv/bin/playwright" install-deps chromium
install -d -m 0755 -o root -g "$RUNTIME_GROUP" "$APP_ROOT/ms-playwright"
PLAYWRIGHT_BROWSERS_PATH="$APP_ROOT/ms-playwright" "$APP_ROOT/venv/bin/playwright" install chromium
chown -R root:"$RUNTIME_GROUP" "$APP_ROOT/ms-playwright"
chmod -R g+rX,o-rwx "$APP_ROOT/ms-playwright"

if [[ ! -e "$ENV_DIR/bob.env" ]]; then
  install -m 0600 -o root -g root /dev/null "$ENV_DIR/bob.env"
  cat > "$ENV_DIR/bob.env" <<'ENVEOF'
BOB_HOST=127.0.0.1
BOB_PORT=5002
BOB_WORKSPACE_DIR=/opt/bob/current/workspaces
CHATGPT_BRIDGE_HOST=127.0.0.1
CHATGPT_BRIDGE_PORT=5001
CHATGPT_BRIDGE_URL=http://127.0.0.1:5001
CHATGPT_CAPTURE_MODE=copy
CHATGPT_TARGET_URL=https://chatgpt.com/
GITHUB_TOKEN=
SUPABASE_ACCESS_TOKEN=
HF_TOKEN=
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ACCOUNT_ID=
ENVEOF
  chmod 0600 "$ENV_DIR/bob.env"
  chown root:root "$ENV_DIR/bob.env"
fi

install -m 0644 "$RELEASE_DIR/deploy/systemd/bob-api.service" "$SYSTEMD_DIR/bob-api.service"
install -m 0644 "$RELEASE_DIR/deploy/systemd/chatgpt-bridge.service" "$SYSTEMD_DIR/chatgpt-bridge.service"
ln -sfn "$RELEASE_DIR" "$APP_ROOT/current"

systemctl daemon-reload
systemctl enable bob-api.service chatgpt-bridge.service >/dev/null

echo "Bob runtime installed at commit $RELEASE_SHA"
echo "Secrets are not installed. Edit $ENV_DIR/bob.env as root, then run deploy/runtime_doctor.py and bob.preflight."
