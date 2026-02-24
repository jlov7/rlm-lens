from rlm_lens.runtime.grounding import grounding_report


def test_grounding_report_detects_grounded_claims() -> None:
    answer = "## Evidence-backed details\n- Retry behavior is configured by RetryPolicy dataclass.\n- Payment calls use with_retries wrapper.\n"
    citations = [
        {"snippet": "class RetryPolicy:\n    max_attempts = 5"},
        {"snippet": "return with_retries(lambda: client.charge(...), DEFAULT_RETRY_POLICY)"},
    ]

    report = grounding_report(answer, citations)
    assert report["claims_total"] == 2
    assert report["claims_grounded"] >= 1
    assert 0.0 <= report["grounding_score"] <= 1.0
