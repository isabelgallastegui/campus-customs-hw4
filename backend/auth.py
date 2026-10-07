"""Password hashing and validation for Campus Customs accounts.

The `users` table already contains hashes in the format

    pbkdf2_sha256$<salt>$<hex digest>

and the existing test user verifies against PBKDF2-HMAC-SHA256 with 120,000
iterations, so new accounts are written in exactly the same format. That keeps
one scheme across the whole table instead of introducing a second one.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 8  # 16 hex characters, matching the existing rows.

MIN_LENGTH = 8

PASSWORD_RULES: list[tuple[str, str]] = [
    (rf".{{{MIN_LENGTH},}}", f"At least {MIN_LENGTH} characters"),
    (r"[A-Z]", "At least one uppercase letter"),
    (r"[a-z]", "At least one lowercase letter"),
    (r"[0-9]", "At least one number"),
]


def _derive(password: str, salt: str) -> str:
    """Run PBKDF2 over the password with the given salt."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()


def hash_password(password: str) -> str:
    """Produce a storable `pbkdf2_sha256$salt$digest` string."""
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_derive(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, in constant time."""
    try:
        algorithm, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    # compare_digest avoids leaking how much of the hash matched.
    return hmac.compare_digest(_derive(password, salt), digest)


def password_problems(password: str) -> list[str]:
    """Return the unmet password requirements, empty when the password is fine."""
    return [label for pattern, label in PASSWORD_RULES if not re.search(pattern, password)]


def normalize_email(email: str) -> str:
    """Emails are matched case-insensitively and stored lowercased."""
    return email.strip().lower()


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))
