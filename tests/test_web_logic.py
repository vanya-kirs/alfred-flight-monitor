from __future__ import annotations

import json
import subprocess
from pathlib import Path


HTML = Path(__file__).parents[1] / "src" / "alfred_flights" / "web" / "index.html"


def _function_source(name: str) -> str:
    source = HTML.read_text(encoding="utf-8")
    start = source.find(f"function {name}(")
    assert start >= 0, f"missing JavaScript function {name}"
    brace = source.find("{", start)
    depth = 0
    quote = None
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated JavaScript function {name}")


def _run_javascript(functions: list[str], expression: str):
    program = "\n".join(_function_source(name) for name in functions)
    program += f"\nprocess.stdout.write(JSON.stringify({expression}));"
    completed = subprocess.run(
        ["node", "-e", program], check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)


def test_plan_time_helpers_preserve_selected_local_day_and_time() -> None:
    result = _run_javascript(
        ["timestampParts", "combinePlanDateTime"],
        "({parts: timestampParts('2026-12-11T00:30:00+03:00', '+03:00'), "
        "combined: combinePlanDateTime('2026-12-11', '20:30', '+03:00')})",
    )

    assert result == {
        "parts": {"date": "2026-12-11", "time": "00:30"},
        "combined": "2026-12-11T20:30:00+03:00",
    }


def test_recommended_nights_use_calendar_dates_and_preserve_checkout_time() -> None:
    result = _run_javascript(
        ["calendarDayDifference", "recommendedNightsFromJourneys", "recommendedCheckoutAt"],
        "({nights: recommendedNightsFromJourneys('2026-12-10T09:00:00+03:00', "
        "'2026-12-13T18:00:00+03:00'), checkout: recommendedCheckoutAt("
        "'2026-12-10T14:00:00+03:00', '2026-12-15T11:00:00+03:00', 3)})",
    )

    assert result == {
        "nights": 3,
        "checkout": "2026-12-13T11:00:00+03:00",
    }


def test_modifying_timeline_event_preserves_kind_and_sorts_chronologically() -> None:
    result = _run_javascript(
        ["replaceOrCreatePlanEvent"],
        "replaceOrCreatePlanEvent(["
        "{kind:'transfer',title:'Transfer',start_at:'2026-12-10T09:00:00+03:00'},"
        "{kind:'activity',title:'Walk',start_at:'2026-12-10T15:00:00+03:00'}"
        "], 'modify', 0, {kind:'activity',title:'Updated',start_at:'2026-12-10T16:00:00+03:00'})",
    )

    assert [item["title"] for item in result] == ["Walk", "Updated"]
    assert result[1]["kind"] == "transfer"


def test_plan_draft_signature_rejects_stale_dependencies() -> None:
    result = _run_javascript(
        ["canReusePlanDraft"],
        "({same: canReusePlanDraft('flight-1|hotel-1|7', 'flight-1|hotel-1|7'), "
        "stale: canReusePlanDraft('flight-1|hotel-1|7', 'flight-1|hotel-1|5')})",
    )

    assert result == {"same": True, "stale": False}
