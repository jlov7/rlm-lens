from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal


class IndexConfig(BaseModel):
    include_globs: list[str] = Field(default_factory=lambda: ["**/*.md", "**/*.py", "**/*.ts", "**/*.tsx", "**/*.sql"])
    exclude_globs: list[str] = Field(default_factory=lambda: ["**/node_modules/**", "**/.git/**"])
    max_file_bytes: int = 1_000_000


class CreateCorpusRequest(BaseModel):
    name: str
    path: str
    index_config: IndexConfig = Field(default_factory=IndexConfig)
    start_index: bool = True


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class RuntimeBudgets(BaseModel):
    max_wall_time_s: int = 90
    max_subcalls: int = 40
    max_tokens: int | None = None


class RetrievalConfig(BaseModel):
    bm25_weight: float = 0.55
    vector_weight: float = 0.35
    rerank_weight: float = 0.10
    top_k: int = 6


class RuntimeConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-5-nano"
    environment: Literal["docker", "local"] = "docker"
    max_depth: int = 2
    max_iterations: int = 10
    budgets: RuntimeBudgets = Field(default_factory=RuntimeBudgets)
    performance_mode: bool = False
    target_corpora: list[str] = Field(default_factory=list)
    corpus_weights: dict[str, float] = Field(default_factory=dict)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class CreateRunRequest(BaseModel):
    corpus_id: str
    messages: list[ChatMessage]
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)


class Citation(BaseModel):
    citation_id: str
    corpus_id: str | None = None
    path: str
    start_line: int
    end_line: int
    snippet: str


class RunDetail(BaseModel):
    run_id: str
    corpus_id: str
    status: str
    messages: list[ChatMessage]
    final_answer: str | None
    citations: list[Citation]
    usage: dict[str, Any]


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
