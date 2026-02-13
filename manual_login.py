#!/usr/bin/env python3
"""
Manual login script - Opens browser for you to log in to ChatGPT
Run this ONCE before starting the server.
"""
from playwright.sync_api import sync_playwright
import time

print("\n" + "="*60)
print("ChatGPT Manual Login")
print("="*60)
print("\nThis will open a browser window.")
print("Please log in to ChatGPT and wait for the chat interface.")
print("The browser will stay open for 2 minutes.")
print("After you're logged in, you can close this script with Ctrl+C")
print("="*60 + "\n")

with open("profile_config.txt", "r") as f:
    profile_path = f.read().strip()

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
    page.goto("https://chat.openai.com")

    print("✓ Browser opened!")
    print("\n" + "="*60)
    print("👉 LOG IN NOW in the browser window")
    print("="*60)
    print("\nWaiting 120 seconds...")
    print("Press Ctrl+C when done logging in.\n")

    try:
        time.sleep(120)
    except KeyboardInterrupt:
        print("\n\n✓ Login session saved!")

    browser.close()

print("\n✅ Done! You can now start the server:")
print("   python3 chatgpt_api_server.py\n")
