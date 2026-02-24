from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
import os

from .environment import get_environment_status


@dataclass
class Subcall:
    prompt: str
    response: str
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    execution_time: float
    warnings: list[str]


class RLMAdapter:
    """Adapter that prefers official `rlm.RLM`, with deterministic fallback.

    Fallback is used for local testing and offline operation, but warnings are surfaced
    for auditability when provider/env prerequisites are missing.
    """

    def __init__(self, model: str, provider: str, environment: str) -> None:
        self.model = model
        self.provider = provider
        self.environment = environment
        self._rlm: Any | None = None
        self._warnings: list[str] = []

        env_status = get_environment_status()
        if environment == "docker" and not env_status.docker_running:
            self._warnings.append("Docker sandbox unavailable; using local fallback environment.")

        if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            self._warnings.append("OPENAI_API_KEY is not set; using local fallback model behavior.")

        try:
            from rlm import RLM  # type: ignore[import-not-found]

            self._rlm = RLM
        except ImportError:
            self._warnings.append("`rlm` package not available; using fallback adapter.")
            self._rlm = None

    def has_real_rlm(self) -> bool:
        return self._rlm is not None and self.provider == "openai" and os.getenv("OPENAI_API_KEY") is not None

    def warnings(self) -> list[str]:
        return list(self._warnings)

    def call_submodel(self, prompt: str) -> Subcall:
        started = perf_counter()
        warnings = self.warnings()

        if not self.has_real_rlm():
            output = f"Fallback analysis: {prompt[:200]}"
            return Subcall(
                prompt=prompt,
                response=output,
                total_input_tokens=max(1, len(prompt) // 4),
                total_output_tokens=max(1, len(output) // 4),
                total_cost=0.0,
                execution_time=round(perf_counter() - started, 4),
                warnings=warnings,
            )

        instance = self._rlm(model=self.model) if callable(self._rlm) else None
        if instance is None:
            output = f"RLM unavailable for prompt: {prompt[:120]}"
            warnings.append("RLM instance creation failed, fell back to synthetic response.")
        elif hasattr(instance, "run"):
            output = str(instance.run(prompt))
        elif callable(instance):
            output = str(instance(prompt))
        else:
            output = f"RLM instance has no callable interface for prompt: {prompt[:120]}"
            warnings.append("RLM callable interface missing, used synthetic response.")

        return Subcall(
            prompt=prompt,
            response=output,
            total_input_tokens=max(1, len(prompt) // 4),
            total_output_tokens=max(1, len(output) // 4),
            total_cost=0.0,
            execution_time=round(perf_counter() - started, 4),
            warnings=warnings,
        )
