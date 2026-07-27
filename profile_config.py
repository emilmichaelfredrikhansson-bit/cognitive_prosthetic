#!/usr/bin/env python3
"""
Shared resolution of the browser profile path.

The profile directory holds the persistent Chromium session created by
`manual_login.py` and consumed by `chatgpt_api_server.py`.

Resolution order (first hit wins):
  1. CHATGPT_PROFILE_PATH environment variable
  2. profile_config.txt next to this file
  3. DEFAULT_PROFILE_NAME ("./chatgpt_profile")

`profile_config.txt` is gitignored (it is machine-local), so it will not exist
on a fresh clone. That is expected: the default is used and the file is written
on first login instead of being required up front.
"""
import os

# Anchor everything to the repo directory so the scripts work regardless of the
# shell's current working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILENAME = "profile_config.txt"
CONFIG_PATH = os.path.join(BASE_DIR, CONFIG_FILENAME)

DEFAULT_PROFILE_NAME = "chatgpt_profile"
ENV_VAR = "CHATGPT_PROFILE_PATH"


def _resolve(path):
    """Expand ~ and make relative paths relative to the repo, not the cwd."""
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return os.path.normpath(path)


def load_profile_path():
    """Return the absolute profile path, falling back to the default."""
    env_value = os.environ.get(ENV_VAR, "").strip()
    if env_value:
        return _resolve(env_value)

    try:
        with open(CONFIG_PATH, "r") as f:
            configured = f.read().strip()
        if configured:
            return _resolve(configured)
    except OSError:
        pass

    return _resolve(DEFAULT_PROFILE_NAME)


def save_profile_path(profile_path):
    """Persist the chosen profile path to profile_config.txt."""
    with open(CONFIG_PATH, "w") as f:
        f.write(profile_path + "\n")
    return CONFIG_PATH
