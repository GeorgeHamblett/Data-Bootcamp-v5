import re

from report_renderer import render_executive_review_note, render_main_case_summary
from schemas import ApplicationFacts


DANGLING_LINE_RE = re.compile(r"\b(and|or|with|a|an|the|including)\.?$", re.I)


def _assert_no_dangling_line_end(markdown: str) -> None:
    for line in markdown.splitlines():
        cleaned = re.sub(r"[*_`#>-]", "", line).strip()
        if not cleaned:
            continue
        assert not DANGLING_LINE_RE.search(cleaned), line


def test_main_case_summary_removes_ellipses_and_dangling_fragments() -> None:
    facts = ApplicationFacts(
        project_title="A concise project title",
        product_or_intervention="Digital intervention",
        target_population="adults with chronic lower limb wounds, including diabetic foot ulcers and",
        endpoints=[
            "wound area change...",
            "time to healing",
            "referrals",
            "usability",
            "safety…",
        ],
        regulatory_plan="The regulatory plan covers UKCA classification, technical documentation, risk management and",
        health_economics_plan="The health economics plan covers EQ-5D-5L, resource use and economic…",
        duration_months="Not explicitly stated",
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "…" not in output
    assert "..." not in output
    assert ".." not in output
    assert re.search(r"Timeline:\*\* Not explicitly stated\.?", output)
    _assert_no_dangling_line_end(output)


def test_executive_review_note_uses_conditional_missing_wording() -> None:
    facts = ApplicationFacts(
        product_or_intervention="Digital intervention",
        target_population="adults with chronic wounds and",
        study_design="A feasibility study",
        sample_size="Not explicitly stated",
        duration_months="Not explicitly stated",
        finance_or_budget_evidence="None identified from available evidence.",
    )

    output = render_executive_review_note(facts, dashboard=[])

    assert re.search(r"Timeline:\*\* Not explicitly stated\.", output)
    assert "Not explicitly stated months" not in output
    assert "with Not explicitly stated" not in output
    assert "None identified from available evidence.." not in output
    assert ".." not in output
    assert "..." not in output
    assert "…" not in output
    _assert_no_dangling_line_end(output)
