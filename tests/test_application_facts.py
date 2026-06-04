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
