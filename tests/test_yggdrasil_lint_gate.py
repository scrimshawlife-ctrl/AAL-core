from __future__ import annotations

from abx_runes.yggdrasil.lint import render_forbidden_crossings_report


def test_lint_report_is_stable_and_nonempty_when_forbidden():
    """Verify lint report format for forbidden crossings."""
    forbidden = [
        {
            "from": "hel.x",
            "to": "asgard.y",
            "reason": "shadow->forecast requires explicit allowed_lanes + evidence bundle; auto-allow forbidden",
        }
    ]
    report = render_forbidden_crossings_report(forbidden)
    assert "forbidden crossings detected" in report
    assert "hel.x -> asgard.y" in report


def test_lint_report_is_clean_when_no_forbidden():
    """Verify lint report format when clean."""
    forbidden = []
    report = render_forbidden_crossings_report(forbidden)
    assert "no forbidden crossings detected" in report
