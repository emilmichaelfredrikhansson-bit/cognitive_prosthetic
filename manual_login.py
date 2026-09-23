#!/usr/bin/env python3
"""
Manual login script - Opens browser for you to log in to ChatGPT
Run this ONCE before starting the server.

Usage:
    python3 manual_login.py                  # use the configured/default profile
    python3 manual_login.py ./my_profile     # use (and remember) a custom profile
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

from profile_config import (
    CONFIG_FILENAME,
    DEFAULT_PROFILE_NAME,
    ENV_VAR,
    load_profile_path,
    save_profile_path,
)

LOGIN_TIMEOUT_SECONDS = 120
CHATGPT_TARGET_URL = os.environ.get("CHATGPT_TARGET_URL", "https://chatgpt.com/").strip() or "https://chatgpt.com/"


def resolve_profile_path(argv):
    """Pick the profile path for this run and persist it for the server."""
    if len(argv) > 1:
        os.environ[ENV_VAR] = argv[1]

    profile_path = load_profile_path()

    # profile_config.txt is gitignored, so a fresh clone will not have one.
    # Create it here rather than requiring the user to author it by hand.
    if not os.path.exists(profile_path):
        print(f"No existing profile at {profile_path} — a new one will be created.")

    config_path = save_profile_path(profile_path)
    print(f"Saved profile path to {config_path}")

    return profile_path


def main():
    print("\n" + "=" * 60)
    print("ChatGPT Manual Login")
    print("=" * 60)
    print("\nThis will open a browser window.")
    print("Please log in to ChatGPT and wait for the chat interface.")
    print("Press ENTER here once you are logged in (or Ctrl+C).")
    print("=" * 60 + "\n")

    profile_path = resolve_profile_path(sys.argv)
    print(f"Using profile: {profile_path}\n")

    with sync_playwright() as p:
        print("🌐 Opening browser...")
        browser = p.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto(CHATGPT_TARGET_URL)

        print("✓ Browser opened!")
        print("\n" + "=" * 60)
        print("👉 LOG IN NOW in the browser window")
        print("=" * 60 + "\n")

        try:
            # Interactive terminal: wait for the user. Non-interactive (piped or
            # backgrounded) stdin: fall back to a fixed wait.
            if sys.stdin and sys.stdin.isatty():
                input("Press ENTER when you are logged in... ")
            else:
                print(f"stdin is not interactive — waiting {LOGIN_TIMEOUT_SECONDS}s...")
                time.sleep(LOGIN_TIMEOUT_SECONDS)
        except (KeyboardInterrupt, EOFError):
            print()

        print("\n✓ Login session saved!")
        browser.close()

    print("\n✅ Done! You can now start the server:")
    print("   python bob_local.py\n")
    print(f"(Profile path is stored in {CONFIG_FILENAME}; "
          f"override it with {ENV_VAR} or edit that file. "
          f"Default: ./{DEFAULT_PROFILE_NAME})\n")


if __name__ == '__main__':
    main()
