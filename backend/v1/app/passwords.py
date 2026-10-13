"""Password hashing and checking."""

import base64
import hashlib
import hmac
import re
import secrets

# [PASSWORD HASHING HERE]
# How: PBKDF2-HMAC-SHA256 from Python's standard library, with a random
#      16-byte salt per password. The stored value records the algorithm,
#      iteration count, salt, and hash: "pbkdf2_sha256$310000$<salt>$<hash>".
# Why: The requirements say never to keep plain passwords. PBKDF2 is
#      deliberately slow, so stolen hashes are expensive to crack, and it needs
#      no extra packages. 310,000 iterations follows OWASP guidance while
#      staying fast enough on a 128 MB Lambda. Because the iteration count is
#      stored with each hash, it can be raised later without breaking
#      existing passwords.
ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 310_000
MIN_LENGTH = 8


def password_problem(password: object) -> str | None:
    """
    Check a new password against the password rules.

    Args:
        password: The proposed password.

    Returns:
        A message describing the problem, or None if the password is fine.
    """
    if not isinstance(password, str):
        return "Must be text."
    if len(password) < MIN_LENGTH:
        return f"Must be at least {MIN_LENGTH} characters."
    if len(password) > 128:
        return "Must be at most 128 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Must contain at least one letter and one number."
    return None


def hash_password(password: str) -> str:
    """
    Hash a password for storage.

    Args:
        password: The plain password.

    Returns:
        The encoded hash string.
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return "$".join([ALGORITHM, str(ITERATIONS),
                     base64.b64encode(salt).decode(), base64.b64encode(digest).decode()])


def verify_password(password: str, stored: str) -> bool:
    """
    Check a password against a stored hash.

    Args:
        password: The plain password to check.
        stored: The encoded hash from hash_password().

    Returns:
        True if the password matches.
    """
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     base64.b64decode(salt_b64), int(iterations))
        # [CONSTANT-TIME COMPARE HERE]
        # How: hmac.compare_digest compares the hashes.
        # Why: A normal == stops at the first different byte, and that timing
        #      difference can leak information to an attacker.
        return hmac.compare_digest(digest, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False
