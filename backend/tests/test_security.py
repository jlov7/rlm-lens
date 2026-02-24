from pathlib import Path

import pytest

from rlm_lens.security import is_denied, redact_secrets, resolve_corpus_path


def test_resolve_corpus_path_blocks_traversal(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    with pytest.raises(ValueError):
        resolve_corpus_path(root, "../outside.txt")


def test_redact_secrets_replaces_openai_key() -> None:
    text = "OPENAI_API_KEY=sk-12345678901234567890"
    assert "[REDACTED]" in redact_secrets(text)


def test_redact_secrets_replaces_common_tokens() -> None:
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123"
    assert "[REDACTED]" in redact_secrets(text)

    gh_text = "ghp_1234567890abcdefghijklmnopqrstuvwxyzAB"
    assert "[REDACTED]" in redact_secrets(gh_text)


def test_is_denied_blocks_sensitive_file_patterns() -> None:
    assert is_denied(".env")
    assert is_denied(".env.local")
    assert is_denied("secrets/private.pem")
    assert is_denied("tmp/access_token.txt")
