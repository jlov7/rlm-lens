from __future__ import annotations

import re
from typing import Any


def _tokenize(text: str) -> set[str]:
    tokens = [re.sub(r"[^a-z0-9_]", "", token.lower()) for token in text.split()]
    return {token for token in tokens if token and len(token) >= 3}


def _claims(answer: str) -> list[str]:
    claims: list[str] = []
    for line in answer.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            claims.append(stripped[2:])
    return claims


def grounding_report(answer: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
    claims = _claims(answer)
    citation_tokens = [_tokenize(str(citation.get("snippet", ""))) for citation in citations]

    grounded_claims = 0
    ungrounded: list[str] = []
    for claim in claims:
        claim_tokens = _tokenize(claim)
        if not claim_tokens:
            continue
        best_overlap = 0.0
        best_shared = 0
        for c_tokens in citation_tokens:
            shared = len(claim_tokens.intersection(c_tokens))
            overlap = shared / len(claim_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
            if shared > best_shared:
                best_shared = shared

        matched = best_shared >= 2 or (best_shared >= 1 and best_overlap >= 0.15)
        if matched:
            grounded_claims += 1
        else:
            ungrounded.append(claim)

    claim_count = len(claims)
    if claim_count == 0:
        score = 1.0 if citations else 0.0
    else:
        score = grounded_claims / claim_count

    return {
        "claims_total": claim_count,
        "claims_grounded": grounded_claims,
        "claims_ungrounded": ungrounded,
        "grounding_score": round(score, 3),
    }
