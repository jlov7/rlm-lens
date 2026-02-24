from __future__ import annotations

from dataclasses import dataclass
import io
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request
import zipfile


@dataclass(frozen=True)
class StarterPack:
    id: str
    name: str
    description: str
    size_label: str
    approx_files: int
    source_type: str
    source: str
    license: str
    default_prompts: list[str]
    network_required: bool = False


class StarterCorpusService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.base_dir = data_dir / "starter-corpora"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.repo_root = Path(__file__).resolve().parents[3]
        self._packs = self._build_pack_catalog()

    def _build_pack_catalog(self) -> dict[str, StarterPack]:
        fixture_source = self.repo_root / "examples" / "sample_corpus"
        return {
            "fixture-small": StarterPack(
                id="fixture-small",
                name="Fixture Corpus",
                description="Tiny deterministic corpus for first-run demos and visual verification.",
                size_label="Small",
                approx_files=8,
                source_type="local_copy",
                source=str(fixture_source),
                license="MIT (project sample files)",
                default_prompts=[
                    "Summarize the architecture and cite top files.",
                    "Find the retry policy and cite exact line ranges.",
                ],
                network_required=False,
            ),
            "synthetic-medium": StarterPack(
                id="synthetic-medium",
                name="Synthetic Engineering Corpus",
                description="Generated multi-folder engineering corpus for realistic retrieval and tracing.",
                size_label="Medium",
                approx_files=180,
                source_type="generated",
                source="generated://synthetic-medium",
                license="Generated content (RLM-Lens project)",
                default_prompts=[
                    "Map module boundaries and cite at least 6 files.",
                    "Find schema ownership and explain cross-service contracts with citations.",
                ],
                network_required=False,
            ),
            "oss-flask-main": StarterPack(
                id="oss-flask-main",
                name="Flask OSS Snapshot",
                description="Public open-source repository snapshot for larger real-world querying.",
                size_label="Large",
                approx_files=450,
                source_type="remote_archive",
                source="https://codeload.github.com/pallets/flask/tar.gz/refs/heads/main",
                license="BSD-3-Clause (Flask)",
                default_prompts=[
                    "Explain request lifecycle with evidence from core modules.",
                    "Identify extension points and cite source lines.",
                ],
                network_required=True,
            ),
        }

    def list_packs(self) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for pack in self._packs.values():
            target_path = self.base_dir / pack.id
            payload.append(
                {
                    "id": pack.id,
                    "name": pack.name,
                    "description": pack.description,
                    "size_label": pack.size_label,
                    "approx_files": pack.approx_files,
                    "source_type": pack.source_type,
                    "license": pack.license,
                    "default_prompts": list(pack.default_prompts),
                    "network_required": pack.network_required,
                    "installed": target_path.exists(),
                    "path": str(target_path.resolve()) if target_path.exists() else None,
                }
            )
        return payload

    def materialize(self, pack_id: str, *, force: bool = False) -> dict[str, object]:
        pack = self._packs.get(pack_id)
        if pack is None:
            raise ValueError(f"Unknown starter corpus pack: {pack_id}")

        target = self.base_dir / pack.id
        marker_path = target / ".starter-pack.json"

        if target.exists() and marker_path.exists() and not force:
            stats = self._dir_stats(target)
            return {
                "pack_id": pack.id,
                "name": pack.name,
                "path": str(target.resolve()),
                "installed": True,
                "already_present": True,
                **stats,
            }

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        if pack.source_type == "local_copy":
            source = Path(pack.source)
            if not source.exists():
                raise RuntimeError(f"Starter corpus source path does not exist: {source}")
            self._copy_directory(source, target)
        elif pack.source_type == "generated":
            self._generate_synthetic_medium(target)
        elif pack.source_type == "remote_archive":
            self._download_and_extract(pack.source, target)
        else:
            raise RuntimeError(f"Unsupported starter corpus source type: {pack.source_type}")

        marker_path.write_text(
            json.dumps(
                {
                    "pack_id": pack.id,
                    "name": pack.name,
                    "source_type": pack.source_type,
                    "source": pack.source,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        stats = self._dir_stats(target)
        return {
            "pack_id": pack.id,
            "name": pack.name,
            "path": str(target.resolve()),
            "installed": True,
            "already_present": False,
            **stats,
        }

    def _copy_directory(self, source: Path, destination: Path) -> None:
        for file_path in source.rglob("*"):
            if file_path.is_dir():
                continue
            rel = file_path.relative_to(source)
            if ".git" in rel.parts:
                continue
            out = destination / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, out)

    def _generate_synthetic_medium(self, target: Path) -> None:
        docs_dir = target / "docs"
        services_dir = target / "src" / "services"
        schemas_dir = target / "schemas"
        ops_dir = target / "ops" / "runbooks"

        docs_dir.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(parents=True, exist_ok=True)
        schemas_dir.mkdir(parents=True, exist_ok=True)
        ops_dir.mkdir(parents=True, exist_ok=True)

        overview = target / "README.md"
        overview.write_text(
            "# Synthetic Engineering Corpus\n\nThis corpus is generated for RLM-Lens demos.\nIt contains architecture docs, service modules, and schema definitions.\n",
            encoding="utf-8",
        )

        for idx in range(1, 81):
            (docs_dir / f"architecture_{idx:03}.md").write_text(
                f"# Architecture Note {idx}\n\n"
                "Service boundaries are defined between ingest, retrieval, and orchestration layers.\n"
                "Retry policy references: src/services/retry_policy.py\n"
                f"Decision log item {idx}: enforce deterministic trace serialization.\n",
                encoding="utf-8",
            )

        for idx in range(1, 81):
            (services_dir / f"module_{idx:03}.py").write_text(
                "from dataclasses import dataclass\n\n@dataclass\nclass RetryPolicy:\n    max_attempts: int = 5\n    backoff_ms: int = 250\n\ndef with_retries(operation):\n    return operation()\n",
                encoding="utf-8",
            )

        for idx in range(1, 13):
            (schemas_dir / f"domain_{idx:02}.sql").write_text(
                "CREATE TABLE IF NOT EXISTS events (\n  id TEXT PRIMARY KEY,\n  entity TEXT NOT NULL,\n  payload_json TEXT NOT NULL\n);\n",
                encoding="utf-8",
            )

        for idx in range(1, 17):
            (ops_dir / f"incident_{idx:02}.md").write_text(
                f"# Incident Runbook {idx}\n\nIf retries fail, inspect trace events and citation overlap before rollback.\n",
                encoding="utf-8",
            )

    def _download_and_extract(self, url: str, target: Path) -> None:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()

        if url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                zip_members = archive.infolist()
                prefix = self._common_prefix([member.filename for member in zip_members if not member.is_dir()])
                for zip_member in zip_members:
                    if zip_member.is_dir():
                        continue
                    name = zip_member.filename
                    rel_name = name[len(prefix) :].lstrip("/") if prefix else name
                    if not rel_name:
                        continue
                    destination = (target / rel_name).resolve()
                    if not str(destination).startswith(str(target.resolve())):
                        raise RuntimeError("Unsafe archive path encountered")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(zip_member) as src, destination.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
            return

        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            tar_members = [member for member in archive.getmembers() if member.isfile()]
            prefix = self._common_prefix([member.name for member in tar_members])
            for tar_member in tar_members:
                rel_name = tar_member.name[len(prefix) :].lstrip("/") if prefix else tar_member.name
                if not rel_name:
                    continue
                destination = (target / rel_name).resolve()
                if not str(destination).startswith(str(target.resolve())):
                    raise RuntimeError("Unsafe archive path encountered")
                destination.parent.mkdir(parents=True, exist_ok=True)
                extracted = archive.extractfile(tar_member)
                if extracted is None:
                    continue
                with extracted, destination.open("wb") as dst:
                    shutil.copyfileobj(extracted, dst)

    def _common_prefix(self, names: list[str]) -> str:
        if not names:
            return ""
        split_names = [name.split("/") for name in names if name]
        if not split_names:
            return ""
        prefix_parts: list[str] = []
        for parts in zip(*split_names, strict=False):
            first = parts[0]
            if all(item == first for item in parts):
                prefix_parts.append(first)
            else:
                break
        return "/".join(prefix_parts) + ("/" if prefix_parts else "")

    def _dir_stats(self, directory: Path) -> dict[str, int]:
        files = [path for path in directory.rglob("*") if path.is_file() and path.name != ".starter-pack.json"]
        total_bytes = sum(path.stat().st_size for path in files)
        return {"files_total": len(files), "bytes_total": total_bytes}
