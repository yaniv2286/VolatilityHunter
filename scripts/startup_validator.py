"""VolatilityHunter startup validator.

Exits non-zero if critical configuration, secrets, data, or state files are missing.
Warnings are logged but do not block startup.

Run manually:
    python scripts/startup_validator.py

Or call validate() from the entrypoint before starting the daily trading loop.
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("startup_validator")


@dataclass
class ValidationResult:
    ok: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CRITICAL_ENV = {
    "TIINGO_API_KEY": "Required to fetch market data from Tiingo.",
}

OPTIONAL_ENV = {
    "EMAIL_SENDER": "Gmail sender for daily briefs.",
    "EMAIL_PASSWORD": "Gmail app password for daily briefs.",
    "EMAIL_RECIPIENTS": "Comma-separated destination emails for daily briefs.",
    "TELEGRAM_BOT_TOKEN": "Telegram bot token for alerts.",
    "TELEGRAM_CHAT_ID": "Telegram chat ID for alerts.",
}

REQUIRED_FILES = [
    ("src/strategy_engine.py", "Core strategy engine (single source of truth)."),
    ("src/smart_data_loader_factory.py", "Data loader factory."),
    ("src/brokerage_interface.py", "Brokerage interface wrapper."),
]

REQUIRED_DATA = [
    ("portfolio.json", "Current portfolio state."),
]



def _validate_python_version(result: ValidationResult) -> None:
    if sys.version_info < (3, 10):
        result.add_error(f"Python {sys.version_info.major}.{sys.version_info.minor} is too old; Python 3.10+ is required.")


def _validate_env(result: ValidationResult) -> None:
    for key, description in CRITICAL_ENV.items():
        value = os.getenv(key)
        if not value or value.strip() == "" or "your" in value.lower():
            result.add_error(f"{key} is missing or looks like a placeholder. {description}")

    for key, description in OPTIONAL_ENV.items():
        value = os.getenv(key)
        if not value or value.strip() == "" or "your" in value.lower():
            result.add_warning(f"{key} is not configured. {description}")


def _validate_required_files(result: ValidationResult) -> None:
    for relative, description in REQUIRED_FILES:
        path = PROJECT_ROOT / relative
        if not path.exists():
            result.add_error(f"Required file missing: {path} ({description})")


def _validate_data_state(result: ValidationResult) -> None:
    for relative, description in REQUIRED_DATA:
        path = PROJECT_ROOT / "data" / relative
        if not path.exists():
            result.add_error(f"Required data file missing: {path} ({description})")
        elif path.stat().st_size == 0:
            result.add_error(f"Required data file is empty: {path} ({description})")

    spy = PROJECT_ROOT / "data" / "raw" / "SPY.parquet"
    if not spy.exists():
        result.add_error(f"Benchmark market data missing: {spy}")
    else:
        age_hours = (datetime.utcnow() - datetime.utcfromtimestamp(spy.stat().st_mtime)).total_seconds() / 3600
        if age_hours > 48:
            result.add_warning(f"SPY.parquet is {age_hours:.1f} hours old.")


def _validate_directories(result: ValidationResult) -> None:
    for relative in ["data", "data/raw", "logs", "reports"]:
        path = PROJECT_ROOT / relative
        if not path.exists():
            logger.info("Creating missing runtime directory: %s", path)
            path.mkdir(parents=True, exist_ok=True)


def validate() -> ValidationResult:
    """Run all startup checks and return a ValidationResult."""
    result = ValidationResult()
    _validate_python_version(result)
    _validate_env(result)
    _validate_required_files(result)
    _validate_data_state(result)
    _validate_directories(result)
    return result


def _print_report(result: ValidationResult) -> None:
    print("=" * 60)
    print("VolatilityHunter Startup Validator")
    print("=" * 60)
    if result.warnings:
        print("\nWARNINGS (startup will continue):")
        for w in result.warnings:
            print(f"  - {w}")
    if result.errors:
        print("\nERRORS (startup blocked):")
        for e in result.errors:
            print(f"  - {e}")
    print("\n" + ("OK" if result.ok else "FAILED"))
    print("=" * 60)


def main() -> int:
    result = validate()
    _print_report(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
