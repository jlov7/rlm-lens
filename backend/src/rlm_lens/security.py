from __future__ import annotations

from pathlib import Path
import fnmatch
import hashlib
import re


DEFAULT_DENY_GLOBS = [
    "**/.git/**",
    "**/node_modules/**",
    ".env",
    ".env*",
    "**/.env",
    "**/.env*",
    "*.pem",
    "**/*.pem",
    "*secret*",
    "**/*secret*",
    "*token*",
    "**/*token*",
    "*key*",
    "**/*key*",
]

_SECRET_PATTERNS = [
    re.compile(r"OPENAI_API_KEY\s*=\s*[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9\-_\.=]{10,}"),
    re.compile(r"[A-Z0-9_]{3,64}\s*=\s*[A-Za-z0-9_\-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
]


def is_binary_bytes(content: bytes) -> bool:
    return b"\x00" in content


def sha256_text(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def sha256_bytes(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"sha256:{digest}"


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def relative_path_within_root(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_root not in resolved_path.parents and resolved_root != resolved_path:
        raise ValueError("Path escapes corpus root")
    return resolved_path.relative_to(resolved_root).as_posix()


def resolve_corpus_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    if root.resolve() not in candidate.parents and root.resolve() != candidate:
        raise ValueError("Path traversal is not allowed")
    return candidate


def is_denied(path: str, extra_excludes: list[str] | None = None) -> bool:
    patterns = list(DEFAULT_DENY_GLOBS)
    if extra_excludes:
        patterns.extend(extra_excludes)
    normalized = path.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return any(fnmatch.fnmatch(normalized, pat) for pat in patterns)


def contains_hidden_segment(path: str) -> bool:
    return any(part.startswith(".") for part in Path(path).parts)
