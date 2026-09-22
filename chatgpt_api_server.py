#!/usr/bin/env python3
"""
ChatGPT Web API Server (Thread-safe version)
Uses a single dedicated thread for all Playwright operations
"""
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import threading
import queue
import time
import logging
import os
import re
import sys
from urllib.parse import urlsplit

from profile_config import load_profile_path

app = Flask(__name__)

CHATGPT_TARGET_URL = os.environ.get("CHATGPT_TARGET_URL", "https://chatgpt.com/").strip()
CHATGPT_CAPTURE_MODE = os.environ.get("CHATGPT_CAPTURE_MODE", "copy").strip().lower()
if CHATGPT_CAPTURE_MODE not in {"copy", "legacy_dom"}:
    raise RuntimeError("CHATGPT_CAPTURE_MODE must be 'copy' or 'legacy_dom'")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Task queue for browser operations
task_queue = queue.Queue()
result_queue = queue.Queue()
is_ready = False
startup_error = None
browser_thread = None

def browser_worker():
    """Dedicated thread for all browser operations"""
    global is_ready, startup_error

    profile_path = load_profile_path()

    if not os.path.exists(profile_path):
        startup_error = (f"Profile not found at: {profile_path}. "
                         "Run: python3 manual_login.py")
        logging.error(f"❌ {startup_error}")
        return

    logging.info(f"Using profile: {profile_path}")

    playwright = None
    browser_context = None
    try:
        playwright = sync_playwright().start()

        browser_context = playwright.chromium.launch_persistent_context(
            profile_path,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()

        logging.info(f"🌐 Navigating to ChatGPT target: {CHATGPT_TARGET_URL}")
        page.goto(CHATGPT_TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        origin_parts = urlsplit(page.url)
        origin = f"{origin_parts.scheme}://{origin_parts.netloc}"
        try:
            browser_context.grant_permissions(
                ["clipboard-read", "clipboard-write"],
                origin=origin,
            )
        except Exception as e:
            logging.warning(f"Could not pre-grant clipboard permissions: {e}")
    except Exception as e:
        startup_error = f"Browser failed to start: {e}"
        logging.error(f"❌ {startup_error}")
        # Don't strand a Chromium process if we got partway through startup.
        for closer in (getattr(browser_context, 'close', None),
                       getattr(playwright, 'stop', None)):
            try:
                if closer:
                    closer()
            except Exception:
                pass
        return

    # Check if chat interface is ready
    try:
        textarea = find_textarea(page, timeout=10)
        if textarea:
            is_ready = True
            logging.info("✅ Chat interface ready!")
        else:
            logging.warning("⚠️  Could not find textarea, but continuing...")
            is_ready = True  # Try anyway
    except Exception as e:
        logging.warning(f"⚠️  Initial check failed: {e}, but continuing...")
        is_ready = True

    # Process tasks from queue
    while True:
        try:
            task = task_queue.get()

            if task is None:  # Shutdown signal
                break

            task_type = task.get('type')

            if task_type == 'send_message':
                result = send_message(page, task['prompt'])
                result_queue.put(result)

            elif task_type == 'new_chat':
                result = start_new_chat(page)
                result_queue.put(result)

        except Exception as e:
            logging.error(f"Error in browser worker: {e}")
            result_queue.put({"success": False, "error": str(e)})

    # Cleanup
    browser_context.close()
    playwright.stop()

def find_textarea(page, timeout=10):
    """Find the chat textarea"""
    start_time = time.time()

    selectors = [
        '#prompt-textarea',
        'textarea[placeholder*="Message"]',
        'textarea[placeholder*="message"]',
        'textarea[data-id="root"]',
        'textarea[id*="prompt"]',
        'textarea',
        'div[contenteditable="true"]'
    ]

    while time.time() - start_time < timeout:
        for selector in selectors:
            try:
                elements = page.locator(selector).all()
                for elem in elements:
                    if elem.is_visible():
                        logging.info(f"✓ Found input: {selector}")
                        return elem
            except:
                pass
        time.sleep(0.5)

    return None

def send_message(page, prompt_text):
    """Send message and get response"""
    try:
        logging.info(f"📤 Sending: {prompt_text[:100]}...")

        # Find textarea
        textarea = find_textarea(page, timeout=15)
        if not textarea:
            return {"success": False, "error": "Could not find chat input"}

        # Click and type
        textarea.click()
        time.sleep(0.3)

        # Clear and type message
        textarea.fill("")
        time.sleep(0.2)
        textarea.type(prompt_text, delay=20)
        time.sleep(0.5)

        # Send
        page.keyboard.press("Enter")
        logging.info("✓ Message sent, waiting for response...")

        time.sleep(3)

        # Wait for response completion
        try:
            # Wait for stop button to appear
            page.wait_for_selector(
                'button[aria-label*="Stop"], button[aria-label*="stop"]',
                timeout=5000,
                state='visible'
            )
            logging.info("✓ Response started...")

            # Wait for it to disappear (response complete)
            page.wait_for_selector(
                'button[aria-label*="Stop"], button[aria-label*="stop"]',
                timeout=180000,
                state='hidden'
            )
            logging.info("✓ Response complete!")
        except:
            logging.warning("Stop button not detected, using time-based wait...")
            time.sleep(5)

        time.sleep(1.5)

        # Capture response through the visible Copy action by default.
        response_text = capture_response(page)

        if not response_text:
            return {
                "success": False,
                "error": f"Could not capture response using mode: {CHATGPT_CAPTURE_MODE}"
            }

        logging.info(f"📥 Got response ({len(response_text)} chars)")

        return {
            "success": True,
            "response": response_text.strip(),
            "prompt": prompt_text
        }

    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

def capture_response(page):
    """Capture the last assistant response.

    Default path clicks ChatGPT's visible Copy control and reads the browser
    clipboard. Direct DOM text extraction exists only as an explicit legacy
    compatibility mode.
    """
    if CHATGPT_CAPTURE_MODE == "copy":
        copy_candidates = []
        selectors = [
            'button[aria-label*="Copy"]',
            'button[aria-label*="copy"]',
            'button[title*="Copy"]',
            'button[title*="copy"]',
        ]
        for selector in selectors:
            try:
                copy_candidates.extend(page.locator(selector).all())
            except Exception:
                pass

        try:
            copy_candidates.extend(page.get_by_role(
                "button",
                name=re.compile("copy", re.IGNORECASE),
            ).all())
        except Exception:
            pass

        seen = set()
        unique = []
        for candidate in copy_candidates:
            try:
                key = candidate.evaluate("(el) => el.outerHTML")
            except Exception:
                key = str(id(candidate))
            if key not in seen:
                seen.add(key)
                unique.append(candidate)

        for candidate in reversed(unique):
            try:
                if not candidate.is_visible():
                    continue
                candidate.click()
                time.sleep(0.4)
                copied = page.evaluate("navigator.clipboard.readText()")
                if isinstance(copied, str) and copied.strip():
                    return copied.strip()
            except Exception:
                continue
        return None

    # Explicit compatibility escape hatch only.
    try:
        messages = page.locator('[data-message-author-role="assistant"]').all()
        if messages:
            return messages[-1].inner_text().strip()
    except Exception:
        pass
    try:
        articles = page.locator("article").all()
        if len(articles) >= 2:
            return articles[-1].inner_text().strip()
    except Exception:
        pass
    return None


def start_new_chat(page):
    """Start a new chat"""
    try:
        logging.info("🔄 Starting new chat...")
        page.goto(CHATGPT_TARGET_URL, wait_until="domcontentloaded")
        time.sleep(3)

        textarea = find_textarea(page, timeout=10)
        if textarea:
            return {"success": True, "message": "New chat started"}
        else:
            return {"success": False, "error": "Could not verify new chat"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/chat', methods=['POST'])
def chat():
    """Send a prompt to ChatGPT"""
    if not is_ready:
        return jsonify({"success": False, "error": "Server not ready"}), 503

    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"success": False, "error": "Missing 'prompt' field"}), 400

    prompt = data['prompt']
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"success": False, "error": "Prompt must be non-empty string"}), 400

    # Queue the task
    task_queue.put({'type': 'send_message', 'prompt': prompt})

    # Wait for result (with timeout)
    try:
        result = result_queue.get(timeout=200)  # 200 second timeout
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except queue.Empty:
        return jsonify({"success": False, "error": "Request timed out"}), 504

@app.route('/new-chat', methods=['POST'])
def new_chat():
    """Start a new chat"""
    if not is_ready:
        return jsonify({"success": False, "error": "Server not ready"}), 503

    task_queue.put({'type': 'new_chat'})

    try:
        result = result_queue.get(timeout=30)
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except queue.Empty:
        return jsonify({"success": False, "error": "Request timed out"}), 504

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    if startup_error:
        return jsonify({
            "status": "error",
            "ready": False,
            "error": startup_error
        }), 503

    return jsonify({
        "status": "running" if is_ready else "initializing",
        "ready": is_ready
    }), 200

@app.route('/status', methods=['GET'])
def status():
    """Server status"""
    return jsonify({
        "server": "running",
        "browser_ready": is_ready,
        "profile_path": load_profile_path(),
        "target_url": CHATGPT_TARGET_URL,
        "capture_mode": CHATGPT_CAPTURE_MODE,
        "endpoints": {
            "chat": "POST /chat",
            "new_chat": "POST /new-chat",
            "health": "GET /health",
            "status": "GET /status"
        }
    }), 200

if __name__ == '__main__':
    print("\n" + "="*60)
    print("ChatGPT API Server (Thread-Safe)")
    print("="*60)

    profile_path = load_profile_path()
    if not os.path.exists(profile_path):
        print(f"\n❌ No profile found at: {profile_path}")
        print("Please run: python3 manual_login.py")
        sys.exit(1)

    # Start browser worker thread
    browser_thread = threading.Thread(target=browser_worker, daemon=True)
    browser_thread.start()

    # Wait for browser to be ready — bail out if the worker died during startup
    # instead of spinning here forever.
    print("\nInitializing browser...")
    while not is_ready:
        if startup_error is not None or not browser_thread.is_alive():
            print(f"\n❌ {startup_error or 'Browser worker exited unexpectedly.'}")
            sys.exit(1)
        time.sleep(0.5)

    print("\n" + "="*60)
    print("🚀 Server is running on http://localhost:5001")
    print("="*60)
    print("\nEndpoints:")
    print("  POST http://localhost:5001/chat")
    print("  POST http://localhost:5001/new-chat")
    print("  GET  http://localhost:5001/health")
    print("\nExample:")
    print('  curl -X POST http://localhost:5001/chat \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"prompt": "Hello!"}\'')
    print("\n" + "="*60 + "\n")

    try:
        host = os.environ.get("CHATGPT_BRIDGE_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = int(os.environ.get("CHATGPT_BRIDGE_PORT", "5001"))
        app.run(host=host, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        task_queue.put(None)  # Signal shutdown
        print("✓ Goodbye!")
