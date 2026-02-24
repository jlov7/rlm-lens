from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from ..providers import get_provider_spec, normalize_provider_api_key, normalize_provider_id, provider_key_hint, provider_key_present
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

    def __init__(
        self,
        model: str,
        provider: str,
        environment: str,
        provider_api_key: str | None = None,
    ) -> None:
        self.model = model
        self.provider = normalize_provider_id(provider)
        self.environment = environment
        self.provider_api_key = normalize_provider_api_key(provider_api_key)
        self._rlm: Any | None = None
        self._warnings: list[str] = []

        env_status = get_environment_status()
        if environment == "docker" and not env_status.docker_running:
            self._warnings.append("Docker sandbox unavailable; using local fallback environment.")

        if not provider_key_present(self.provider, self.provider_api_key):
            self._warnings.append(f"{provider_key_hint(self.provider)} is not set; using local fallback model behavior.")

        try:
            from rlm import RLM  # type: ignore[import-not-found]

            self._rlm = RLM
        except ImportError:
            self._warnings.append("`rlm` package not available; using fallback adapter.")
            self._rlm = None

    def has_real_rlm(self) -> bool:
        return self._rlm is not None and provider_key_present(self.provider, self.provider_api_key)

    def warnings(self) -> list[str]:
        return list(self._warnings)

    def _constructor_kwargs(self) -> list[dict[str, object]]:
        candidate_kwargs: list[dict[str, object]] = [{"model": self.model}]
        if self.provider != "openai":
            candidate_kwargs.append({"model": self.model, "backend": self.provider})
        if self.provider_api_key is not None:
            candidate_kwargs.append({"model": self.model, "api_key": self.provider_api_key})
            if self.provider != "openai":
                candidate_kwargs.append({"model": self.model, "backend": self.provider, "api_key": self.provider_api_key})
                candidate_kwargs.append(
                    {
                        "model": self.model,
                        "backend": self.provider,
                        "backend_kwargs": {"api_key": self.provider_api_key},
                    }
                )

        deduped: list[dict[str, object]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        for kwargs in candidate_kwargs:
            key = tuple(sorted((name, repr(value)) for name, value in kwargs.items()))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(kwargs)
        return deduped

    def _build_instance(self) -> tuple[object | None, str | None]:
        if not callable(self._rlm):
            return None, "RLM constructor unavailable; using fallback adapter."

        for kwargs in self._constructor_kwargs():
            try:
                return self._rlm(**kwargs), None
            except TypeError:
                continue
            except Exception as exc:  # noqa: BLE001
                return None, f"Provider backend initialization failed ({exc.__class__.__name__}); using fallback model behavior."

        spec = get_provider_spec(self.provider)
        if spec.id != "openai":
            return None, f"Provider `{spec.label}` backend is not supported by the installed rlm package; using fallback model behavior."
        return None, "RLM backend initialization failed; using fallback model behavior."

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

        instance, build_warning = self._build_instance()
        if instance is None:
            if build_warning:
                warnings.append(build_warning)
            output = f"RLM unavailable for prompt: {prompt[:120]}"
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
