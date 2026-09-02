"""
hash.py — Cryptographic SHA-256 Provenance & Hashing Utilities for PROJECT ANCHOR.
"""

import hashlib
import hmac
from pathlib import Path
from typing import Union


def compute_sha256(text: str) -> str:
    """Compute the deterministic SHA-256 hex digest for a UTF-8 string."""
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_file_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Compute the SHA-256 hex digest of a file using streaming chunks."""
    target = Path(file_path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {target}")

    hasher = hashlib.sha256()
    with open(target, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_sha256(text: str, expected_hash: str) -> bool:
    """Verify that a given string matches an expected SHA-256 hex digest in constant time."""
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return False
    computed = compute_sha256(text)
    return hmac.compare_digest(computed.lower(), expected_hash.lower())
