"""Password hashing with scrypt (standard library only)."""
import hashlib
import hmac
import os


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$")
        dk = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return scheme == "scrypt" and hmac.compare_digest(dk.hex(), digest)
    except (ValueError, TypeError):
        return False
