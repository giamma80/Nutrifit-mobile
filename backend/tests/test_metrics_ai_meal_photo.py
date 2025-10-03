from metrics.ai_meal_photo import (
    record_request,
    record_latency_ms,
    record_fallback,
    snapshot,
    time_analysis,
    record_error,
    record_failed,
)


def test_metrics_basic_flow() -> None:
    base = snapshot()
    assert (
        all(c["value"] == 0 for c in base["counters"])  # counters zero
        if base["counters"]
        else True
    )

    with time_analysis(phase="stub", source="stub"):
        pass
    record_fallback("PARSE_EMPTY", source="stub")
    record_request(phase="stub", status="completed", source="stub")
    record_latency_ms(10.0, source="stub")
    record_error("PARSE_EMPTY", source="stub")
    record_error("PARSE_EMPTY", source="stub")
    record_failed("PARSE_EMPTY", source="stub")

    data = snapshot()
    req = [c for c in data["counters"] if c["name"] == "ai_meal_photo_requests_total"]
    assert req
    fb = [
        c
        for c in data["counters"]
        if c["name"] == "ai_meal_photo_fallback_total" and c["tags"].get("reason") == "PARSE_EMPTY"
    ]
    assert fb and fb[0]["value"] == 1
    h = [
        h
        for h in data["histograms"]
        if h["name"] == "ai_meal_photo_latency_ms" and h["tags"].get("source") == "stub"
    ]
    assert h and h[0]["count"] >= 2
    errs = [
        c
        for c in data["counters"]
        if c["name"] == "ai_meal_photo_errors_total" and c["tags"].get("code") == "PARSE_EMPTY"
    ]
    assert errs and errs[0]["value"] == 2
    failed = [
        c
        for c in data["counters"]
        if c["name"] == "ai_meal_photo_failed_total" and c["tags"].get("code") == "PARSE_EMPTY"
    ]
    assert failed and failed[0]["value"] == 1
