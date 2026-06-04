import re

from report_renderer import clean_display_value, render_executive_review_note, render_main_case_summary
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


def test_main_case_summary_filters_generic_endpoint_and_milestone_title() -> None:
    facts = ApplicationFacts(
        project_title="Month 2: Project governance confirmed",
        product_or_intervention="Digital intervention",
        endpoints=["endpoint", "primary endpoint", "wound area change"],
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "Project title:** Not explicitly stated" in output
    assert "Project title:** Month 2: Project governance confirmed" not in output
    assert "Main outcomes:** wound area change" in output
    assert "Main outcomes:** endpoint" not in output


def test_summary_and_executive_note_have_clean_complete_lines() -> None:
    facts = ApplicationFacts(
        project_title="A clean project title",
        product_or_intervention="Digital intervention...",
        target_population="adults with chronic wounds and",
        study_design="A feasibility study..",
        sample_size="Not explicitly stated",
        duration_months="Not explicitly stated",
        finance_or_budget_evidence="None identified from available evidence..",
        endpoints=["usability...", "safety…"],
    )

    summary = render_main_case_summary(facts, dashboard=[])
    executive = render_executive_review_note(facts, dashboard=[])
    combined = summary + "\n" + executive

    assert "..." not in combined
    assert "…" not in combined
    assert ".." not in combined
    assert "Not explicitly stated months" not in combined
    assert "with Not explicitly stated" not in combined
    assert re.search(r"Timeline:\*\* Not explicitly stated\.", executive)
    _assert_no_dangling_line_end(combined)


def test_summary_strips_duplicate_labels_from_values() -> None:
    facts = ApplicationFacts(
        study_design="Research design: prospective, multi-site feasibility study",
        comparator_or_control="Comparator or control: usual care",
        health_economics_plan="Health economics: EQ-5D-5L, resource use and QALY analysis",
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "Design:** Research design:" not in output
    assert "Comparator/control:** Comparator or control:" not in output
    assert "Health economics evidence:** Health economics:" not in output
    assert "Design:** prospective, multi-site feasibility study" in output
    assert "Comparator/control:** usual care" in output


def test_woubot_outcomes_render_concise_not_repeated_endpoint_sentences() -> None:
    facts = ApplicationFacts(
        endpoints=[
            "Primary endpoint: prediction of delayed wound healing by 30 days.",
            "Secondary endpoints include wound area change, time to healing, referrals, nurse documentation time, usability, EQ-5D-5L and safety.",
            "The primary endpoint is prediction of delayed wound healing by 30 days and secondary endpoints include wound area change, time to healing, referrals, usability, EQ-5D-5L and safety.",
        ]
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "Main outcomes:** prediction of delayed wound healing by 30 days, wound area change, time to healing, referrals, nurse documentation time, usability, EQ-5D-5L and safety." in output
    assert "The primary endpoint is" not in output
    assert "endpoint" not in re.search(r"Main outcomes:\*\* (.*)", output).group(1).lower()


def test_summary_setting_is_rendered_once_without_explanatory_sentence() -> None:
    facts = ApplicationFacts(sites_or_setting="NHS community wound services")

    output = render_main_case_summary(facts, dashboard=[])

    assert "Setting:** NHS community wound services" in output
    assert "The setting is" not in output
    assert output.count("Setting:**") == 1


def test_missing_setting_renders_not_explicitly_stated_once() -> None:
    output = render_main_case_summary(ApplicationFacts(), dashboard=[])

    assert "Setting:** Not explicitly stated" in output
    assert "The setting is" not in output
    assert output.count("Setting:**") == 1


def test_project_management_evidence_does_not_end_with_are() -> None:
    facts = ApplicationFacts(project_management_plan="30-month plan, seven work packages, Gantt-style timeline, milestones, go/no-go criteria, operational meetings, project board, steering group and risk register are.")

    output = render_main_case_summary(facts, dashboard=[])

    assert "risk register are." not in output
    assert "risk register" in output
    _assert_no_dangling_line_end(output)


def test_synthetic_wording_is_not_rendered_as_ppie_evidence() -> None:
    facts = ApplicationFacts(ppie_plan="The proposal is intentionally near-overlapping to test novelty and similarity detection. PPIE evidence: public contributors shaped it.")

    output = render_main_case_summary(facts, dashboard=[])

    assert "PPIE evidence:** Not explicitly stated" in output
    assert "intentionally near-overlapping" not in output


def test_clean_display_value_handles_values_without_repeated_comma_terms() -> None:
    assert clean_display_value("Review the detailed checklist table") == "Review the detailed checklist table"
    assert clean_display_value("usual care") == "usual care"


def test_clean_display_value_dedupes_repeated_comma_terms() -> None:
    assert clean_display_value("rehabilitation, rehabilitation") == "rehabilitation"


def test_summary_deduplicates_identical_ppie_and_leadership_evidence() -> None:
    facts = ApplicationFacts(
        ppie_plan="PPIE evidence: public contributors shaped recruitment materials.",
        ppie_leadership_evidence="public contributors shaped recruitment materials",
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "PPIE evidence:** Not explicitly stated" in output
    assert "PPIE leadership evidence:** public contributors shaped recruitment materials" in output


def test_comparator_prefix_and_currency_spacing_are_cleaned_in_summary_and_executive_note() -> None:
    facts = ApplicationFacts(
        comparator_or_control="The comparator is usual NHS wound assessment",
        finance_or_budget_evidence="Budget and Finance: Total request is £984, 760 with partner cost of £22, 600.",
    )

    summary = render_main_case_summary(facts, dashboard=[])
    executive = render_executive_review_note(facts, dashboard=[])
    combined = summary + "\n" + executive

    assert "Comparator/control:** usual NHS wound assessment" in summary
    assert "Comparator/control:** The comparator is" not in summary
    assert "£984,760" in combined
    assert "£22,600" in combined
    assert clean_display_value("Total budget £1, 250, 000") == "Total budget £1,250,000"
    assert "£984, 760" not in combined
    assert "£22, 600" not in combined


def test_summary_never_renders_one_work_packages() -> None:
    facts = ApplicationFacts(project_management_plan="1 work package, milestones and risk register")

    output = render_main_case_summary(facts, dashboard=[])

    assert "1 work package" in output
    assert "1 work packages" not in output


def test_uncertain_work_package_count_renders_work_packages_present() -> None:
    facts = ApplicationFacts(project_management_plan="work packages present, milestones and risk register")

    output = render_main_case_summary(facts, dashboard=[])

    assert "work packages present" in output
    assert "1 work packages" not in output


def test_summary_trl_current_and_target_render_as_range() -> None:
    facts = ApplicationFacts(
        current_trl_or_stage="TRL 5",
        target_trl_or_stage="TRL 7",
        trl_evidence="TRL 5, TRL 7",
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "Development stage:** TRL 5 to TRL 7" in output
    assert "Development stage:** TRL 5, TRL 7" not in output


def test_health_economics_evidence_does_not_end_as_vague_resource_use_data_fragment() -> None:
    facts = ApplicationFacts(
        health_economics_plan="Resource use data. Resource use data will support the health economic modelling."
    )

    output = render_main_case_summary(facts, dashboard=[])

    assert "Health economics evidence:** Resource use data." not in output
    assert "Resource use data will support the health economic modelling" in output


def test_regulatory_evidence_is_concise_and_not_duplicated() -> None:
    facts = ApplicationFacts(
        regulatory_plan=(
            "Integration will follow IEC 62304, ISO 14971 and ISO 13485, with UKCA-related "
            "technical documentation and risk management. To integrate MQAE, integration will follow "
            "IEC 62304, ISO 14971 and ISO 13485, with UKCA-related technical documentation and risk management."
        )
    )

    output = render_main_case_summary(facts, dashboard=[])
    regulatory_line = re.search(r"Regulatory/adoption evidence:\*\* (.*)", output).group(1)

    assert "Integration will follow IEC 62304, ISO 14971 and ISO 13485" in regulatory_line
    assert regulatory_line.lower().count("integration will follow") == 1
    assert "To integrate" not in regulatory_line
