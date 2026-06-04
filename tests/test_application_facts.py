from application_facts import extract_application_facts
from document_loader import LoadedDocument
from schemas import NOT_EXPLICITLY_STATED


def test_narrative_project_sentence_is_not_extracted_as_title() -> None:
    text = """
    This project will test a digital intervention for adults with chronic conditions.
    Target population: adults with chronic lower limb wounds.
    Study design: feasibility study.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.project_title == NOT_EXPLICITLY_STATED


def test_target_population_trims_dangling_terminal_words_safely() -> None:
    text = """
    Project title: Generic Feasibility Study
    Target population: adults with chronic lower limb wounds, including diabetic foot ulcers and
    Study design: feasibility study.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.target_population == "adults with chronic lower limb wounds, including diabetic foot ulcers"
    assert not facts.target_population.endswith((" and", " an", " including"))


def test_month_milestone_is_never_extracted_as_project_title() -> None:
    text = """
    Month 2: Project governance confirmed
    Target population: older adults at risk of falls.
    Study design: feasibility study.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.project_title == NOT_EXPLICITLY_STATED


def test_synthetic_high_similarity_banner_is_rejected_as_project_title() -> None:
    text = """
    SYNTHETIC HIGH-SIMILARITY TEST PROPOSAL
    Product: Woubot digital wound tool.
    Study design: feasibility study.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.project_title == NOT_EXPLICITLY_STATED


def test_valid_labelled_project_title_extracts_correctly() -> None:
    text = """
    Project title: StepRight movement quality assessment for community falls rehabilitation
    Product: StepRight wearable digital therapeutic.
    Target population: older adults at risk of falls.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.project_title == "StepRight movement quality assessment for community falls rehabilitation"


def test_fallback_title_does_not_use_milestone_gantt_appendix_or_work_package_lines() -> None:
    text = """
    Appendix A: Gantt/workplan
    Work package 1: Discovery and setup
    Gantt chart included
    Month 2: Project governance confirmed
    WP 2: Clinical validation Month start 3 Month end 8
    Target population: older adults at risk of falls.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.project_title == NOT_EXPLICITLY_STATED


def test_trl_is_not_extracted_as_acronym_or_short_name() -> None:
    text = """
    Project title: Digital wound monitoring feasibility study
    Development stage: TRL 5 to TRL 7.
    Product: wound monitoring platform.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.acronym_or_short_name == NOT_EXPLICITLY_STATED


def test_clear_non_generic_module_acronym_extracts() -> None:
    text = """
    Project title: StepRight movement quality assessment for community falls rehabilitation
    The movement quality assessment engine (MQAE) module will support the intervention.
    Product: StepRight wearable digital therapeutic.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.acronym_or_short_name == "MQAE"


def test_main_outcomes_do_not_contain_standalone_endpoint() -> None:
    text = """
    Project title: Wound monitoring feasibility study
    Primary endpoint: endpoint.
    Secondary outcomes: wound area change, time to healing, referrals, usability and safety.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert "endpoint" not in {outcome.lower() for outcome in facts.endpoints}
    assert "wound area change" in {outcome.lower() for outcome in facts.endpoints}


def test_synthetic_test_wording_is_not_ppie_evidence() -> None:
    text = """
    Project title: Digital wound monitoring feasibility study
    The proposal is intentionally near-overlapping to test novelty and similarity detection as PPIE evidence with public contributors.
    Study design: feasibility study.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.ppie_plan == NOT_EXPLICITLY_STATED


def test_outcomes_are_deduplicated_and_concise() -> None:
    text = """
    Project title: Woubot feasibility study
    Primary endpoint: prediction of delayed wound healing by 30 days.
    Secondary endpoints include wound area change, wound area change, time to healing, referrals, nurse documentation time, usability, EQ-5D-5L and safety.
    The primary endpoint is prediction of delayed wound healing by 30 days and secondary endpoints include wound area change, time to healing, referrals, usability, EQ-5D-5L and safety.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])
    lowered = [item.lower() for item in facts.endpoints]

    assert lowered.count("wound area change") == 1
    assert "endpoint" not in lowered
    assert "the primary endpoint is prediction of delayed wound healing by 30 days and secondary endpoints include wound area change, time to healing, referrals, usability, eq-5d-5l and safety" not in lowered


def test_movement_quality_assessment_engine_module_acronym_extracts_mqae() -> None:
    text = """
    Project title: StepRight community rehabilitation study
    The movement quality assessment engine (MQAE) module will support balance rehabilitation.
    Product: StepRight wearable digital therapeutic.
    """

    facts = extract_application_facts([LoadedDocument(name="stepright.txt", text=text)])

    assert facts.acronym_or_short_name == "MQAE"


def test_trl_acronym_is_rejected_even_near_platform_context() -> None:
    text = """
    Project title: Digital wound monitoring feasibility study
    The wound monitoring platform is at current TRL 5 and targets TRL 7.
    Product: wound monitoring platform.
    """

    facts = extract_application_facts([LoadedDocument(name="app.txt", text=text)])

    assert facts.acronym_or_short_name == NOT_EXPLICITLY_STATED


def test_uncertain_work_package_count_extracts_present_not_singular_plural_mismatch() -> None:
    text = """
    Project title: Project management plan
    The project management plan includes work packages, milestones, a Gantt timeline and a risk register.
    """

    facts = extract_application_facts([LoadedDocument(name="pm.txt", text=text)])

    assert "work packages present" in facts.project_management_plan
    assert "1 work packages" not in facts.project_management_plan


def test_distinct_current_and_target_trl_extract_as_range_evidence() -> None:
    text = """
    Project title: Development study
    The platform is at current TRL 5 and has target TRL 7 by project close.
    """

    facts = extract_application_facts([LoadedDocument(name="trl.txt", text=text)])

    assert facts.trl_evidence == "TRL 5 to TRL 7"
