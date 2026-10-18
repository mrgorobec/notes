import re
from datetime import UTC, datetime

# Field keys that look like secrets are hidden by default (spoiler in the bot, mask on the web).
_SECRET_WORDS = {"pin", "пін", "pass", "pwd", "cvv", "cvc", "otp", "2fa", "seed"}
_SECRET_PREFIXES = ("парол", "password", "passwd", "passphrase", "token", "токен", "secret", "секрет")


def normalize(text: str) -> str:
    """Case- and whitespace-insensitive form used for search and duplicate checks."""
    return " ".join(text.casefold().split())


def is_secret_key(key: str) -> bool:
    words = re.findall(r"\w+", key.casefold())
    return any(w in _SECRET_WORDS or w.startswith(_SECRET_PREFIXES) for w in words)


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    # SQLite drops tzinfo; Postgres keeps it.
    return value if value.tzinfo else value.replace(tzinfo=UTC)
