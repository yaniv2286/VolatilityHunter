"""Telegram alerting helper for VolatilityHunter.

Mirrors email notifications to a Telegram chat via direct POST to the Bot API.
Safe to import when no token is configured: it becomes a silent no-op.
"""
import html
import os
import re
import traceback
from html.parser import HTMLParser

import requests


class _HTMLStripper(HTMLParser):
    """Convert HTML email bodies to readable plain text for Telegram."""

    # Tags whose contents should never appear in the output.
    _SKIP_TAGS = frozenset({"style", "script", "head", "title", "meta", "link", "noscript"})
    # Tags that act as block separators in plain text.
    _BLOCK_TAGS = frozenset({"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th"})

    def __init__(self):
        super().__init__()
        self.text = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "br":
            self.text.append("\n")
        elif tag in self._BLOCK_TAGS:
            if self.text and not self.text[-1].endswith("\n"):
                self.text.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in self._BLOCK_TAGS:
            if self.text and not self.text[-1].endswith("\n"):
                self.text.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        self.text.append(data)

    def get_text(self):
        text = "".join(self.text)
        # Collapse repeated blank lines while preserving intentional line breaks.
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)


def _strip_html(html_text: str) -> str:
    # Remove embedded CSS/JS blocks up-front so the parser never sees their text.
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    stripper = _HTMLStripper()
    try:
        stripper.feed(cleaned)
        return stripper.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", "", cleaned)


class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled:
            return False

        if len(text) > 4000:
            text = text[:3997] + "..."

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}

        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return True
        except Exception as exc:
            print(f"[TELEGRAM] Failed to send message: {exc}")
            traceback.print_exc()
            return False

    def send_html_email_mirror(self, subject: str, html_body: str) -> bool:
        plain = _strip_html(html_body)
        # Escape dynamic content so it is safe for Telegram's HTML parse mode.
        safe_subject = html.escape(subject)
        safe_plain = html.escape(plain)
        # Preserve line breaks as <br> tags since Telegram HTML mode needs explicit breaks.
        formatted_plain = safe_plain.replace("\n", "<br>")
        header = f"<b>[VolatilityHunter] {safe_subject}</b>"
        return self.send_message(f"{header}<br><br>{formatted_plain}")
