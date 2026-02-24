from pathlib import Path

from rlm_lens.db import Database
from rlm_lens.events import EventBroker
from rlm_lens.indexer import CorpusReader, Indexer
from rlm_lens.models import IndexConfig
from rlm_lens.utils import now_iso


def test_collect_paths_respects_globs(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.py").write_text("print('hi')")
    (root / "b.md").write_text("# doc")
    (root / "c.bin").write_bytes(b"\x00\x01")

    db = Database(tmp_path / "db.sqlite")
    broker = EventBroker()
    indexer = Indexer(db, broker)

    config = IndexConfig(include_globs=["**/*.py", "**/*.md"], exclude_globs=["**/*.md"], max_file_bytes=1000)
    paths = indexer._collect_paths(root, config)
    assert [p.name for p in paths] == ["a.py"]


def test_snapshot_hash_stable(tmp_path: Path) -> None:
    db = Database(tmp_path / "db.sqlite")
    broker = EventBroker()
    indexer = Indexer(db, broker)
    corpus_id = "cor_test"
    db.execute(
        "INSERT INTO corpora (id, name, root_path, created_at, updated_at, index_config_json) VALUES (?, ?, ?, ?, ?, ?)",
        (corpus_id, "test", str(tmp_path), now_iso(), now_iso(), IndexConfig().model_dump_json()),
    )
    db.execute(
        "INSERT INTO files (corpus_id, path, sha256, bytes, mtime, is_binary, indexed_at, language_hint) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (corpus_id, "a.py", "sha256:1", 10, 1.0, 0, now_iso(), "py"),
    )

    first = indexer._snapshot_hash(corpus_id, tmp_path, IndexConfig())
    second = indexer._snapshot_hash(corpus_id, tmp_path, IndexConfig())
    assert first == second


def test_query_token_line_span_prefers_relevant_line(tmp_path: Path) -> None:
    db = Database(tmp_path / "db.sqlite")
    corpus_id = "cor_span"
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "retry_policy.py").write_text("header\nnotes\nclass RetryPolicy:\n    max_attempts = 5\n")

    db.execute(
        "INSERT INTO corpora (id, name, root_path, created_at, updated_at, index_config_json) VALUES (?, ?, ?, ?, ?, ?)",
        (corpus_id, "test", str(corpus_root), now_iso(), now_iso(), IndexConfig().model_dump_json()),
    )
    db.execute(
        "INSERT INTO file_fts (corpus_id, path, content) VALUES (?, ?, ?)",
        (corpus_id, "retry_policy.py", (corpus_root / "retry_policy.py").read_text()),
    )

    reader = CorpusReader(db)
    hits = reader.search(corpus_id, "where retry policy", limit=5)
    assert hits
    assert hits[0].start_line >= 3


def test_sensitive_files_excluded_by_default(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / ".env").write_text("OPENAI_API_KEY=sk-secret")
    (root / "safe.md").write_text("safe")

    db = Database(tmp_path / "db.sqlite")
    broker = EventBroker()
    indexer = Indexer(db, broker)

    config = IndexConfig(include_globs=["**/*"], exclude_globs=[], max_file_bytes=1000)
    paths = [p.relative_to(root).as_posix() for p in indexer._collect_paths(root, config)]
    assert ".env" not in paths
    assert "safe.md" in paths
