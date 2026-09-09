#!/usr/bin/env python3
"""
Verification script for src/telegram_notifier.py.

Validates that HTML email bodies are converted to clean Telegram plain text,
with embedded CSS/style blocks removed and HTML special characters escaped.

Exit code 0 = all checks pass.
Exit code 1 = at least one check failed.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.telegram_notifier import _strip_html, TelegramNotifier


def assert_check(condition: bool, message: str) -> bool:
    if condition:
        print(f"[OK] {message}")
        return True
    print(f"[FAIL] {message}")
    return False


def main() -> int:
    failures = 0

    sample_html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background-color: white; }
        </style>
        <script>alert('xss');</script>
    </head>
    <body>
        <div class="header">
            <h2>VolatilityHunter Daily Report</h2>
            <p><b>Mode:</b> IBKR_PAPER</p>
        </div>
        <div class="section">
            <h3>Summary</h3>
            <p>Portfolio Value: $100,000.00</p>
            <p>Cash &lt; 5%</p>
        </div>
    </body>
    </html>
    """

    plain = _strip_html(sample_html)

    # CSS and JS content must not leak into plain text.
    failures += not assert_check("font-family" not in plain, "CSS style content removed")
    failures += not assert_check("background-color" not in plain, "CSS property content removed")
    failures += not assert_check("alert('xss')" not in plain, "Script content removed")
    # Visible text must be preserved.
    failures += not assert_check("VolatilityHunter Daily Report" in plain, "Report title preserved")
    failures += not assert_check("IBKR_PAPER" in plain, "Mode value preserved")
    failures += not assert_check("Portfolio Value: $100,000.00" in plain, "Portfolio value preserved")
    # HTML tags should be removed; a literal '<' from decoded entity content is fine.
    failures += not assert_check(__import__("re").search(r"<[^>]+>", plain) is None, "No stray HTML tag markup in output")

    # Verify Telegram message construction escapes dynamic content safely.
    captured_texts = []

    class CaptureNotifier(TelegramNotifier):
        def __init__(self):
            # Explicitly set dummy credentials so enabled=True, but override send.
            super().__init__(token="dummy", chat_id="12345")

        def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
            captured_texts.append((text, parse_mode))
            return True

    notifier = CaptureNotifier()
    notifier.send_html_email_mirror(
        subject="OK VolatilityHunter IBKR_PAPER completed - 2026-09-07 17:17:17",
        html_body=sample_html,
    )

    failures += not assert_check(len(captured_texts) == 1, "One Telegram message captured")
    text, parse_mode = captured_texts[0]
    failures += not assert_check(parse_mode == "HTML", "Uses HTML parse mode")
    failures += not assert_check("<b>[VolatilityHunter] OK VolatilityHunter" in text, "Bold header present")
    failures += not assert_check("font-family" not in text, "No CSS in sent message")
    failures += not assert_check("&lt;" in text, "HTML special characters escaped")
    failures += not assert_check("<br>" in text, "Line breaks converted to <br> tags")

    # Verify fallback when no token configured (silent no-op).
    silent = TelegramNotifier(token="", chat_id="")
    failures += not assert_check(silent.enabled is False, "Notifier disabled without credentials")
    failures += not assert_check(silent.send_message("test") is False, "Disabled notifier returns False")

    if failures:
        print(f"\n[FAIL] {failures} check(s) failed.")
        return 1

    print("\n[OK] All Telegram notifier checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
