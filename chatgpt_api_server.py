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
import ipaddress
import sys
import uuid
from urllib.parse import urlsplit

from profile_config import load_profile_path

# Windows/remote shells may inherit a legacy code page such as cp1252. Bob's
# human-facing logs contain Unicode, so make stdio encoding deterministic without
# letting an unrenderable glyph crash the bridge process.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

app = Flask(__name__)

BOB_CHATGPT_PROJECT_NAME = os.environ.get("BOB_CHATGPT_PROJECT_NAME", "Bob").strip() or "Bob"
BOB_CHATGPT_PROJECT_URL = os.environ.get("BOB_CHATGPT_PROJECT_URL", "").strip()
CHATGPT_TARGET_URL = (BOB_CHATGPT_PROJECT_URL or os.environ.get("CHATGPT_TARGET_URL", "")).strip()
CHATGPT_CAPTURE_MODE = os.environ.get("CHATGPT_CAPTURE_MODE", "copy").strip().lower()
BOB_COMPANION_UI_URL = os.environ.get("BOB_COMPANION_UI_URL", "http://127.0.0.1:5002/").strip()

def parse_timeout_seconds(value, default=360):
    raw = str(value or "").strip()
    if not raw:
        return default
    try:
        timeout = int(raw)
    except ValueError as exc:
        raise RuntimeError("CHATGPT_RESPONSE_TIMEOUT_SECONDS must be an integer") from exc
    if not 30 <= timeout <= 900:
        raise RuntimeError("CHATGPT_RESPONSE_TIMEOUT_SECONDS must be between 30 and 900")
    return timeout

CHATGPT_RESPONSE_TIMEOUT_SECONDS = parse_timeout_seconds(
    os.environ.get("CHATGPT_RESPONSE_TIMEOUT_SECONDS")
)
if CHATGPT_CAPTURE_MODE not in {"copy", "legacy_dom"}:
    raise RuntimeError("CHATGPT_CAPTURE_MODE must be 'copy' or 'legacy_dom'")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Task queue for browser operations. Responses are request-correlated; there is
# intentionally no shared result queue because late completion from one request
# must never be consumable by another request.
task_queue = queue.Queue()
request_registry_lock = threading.RLock()
request_registry = {}
MAX_TRACKED_BROWSER_REQUESTS = 100
is_ready = False
startup_error = None
browser_thread = None
runtime_error = None
browser_generation = 0


def _normalize_request_id(value=None):
    request_id = str(value or f"bridge-{uuid.uuid4().hex[:16]}").strip()
    if not request_id or len(request_id) > 128:
        raise ValueError("request_id must contain 1..128 characters")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", request_id):
        raise ValueError("request_id contains unsupported characters")
    return request_id


def _prune_request_registry_locked():
    if len(request_registry) <= MAX_TRACKED_BROWSER_REQUESTS:
        return
    terminal = sorted(
        (
            item
            for item in request_registry.values()
            if item.get("state") in {"DONE", "FAILED", "TIMED_OUT"}
        ),
        key=lambda item: item.get("finished_at") or item.get("created_at") or 0,
    )
    while len(request_registry) > MAX_TRACKED_BROWSER_REQUESTS and terminal:
        item = terminal.pop(0)
        request_registry.pop(item["request_id"], None)


def make_browser_task(task_type, *, request_id=None, tags=None, **payload):
    request_id = _normalize_request_id(request_id)
    response_queue = queue.Queue(maxsize=1)
    now = time.time()
    with request_registry_lock:
        if request_id in request_registry:
            raise ValueError(f"duplicate browser request_id: {request_id}")
        request_registry[request_id] = {
            "request_id": request_id,
            "type": str(task_type),
            "state": "QUEUED",
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "tags": dict(tags or {}),
            "error": None,
        }
        _prune_request_registry_locked()
    task = {
        "type": str(task_type),
        "_request_id": request_id,
        "_response_queue": response_queue,
        **payload,
    }
    return task, response_queue


def update_browser_request(task, state, *, error=None):
    request_id = task.get("_request_id")
    if not request_id:
        return
    now = time.time()
    with request_registry_lock:
        item = request_registry.get(request_id)
        if item is None:
            return
        item["state"] = str(state)
        if state == "RUNNING" and item.get("started_at") is None:
            item["started_at"] = now
        if state in {"DONE", "FAILED", "TIMED_OUT"}:
            item["finished_at"] = now
        if error is not None:
            item["error"] = str(error)
        _prune_request_registry_locked()


def deliver_browser_result(task, result):
    result = dict(result or {
        "success": False,
        "error": "browser task produced no result",
    })
    request_id = task.get("_request_id")
    if request_id:
        result.setdefault("request_id", request_id)
    tags = {}
    with request_registry_lock:
        item = request_registry.get(request_id)
        if item is not None:
            tags = dict(item.get("tags") or {})
    for key, value in tags.items():
        result.setdefault(key, value)
    update_browser_request(
        task,
        "DONE" if result.get("success") else "FAILED",
        error=result.get("error"),
    )
    response_queue = task.get("_response_queue")
    if response_queue is not None:
        try:
            response_queue.put_nowait(result)
        except queue.Full:
            pass
    return result


def submit_browser_task(
    task_type,
    *,
    timeout,
    request_id=None,
    tags=None,
    **payload,
):
    task, response_queue = make_browser_task(
        task_type,
        request_id=request_id,
        tags=tags,
        **payload,
    )
    task_queue.put(task)
    try:
        result = response_queue.get(timeout=timeout)
        return result, (200 if result.get("success") else 500)
    except queue.Empty:
        update_browser_request(task, "TIMED_OUT", error="Request timed out")
        result = {
            "success": False,
            "error": "Request timed out",
            "request_id": task["_request_id"],
        }
        for key, value in dict(tags or {}).items():
            result.setdefault(key, value)
        return result, 504


def browser_request_status():
    now = time.time()
    with request_registry_lock:
        items = []
        for item in request_registry.values():
            public = dict(item)
            public["age_seconds"] = round(
                now - float(item.get("created_at") or now), 3
            )
            items.append(public)
    items.sort(key=lambda item: item.get("created_at") or 0, reverse=True)
    active = [
        item for item in items if item.get("state") in {"QUEUED", "RUNNING"}
    ]
    return {
        "active_count": len(active),
        "active": active,
        "recent": items[:20],
    }

def is_browser_closed_error(value):
    """Classify Playwright target/context closure as recoverable browser loss."""
    text = str(value or "").casefold()
    markers = (
        "target page, context or browser has been closed",
        "target closed",
        "page has been closed",
        "page is closed",
        "context has been closed",
        "browser has been closed",
        "browser is closed",
    )
    return any(marker in text for marker in markers)


def browser_result_needs_recovery(result):
    return bool(
        isinstance(result, dict)
        and not result.get("success")
        and is_browser_closed_error(result.get("error"))
    )


def task_allows_transparent_browser_retry(task_type):
    """Only context-independent browser tasks may be retried after session loss."""
    return task_type in {"cognition_request", "new_chat", "show_ui"}


def browser_session_is_live(page, browser_context):
    """Actively probe Chromium from the Playwright-owning worker thread."""
    try:
        if page is None or browser_context is None or page.is_closed():
            return False
        page.evaluate("() => true")
        return True
    except Exception:
        return False


def validate_chatgpt_project_url(url):
    """Require an explicit non-root ChatGPT target for Bob cognition."""
    value = str(url or "").strip()
    if not value:
        raise ValueError("BOB_CHATGPT_PROJECT_URL must be configured for normal Bob runtime")
    parts = urlsplit(value)
    if parts.scheme != "https" or (parts.hostname or "").lower() not in {"chatgpt.com", "www.chatgpt.com"}:
        raise ValueError("Bob ChatGPT project URL must be an https://chatgpt.com/ URL")
    if parts.path in {"", "/"}:
        raise ValueError("Bob must target a dedicated ChatGPT Project URL, not the ChatGPT home page")
    return value


def validate_companion_ui_url(url):
    """Return a local companion URL or fail closed for non-loopback targets."""
    value = str(url or "").strip()
    if not value:
        raise ValueError("BOB_COMPANION_UI_URL must not be empty")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("companion UI URL must be an absolute http(s) URL")
    host = parts.hostname.strip().lower()
    if host != "localhost":
        try:
            if not ipaddress.ip_address(host).is_loopback:
                raise ValueError("companion UI URL must use a loopback host")
        except ValueError as exc:
            if "loopback" in str(exc):
                raise
            raise ValueError("companion UI URL must use localhost or a loopback IP") from exc
    return value


def show_companion_ui(chatgpt_page, url):
    """Open/focus Bob in the same persistent browser while keeping ChatGPT available."""
    target = validate_companion_ui_url(url)
    target_parts = urlsplit(target)
    target_origin = f"{target_parts.scheme}://{target_parts.netloc}"
    for candidate in chatgpt_page.context.pages:
        try:
            current = urlsplit(candidate.url)
            current_origin = f"{current.scheme}://{current.netloc}"
            if current_origin == target_origin:
                candidate.goto(target, wait_until="domcontentloaded", timeout=15000)
                candidate.bring_to_front()
                return {"success": True, "url": candidate.url, "reused": True}
        except Exception:
            continue
    companion = chatgpt_page.context.new_page()
    companion.goto(target, wait_until="domcontentloaded", timeout=15000)
    companion.bring_to_front()
    return {"success": True, "url": companion.url, "reused": False}


def set_browser_state(ready, error=None):
    """Publish worker-owned browser liveness without exposing Playwright cross-thread."""
    global is_ready, runtime_error
    is_ready = bool(ready)
    runtime_error = None if ready else (str(error) if error else "browser unavailable")


def close_browser_context(browser_context):
    if browser_context is None:
        return
    try:
        browser_context.close()
    except Exception:
        pass


def launch_browser_session(playwright, profile_path):
    """Launch, project-bind, permission-bind, and authenticate one browser session."""
    global browser_generation
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

    project_url = validate_chatgpt_project_url(CHATGPT_TARGET_URL)
    logging.info(f"🌐 Navigating to dedicated ChatGPT project: {BOB_CHATGPT_PROJECT_NAME}")
    page.goto(project_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    origin_parts = urlsplit(page.url)
    origin = f"{origin_parts.scheme}://{origin_parts.netloc}"
    try:
        browser_context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin=origin,
        )
    except Exception as exc:
        logging.warning(f"Could not pre-grant clipboard permissions: {exc}")

    textarea = find_textarea(page, timeout=12)
    if not textarea:
        close_browser_context(browser_context)
        raise RuntimeError(
            "ChatGPT chat input was not found. The session may need login "
            "or the ChatGPT UI selectors may have changed."
        )

    browser_generation += 1
    generation = browser_generation

    def mark_context_closed():
        if generation == browser_generation:
            set_browser_state(False, "browser context closed")

    def mark_page_closed():
        if generation == browser_generation:
            set_browser_state(False, "ChatGPT page closed")

    try:
        browser_context.on("close", lambda _context=None: mark_context_closed())
        page.on("close", lambda _page=None: mark_page_closed())
    except Exception:
        pass

    set_browser_state(True)
    logging.info(f"✅ Chat interface ready! browser_generation={generation}")
    return browser_context, page


def execute_browser_task(page, task):
    task_type = task.get('type')
    if task_type == 'send_message':
        return send_message(page, task['prompt'])
    if task_type == 'cognition_request':
        fresh = start_new_chat(page)
        return send_message(page, task['prompt']) if fresh.get("success") else fresh
    if task_type == 'new_chat':
        return start_new_chat(page)
    if task_type == 'show_ui':
        return show_companion_ui(page, task.get('url') or BOB_COMPANION_UI_URL)
    return {"success": False, "error": f"unknown browser task: {task_type}"}


def browser_worker():
    """Dedicated thread for all browser operations with bounded self-recovery."""
    global is_ready, startup_error, runtime_error

    profile_path = load_profile_path()

    if not os.path.exists(profile_path):
        startup_error = (f"Profile not found at: {profile_path}. "
                         "Run: python3 manual_login.py")
        logging.error(f"❌ {startup_error}")
        return

    logging.info(f"Using profile: {profile_path}")

    playwright = None
    browser_context = None
    page = None
    try:
        playwright = sync_playwright().start()
        try:
            browser_context, page = launch_browser_session(playwright, profile_path)
            startup_error = None
        except Exception as exc:
            startup_error = f"Browser failed to start: {exc}"
            set_browser_state(False, startup_error)
            logging.error(f"❌ {startup_error}")
            return

        # Process tasks from queue. A dead Playwright target gets one bounded
        # browser-session recovery + retry; ordinary model/capture failures do not.
        while True:
            try:
                task = task_queue.get(timeout=1.0)
            except queue.Empty:
                if not browser_session_is_live(page, browser_context):
                    set_browser_state(False, "browser liveness heartbeat failed")
                    close_browser_context(browser_context)
                    browser_context = None
                    page = None
                    try:
                        browser_context, page = launch_browser_session(
                            playwright, profile_path
                        )
                        logging.info("♻️ Browser session recovered by idle heartbeat")
                    except Exception as exc:
                        set_browser_state(False, f"browser recovery failed: {exc}")
                continue

            if task is None:
                break

            update_browser_request(task, "RUNNING")
            result = None
            for attempt in range(2):
                if page is None or not is_ready:
                    try:
                        close_browser_context(browser_context)
                        browser_context, page = launch_browser_session(playwright, profile_path)
                        logging.info("♻️ Browser session recovered before task retry")
                    except Exception as exc:
                        set_browser_state(False, f"browser recovery failed: {exc}")
                        result = {"success": False, "error": runtime_error}
                        break

                try:
                    if page.is_closed():
                        result = {
                            "success": False,
                            "error": "ChatGPT page is closed",
                        }
                    else:
                        result = execute_browser_task(page, task)
                except Exception as exc:
                    result = {"success": False, "error": str(exc)}

                if browser_result_needs_recovery(result) and attempt == 0:
                    task_type = task.get("type")
                    logging.warning(
                        f"Browser target lost during {task_type}; "
                        "restarting persistent context once"
                    )
                    set_browser_state(False, result.get("error"))
                    close_browser_context(browser_context)
                    browser_context = None
                    page = None

                    if not task_allows_transparent_browser_retry(task_type):
                        try:
                            browser_context, page = launch_browser_session(
                                playwright, profile_path
                            )
                            logging.info(
                                "♻️ Browser transport recovered; stateful task not retried"
                            )
                        except Exception as exc:
                            set_browser_state(
                                False,
                                f"browser recovery failed: {exc}",
                            )
                        result = {
                            "success": False,
                            "error": (
                                "Stateful ChatGPT session was lost. Browser transport "
                                "was recovered, but the request was not retried because "
                                "prior conversation context cannot be assumed."
                            ),
                        }
                        break
                    continue
                break

            deliver_browser_result(task, result)
    except Exception as exc:
        set_browser_state(False, f"browser worker failed: {exc}")
        logging.error(f"Error in browser worker: {exc}")
    finally:
        set_browser_state(False, runtime_error or "browser worker stopped")
        close_browser_context(browser_context)
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass

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
        if page.is_closed():
            raise RuntimeError("ChatGPT page is closed")
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

def copy_candidates(scope):
    """Return de-duplicated visible Copy controls across supported UI locales."""
    candidates = []
    selectors = [
        'button[data-testid*="copy"]',
        'button[aria-label*="Copy"]',
        'button[aria-label*="copy"]',
        'button[aria-label*="Kopiera"]',
        'button[aria-label*="kopiera"]',
        'button[title*="Copy"]',
        'button[title*="copy"]',
        'button[title*="Kopiera"]',
        'button[title*="kopiera"]',
    ]
    for selector in selectors:
        try:
            candidates.extend(scope.locator(selector).all())
        except Exception:
            pass

    try:
        candidates.extend(scope.get_by_role(
            "button",
            name=re.compile(r"(copy|kopiera)", re.IGNORECASE),
        ).all())
    except Exception:
        pass

    seen = set()
    visible = []
    for candidate in candidates:
        try:
            if not candidate.is_visible():
                continue
            key = candidate.evaluate("(el) => el.outerHTML")
        except Exception:
            continue
        if key not in seen:
            seen.add(key)
            visible.append(candidate)
    return visible


def assistant_count(page):
    try:
        return page.locator('[data-message-author-role="assistant"]').count()
    except Exception:
        return 0


def assistant_copy_candidates(page):
    """Return the newest assistant turn's message-level Copy control.

    Code blocks can expose their own Copy/Kopiera button while the assistant is
    still streaming. Prefer ChatGPT's turn-action copy button and exclude
    controls explicitly labelled as code-copy fallbacks.
    """
    try:
        messages = page.locator('[data-message-author-role="assistant"]')
        count = messages.count()
        if count < 1:
            return []
        message = messages.nth(count - 1)
        for xpath in (
            "xpath=ancestor::article[1]",
            "xpath=ancestor::*[contains(@data-testid,'conversation-turn')][1]",
        ):
            try:
                container = message.locator(xpath)
                if not container.count():
                    continue

                preferred = []
                try:
                    preferred = container.locator(
                        'button[data-testid="copy-turn-action-button"]'
                    ).all()
                except Exception:
                    pass
                preferred = [
                    item for item in preferred
                    if item.is_visible() and item.is_enabled()
                ]
                if preferred:
                    return preferred

                fallbacks = []
                for candidate in copy_candidates(container):
                    try:
                        if not candidate.is_enabled():
                            continue
                        label = " ".join(filter(None, [
                            candidate.get_attribute("aria-label"),
                            candidate.get_attribute("title"),
                            candidate.get_attribute("data-testid"),
                        ])).lower()
                    except Exception:
                        label = ""
                    if "code" in label or "kod" in label:
                        continue
                    fallbacks.append(candidate)
                if fallbacks:
                    return fallbacks
            except Exception:
                pass
    except Exception:
        pass
    return []


CHATGPT_TRANSIENT_UI_PATTERNS = (
    (
        "RATE_LIMITED",
        re.compile(
            r"too many (?:concurrent )?requests|rate limit(?:ed)?|please slow down",
            re.IGNORECASE,
        ),
    ),
    (
        "USAGE_LIMIT",
        re.compile(
            r"you(?:'|’)ve reached[^\n]{0,120}limit|usage limit|come back later",
            re.IGNORECASE,
        ),
    ),
)


def detect_chatgpt_transient_ui_error(page):
    """Return a sanitized transient ChatGPT UI error category, if visible.

    Only alert/live-region/error surfaces are inspected. Raw UI text is never
    logged or returned so prompts/responses do not leak into diagnostics.
    """
    selectors = (
        '[role="alert"]',
        '[role="status"]',
        '[aria-live="assertive"]',
        '[aria-live="polite"]',
        '[data-sonner-toast]',
        '[data-testid*="error"]',
    )
    visible_text = []
    for selector in selectors:
        try:
            items = page.locator(selector)
            for index in range(min(items.count(), 12)):
                item = items.nth(index)
                if not item.is_visible():
                    continue
                text = item.inner_text(timeout=1000)
                if isinstance(text, str) and text.strip():
                    visible_text.append(text.strip())
        except Exception:
            continue

    if not visible_text:
        return None

    haystack = "\n".join(visible_text)
    for category, pattern in CHATGPT_TRANSIENT_UI_PATTERNS:
        if pattern.search(haystack):
            return category
    return None


def wait_for_new_assistant_copy(page, baseline_assistant_count, timeout=180):
    """Wait for completion, but surface a dead Playwright target immediately."""
    deadline = time.time() + timeout
    next_diagnostic_at = time.time()
    last_diagnostic = None
    while time.time() < deadline:
        try:
            if page.is_closed():
                raise RuntimeError("ChatGPT page is closed")
            transient_ui_error = detect_chatgpt_transient_ui_error(page)
            if transient_ui_error:
                logging.warning(
                    "ChatGPT transient UI state detected: %s",
                    transient_ui_error,
                )
                raise RuntimeError(
                    f"CHATGPT_TRANSIENT_UI:{transient_ui_error}"
                )
            current_assistant_count = assistant_count(page)
            if current_assistant_count > baseline_assistant_count:
                if assistant_copy_candidates(page):
                    return True
            if time.time() >= next_diagnostic_at:
                try:
                    author_roles = page.locator("[data-message-author-role]").evaluate_all(
                        "(els) => els.map((el) => el.getAttribute('data-message-author-role'))"
                    )
                    turn_copy_count = page.locator(
                        'button[data-testid="copy-turn-action-button"]'
                    ).count()
                    conversation_turn_count = page.locator(
                        '[data-testid*="conversation-turn"]'
                    ).count()
                    last_diagnostic = {
                        "baseline_assistant": baseline_assistant_count,
                        "assistant": current_assistant_count,
                        "author_roles": author_roles[-8:],
                        "turn_copy": turn_copy_count,
                        "conversation_turn": conversation_turn_count,
                    }
                    logging.info("Capture wait diagnostic: %s", last_diagnostic)
                except Exception as diag_exc:
                    logging.info("Capture wait diagnostic failed: %s", diag_exc)
                next_diagnostic_at = time.time() + 15
        except Exception as exc:
            if is_browser_closed_error(exc) or str(exc).startswith("CHATGPT_TRANSIENT_UI:"):
                raise
        time.sleep(0.5)
    logging.error("Capture wait timed out; last_diagnostic=%s", last_diagnostic)
    return False


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

        # Fill the complete prompt atomically. Compiled Bob contexts can be
        # thousands of characters; per-character typing can exceed Playwright's
        # action timeout before the message is even submitted.
        textarea.fill(prompt_text)
        time.sleep(0.5)

        # Track assistant turns before submission. User turns also expose Copy
        # controls, so a raw page-level Copy count is not sufficient completion
        # evidence.
        baseline_assistant_count = assistant_count(page)

        # Send
        page.keyboard.press("Enter")
        logging.info("✓ Message sent, waiting for response...")

        if CHATGPT_CAPTURE_MODE == "copy":
            if not wait_for_new_assistant_copy(
                page,
                baseline_assistant_count,
                timeout=CHATGPT_RESPONSE_TIMEOUT_SECONDS,
            ):
                logging.error("No completed assistant Copy/Kopiera control appeared before timeout")
                return {
                    "success": False,
                    "error": "Timed out waiting for completed assistant response"
                }
            logging.info("✓ Response complete (assistant Copy/Kopiera control visible)")
        else:
            # Explicit legacy mode keeps a bounded time-based compatibility path.
            time.sleep(8)

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
        candidates = assistant_copy_candidates(page)
        for candidate in reversed(candidates):
            try:
                if not candidate.is_visible():
                    continue
                # ChatGPT's floating action toolbar can transiently overlay the
                # message-level Copy button even after it is visible/enabled.
                # Force the click on the already-qualified button rather than
                # failing on pointer-interception geometry.
                candidate.click(timeout=5000, force=True)
                time.sleep(0.4)
                copied = page.evaluate("navigator.clipboard.readText()")
                if isinstance(copied, str) and copied.strip():
                    return copied.strip()
            except Exception as exc:
                logging.warning(f"Assistant Copy control failed: {exc}")
                continue
        logging.error(
            f"Could not copy newest assistant turn; candidates={len(candidates)}"
        )
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
        page.goto(validate_chatgpt_project_url(CHATGPT_TARGET_URL), wait_until="domcontentloaded")
        time.sleep(3)

        textarea = find_textarea(page, timeout=10)
        if textarea:
            return {"success": True, "message": "New chat started"}
        else:
            return {"success": False, "error": "Could not verify new chat"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def browser_worker_alive():
    return bool(browser_thread is not None and browser_thread.is_alive())


def bridge_can_accept_tasks():
    """A live worker may recover a dead browser session on the next task."""
    return startup_error is None and browser_worker_alive()


@app.route('/chat', methods=['POST'])
def chat():
    """Send a prompt to ChatGPT using a request-correlated browser task."""
    if not bridge_can_accept_tasks():
        return jsonify({"success": False, "error": startup_error or runtime_error or "Server not ready"}), 503

    data = request.get_json() or {}
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"success": False, "error": "Prompt must be non-empty string"}), 400
    try:
        result, status_code = submit_browser_task(
            "send_message",
            prompt=prompt,
            request_id=data.get("request_id"),
            tags={
                key: str(data[key])
                for key in ("run_id", "cognition_id")
                if data.get(key) not in (None, "")
            },
            timeout=CHATGPT_RESPONSE_TIMEOUT_SECONDS + 30,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 409
    return jsonify(result), status_code


@app.route('/cognition', methods=['POST'])
def cognition():
    """Run one stateless, request-correlated cognition in a fresh conversation."""
    if not bridge_can_accept_tasks():
        return jsonify({"success": False, "error": startup_error or runtime_error or "Server not ready"}), 503

    data = request.get_json() or {}
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"success": False, "error": "Prompt must be non-empty string"}), 400
    try:
        result, status_code = submit_browser_task(
            "cognition_request",
            prompt=prompt,
            request_id=data.get("request_id"),
            tags={
                key: str(data[key])
                for key in ("run_id", "cognition_id")
                if data.get(key) not in (None, "")
            },
            timeout=CHATGPT_RESPONSE_TIMEOUT_SECONDS + 30,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 409
    return jsonify(result), status_code


@app.route('/new-chat', methods=['POST'])
def new_chat():
    """Start a request-correlated fresh chat."""
    if not bridge_can_accept_tasks():
        return jsonify({"success": False, "error": startup_error or runtime_error or "Server not ready"}), 503
    data = request.get_json(silent=True) or {}
    try:
        result, status_code = submit_browser_task(
            "new_chat",
            request_id=data.get("request_id"),
            tags={
                key: str(data[key])
                for key in ("run_id", "cognition_id")
                if data.get(key) not in (None, "")
            },
            timeout=30,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 409
    return jsonify(result), status_code


@app.route('/show-ui', methods=['POST'])
def show_ui():
    """Bring the local Bob companion UI to the front in the managed browser."""
    if not bridge_can_accept_tasks():
        return jsonify({"success": False, "error": startup_error or runtime_error or "Server not ready"}), 503
    data = request.get_json(silent=True) or {}
    target = data.get("url") or BOB_COMPANION_UI_URL
    try:
        target = validate_companion_ui_url(target)
        result, status_code = submit_browser_task(
            "show_ui",
            url=target,
            request_id=data.get("request_id"),
            tags={
                key: str(data[key])
                for key in ("run_id", "cognition_id")
                if data.get(key) not in (None, "")
            },
            timeout=30,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify(result), status_code


@app.route('/health', methods=['GET'])
def health():
    """Health check that fails closed when the worker/browser is not usable."""
    worker_alive = browser_worker_alive()
    ready = bool(is_ready and worker_alive and startup_error is None)
    if not ready:
        error = startup_error or runtime_error or (
            "browser worker is not running" if not worker_alive else "browser not ready"
        )
        return jsonify({
            "status": "error" if startup_error or not worker_alive else "recovering",
            "ready": False,
            "error": error,
            "browser_generation": browser_generation,
        }), 503

    return jsonify({
        "status": "running",
        "ready": True,
        "browser_generation": browser_generation,
    }), 200

@app.route('/status', methods=['GET'])
def status():
    """Server status"""
    return jsonify({
        "server": "running",
        "browser_ready": bool(is_ready and browser_worker_alive()),
        "browser_worker_alive": browser_worker_alive(),
        "browser_generation": browser_generation,
        "runtime_error": runtime_error,
        "requests": browser_request_status(),
        "profile_path": load_profile_path(),
        "project_name": BOB_CHATGPT_PROJECT_NAME,
        "project_url_configured": bool(CHATGPT_TARGET_URL),
        "capture_mode": CHATGPT_CAPTURE_MODE,
        "companion_ui_url": BOB_COMPANION_UI_URL,
        "endpoints": {
            "chat": "POST /chat (legacy/stateful continuation)",
            "cognition": "POST /cognition (fresh chat per request)",
            "new_chat": "POST /new-chat",
            "show_ui": "POST /show-ui",
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
    print("  POST http://localhost:5001/cognition")
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
