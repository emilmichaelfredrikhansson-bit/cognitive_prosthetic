from __future__ import annotations

import os
import threading

import requests

from .errors import BobError


class ChatGPTBridge:
    def __init__(self, base_url: str | None = None, timeout: int = 220):
        self.base_url = (base_url or os.environ.get("CHATGPT_BRIDGE_URL") or "http://127.0.0.1:5001").rstrip("/")
        self.timeout = timeout
        self._lock = threading.Lock()

    def send(self, prompt: str) -> str:
        with self._lock:
            response = requests.post(
                self.base_url + "/chat",
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise BobError(payload.get("error") or "ChatGPT bridge failed")
            text = payload.get("response")
            if not isinstance(text, str):
                raise BobError("ChatGPT bridge returned no response text")
            return text

    def cognition(self, prompt: str) -> str:
        """Run one cognition request in a fresh ChatGPT conversation.

        This is the canonical primitive for the future stateless Context Compiler
        path. Existing closed-loop V1 work still uses send() until durable
        compiled-context continuation is implemented.
        """
        with self._lock:
            response = requests.post(
                self.base_url + "/cognition",
                json={"prompt": prompt},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise BobError(payload.get("error") or "fresh cognition request failed")
            text = payload.get("response")
            if not isinstance(text, str):
                raise BobError("fresh cognition request returned no response text")
            return text

    def new_chat(self) -> None:
        with self._lock:
            response = requests.post(self.base_url + "/new-chat", json={}, timeout=30)
            response.raise_for_status()
