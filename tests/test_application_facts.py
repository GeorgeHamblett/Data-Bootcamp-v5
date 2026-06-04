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
