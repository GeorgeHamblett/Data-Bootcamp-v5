"""Generic deterministic application fact extraction.

The extractor reads every runtime application/supporting document supplied to it. It
uses reusable patterns for NIHR/RSS applications and deliberately ignores document
labels such as training/example banners. Built-in guidance should never be passed in.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

from document_loader import LoadedDocument
from schemas import ApplicationFacts, NOT_EXPLICITLY_STATED

NOISE_PATTERNS = [
    r"FOR\s+TRAINING\s+USE\s+ONLY",
    r"TRAINING\s+USE\s+ONLY",
    r"FICTIONAL\s+EXAMPLE\s+APPLICATION",
    r"SYNTHETIC\s+EXEMPLAR",
    r"DUMMY\s+APPLICATION",
    r"\b(?:fictional|invented|training only|dummy)\b",
]

PRODUCT_STOPWORDS = {"the", "a", "an", "it", "this", "we"}
DISCLAIMER_RE = re.compile(r"\b(?:fictional|invented|training only|synthetic exemplar|dummy)\b", re.I)
SYNTHETIC_EVIDENCE_RE = re.compile(
    r"synthetic proposal|high-similarity test|intentionally near-overlapping|"
    r"test novelty and similarity detection|fictional|dummy|training use only|exemplar",
    re.I,
)

FIELD_PATTERNS = {
    "product_or_intervention": [r"(?:intervention\s*/\s*product|product\s*/\s*intervention|product|intervention|innovation|service|device|software|programme|program|model|method)\s*[:\-]\s*(.+)"],
    "acronym_or_short_name": [r"(?:acronym|short\s+name|module)\s*[:\-]\s*(.+)"],
    "target_population": [r"(?:target\s+population|population)\s*[:\-]\s*(.+)"],
    "clinical_or_social_care_need": [r"(?:clinical\s+need|social\s+care\s+need|need|problem)\s*(?:is|are|[:\-])\s*(.+)"],
    "technology_type": [r"(?:technology\s+type|intervention\s+type)\s*[:\-]\s*(.+)"],
    "study_design": [r"(?:study\s+design|design)\s*[:\-]\s*(.+)"],
    "sites_or_setting": [r"(?:sites?|setting)\s*[:\-]\s*(.+)"],
    "project_title": [r"(?:project\s+title|application\s+title|proposal\s+title|title)\s*[:\-]\s*(.+)"],
    "application_claimed_call": [r"(?:funding\s+call|funding\s+opportunity|claimed\s+call|programme)\s*[:\-]\s*(.+)"],
    "applicant_or_lead": [r"(?:lead\s+applicant|chief\s+investigator|principal\s+investigator|applicant\s+lead)\s*[:\-]\s*(.+)"],
    "contracting_organisation": [r"(?:contracting\s+organisation|contracting\s+organization|host\s+organisation|sponsor)\s*[:\-]\s*(.+)"],
    "methodology": [r"(?:methodology|methods?)\s*[:\-]\s*(.+)"],
    "next_stage_plan": [r"(?:next\s+stage|future\s+work|next\s+step)\s*[:\-]\s*(.+)"],
}

PRODUCT_PATTERNS = [
    r"(?:called|known as|named)\s+([A-Z][A-Za-z0-9\-]{2,}(?:\s+[A-Z][A-Za-z0-9\-]{2,}){0,3})",
    r"\b([A-Z][A-Za-z0-9\-]{2,})\s+(?:platform|system|intervention|device|software|programme|program|service|model|method|tool)\b",
    r"\b([A-Z][A-Za-z0-9\-]{2,})\s*,\s+a\s+(?:wearable|digital|software|device|service|programme|program|platform|system)",
]

ACRONYM_PATTERNS = [
    r"\(([A-Z][A-Z0-9\-]{2,10})\)",
    r"(?:abbreviated as|short name|acronym|module called)\s+([A-Z][A-Z0-9\-]{2,10})\b",
]

GENERIC_ACRONYMS = {
    "TRL", "NHS", "NIHR", "PPI", "PPIE", "QALY", "UKCA", "DTAC",
    "IRAS", "ISO", "IEC", "RAG", "JSON", "AI", "ML", "API",
}

KEYWORDS = {
    "population": [r"aged\s+\d+\s+(?:and\s+over|or\s+over|\+)", r"older adults?", r"children with", r"patients with", r"adults with", r"service users with", r"people with"],
    "need": [r"unmet need", r"clinical need", r"social care problem", r"burden", r"pressure", r"reduced independence", r"rehabilitation", r"prevention", r"mobility", r"balance"],
    "technology": [r"AI-enabled", r"wearable", r"digital therapeutic", r"software", r"device", r"platform", r"algorithm", r"model", r"programme", r"service", r"sensor"],
    "study_design": [r"randomi[sz]ed", r"feasibility", r"pilot", r"trial", r"mixed-methods", r"implementation evaluation", r"process evaluation", r"two-arm", r"single-arm", r"cohort", r"qualitative", r"realist", r"observational", r"case study", r"evaluation"],
    "setting": [r"NHS", r"community", r"primary care", r"secondary care", r"social care", r"Trusts?", r"sites?", r"teams?", r"clinics?"],
    "regulatory": [r"UKCA", r"DTAC", r"ISO\s*14971", r"ISO\s*13485", r"ISO\s*\d+", r"IEC\s*62304", r"IEC\s*\d+", r"MHRA", r"ethics", r"IRAS", r"medical device classification", r"medical device", r"technical documentation", r"risk management", r"software lifecycle", r"quality management system", r"regulatory approval", r"UKCA classification"],
    "health_economics": [r"health economist", r"perspective", r"comparator", r"current care", r"usual care", r"EQ-5D", r"HRQoL", r"QALY", r"resource use", r"micro-costing", r"cost-effectiveness", r"budget impact", r"decision-analytic", r"economic model", r"ICER", r"ROI", r"sensitivity", r"scenario", r"value proposition", r"commissioning"],
    "ppie": [r"public contributors?", r"PPIE?", r"working with people and communities", r"co-design", r"carers?", r"lived experience", r"public co-applicant", r"advisory group", r"payment", r"expenses", r"shaped"],
    "inclusion": [r"underserved", r"underrepresented", r"inequalities", r"digital exclusion", r"accessibility", r"interpreters", r"sex", r"gender", r"ethnicity", r"disability", r"caring responsibilities", r"inclusion costs", r"accessible dissemination"],
    "finance": [r"budget section", r"cost justification", r"staff costs", r"equipment", r"travel", r"subsistence", r"PPIE costs", r"inclusion costs", r"AcoRD", r"SoECAT", r"current rates", r"funding rate", r"scheme cap", r"support costs", r"treatment costs", r"cost category"],
}

ENDPOINT_RE = re.compile(
    r"\b(?:Berg Balance Scale|Timed Up and Go|Activities-specific Balance Confidence(?: scale)?|EQ-5D-5L|EQ-5D|SUS|PSSUQ|prediction of delayed wound healing by 30 days|wound area change|time to healing|referrals|usability|safety|recruitment|retention|adherence|fidelity|interviews?|primary outcome|secondary outcome|primary endpoint|secondary endpoint|endpoints?|outcomes?)\b",
    re.I,
)


def _clean_text(text: str) -> str:
    cleaned = text
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.I)
    return cleaned


DANGLING_TERMINAL_WORDS_RE = re.compile(r"\b(and|or|with|including|using|by|for|to|the|a|an|are|is)\.?$", re.I)


def _remove_dangling_terminal_words(value: str) -> str:
    cleaned = re.sub(r"\.{2,}|…", ".", value or "").strip(" .;:\n\t,/-")
    while cleaned and DANGLING_TERMINAL_WORDS_RE.search(cleaned):
        cleaned = DANGLING_TERMINAL_WORDS_RE.sub("", cleaned).strip(" .;:\n\t,/-")
    return cleaned


def _short(value: str, limit: int = 260) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" .;:\n\t")
    if len(cleaned) <= limit:
        return _remove_dangling_terminal_words(cleaned)
    truncated = cleaned[:limit].rsplit(" ", 1)[0].strip(" .;:\n\t")
    return _remove_dangling_terminal_words(truncated or cleaned[:limit].rstrip())


def _sentences(text: str) -> list[str]:
    return [_short(s, 500) for s in re.split(r"(?<=[.!?])\s+|\n+", text) if _short(s, 500)]


def _find_first(text: str, patterns: list[str]) -> tuple[str, str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.M)
        if match:
            value = _short(match.group(1).splitlines()[0])
            if _is_noise(value):
                continue
            return value, _short(match.group(0))
    return None


def _is_noise(value: str) -> bool:
    return bool(SYNTHETIC_EVIDENCE_RE.search(value or "")) or any(re.search(p, value, re.I) for p in NOISE_PATTERNS)


def _is_disclaimer(value: str) -> bool:
    return bool(DISCLAIMER_RE.search(value))


def _valid_product_candidate(value: str) -> bool:
    cleaned = _short(value, 120).strip(" \"'.,;:")
    return bool(cleaned and cleaned != NOT_EXPLICITLY_STATED and cleaned.lower() not in PRODUCT_STOPWORDS and not _is_noise(cleaned))


def _sentence_with(text: str, patterns: list[str], limit: int = 320) -> str | None:
    for sentence in _sentences(text):
        if _is_noise(sentence):
            continue
        if any(re.search(pattern, sentence, re.I) for pattern in patterns):
            return _short(sentence, limit)
    return None


def _sentences_with(text: str, patterns: list[str], max_items: int = 6, limit: int = 220) -> list[str]:
    results: list[str] = []
    for sentence in _sentences(text):
        if _is_noise(sentence):
            continue
        if any(re.search(pattern, sentence, re.I) for pattern in patterns):
            cleaned = _short(sentence, limit)
            if cleaned and cleaned not in results:
                results.append(cleaned)
        if len(results) >= max_items:
            break
    return results


def _first_matching_product(text: str) -> str | None:
    for pattern in PRODUCT_PATTERNS:
        for match in re.finditer(pattern, text):
            candidate = _short(match.group(1), 80)
            if not _valid_product_candidate(candidate):
                continue
            return candidate
    return None


def _is_generic_acronym(candidate: str) -> bool:
    text = candidate.strip().upper()
    first_token = re.split(r"\s+|[:;,.()\-/]", text)[0] if text else ""
    return text in GENERIC_ACRONYMS or first_token in GENERIC_ACRONYMS


def _first_acronym(text: str, product: str | None = None) -> str | None:
    if product:
        lead = re.match(r"([A-Z][A-Za-z0-9]+(?:[-–][A-Z0-9][A-Za-z0-9]*)+)", product)
        if lead and not _is_generic_acronym(lead.group(1)):
            return lead.group(1)

    labelled = _find_first(text, FIELD_PATTERNS["acronym_or_short_name"])
    if labelled:
        match = re.search(r"\b([A-Z][A-Z0-9\-]{2,10})\b", labelled[0])
        if match and not _is_generic_acronym(match.group(1)):
            return match.group(1)

    component_context = re.compile(
        r"\b(?:product|intervention|method|engine|component|module|platform|system|device|software|algorithm|model|tool)\b",
        re.I,
    )
    named_component_acronym = re.compile(
        r"\b(?:[A-Za-z][A-Za-z0-9-]+\s+){0,10}"
        r"(?:assessment\s+engine|component|method|engine|module|platform|intervention|algorithm|model|tool|system)\s*"
        r"\(([A-Z][A-Z0-9-]{2,10})\)"
        r"(?:\s+(?:module|engine|component|platform|algorithm|model|tool|system))?",
        re.I,
    )
    for sentence in _sentences(text):
        if not component_context.search(sentence):
            continue
        for match in named_component_acronym.finditer(sentence):
            candidate = match.group(1).strip().upper()
            if not _is_generic_acronym(candidate):
                return candidate
        for pattern in ACRONYM_PATTERNS:
            for match in re.finditer(pattern, sentence):
                candidate = match.group(1).strip().upper()
                if _is_generic_acronym(candidate):
                    continue
                return candidate
    return None

def _extract_sample_size(text: str) -> str:
    labelled = re.search(
        r"sample\s+size\s*[:\-]\s*(\d+)\s*participants?\s+recruited\s*[;,]?\s*(\d+)\s+expected\s+evaluable\s+participants?",
        text,
        re.I,
    )
    if labelled:
        return f"{labelled.group(1)} participants recruited; {labelled.group(2)} expected evaluable participants"
    labelled_line = re.search(r"sample\s+size\s*[:\-]\s*([^\n.]{8,220})", text, re.I)
    if labelled_line:
        line = _short(labelled_line.group(1), 220)
        if re.search(r"\b\d+\s+participants?\s+recruited\b", line, re.I):
            evaluable = re.search(r"(\d+)\s+expected\s+evaluable\s+participants?", line, re.I)
            recruited = re.search(r"(\d+)\s+participants?\s+recruited", line, re.I)
            if recruited and evaluable:
                return f"{recruited.group(1)} participants recruited; {evaluable.group(1)} expected evaluable participants"
            return line
    patterns = [
        r"(?:sample size\s*(?:of)?|target(?:\s+sample)?(?:\s+of)?|n\s*=)\s*(?:approximately|about|around)?\s*(\d+)\s*(participants?|people|patients?|service users?)?",
        r"(?:recruit(?:ed)?\s+(?:a\s+)?target\s+of\s*(?:approximately|about|around)?\s*)(\d+)\s*(participants?|people|patients?|service users?)",
        r"(?:approximately|about|around)\s*(\d+)\s*(participants?|people|patients?|service users?)",
        r"\b(\d+)\s*(participants?|people|patients?|service users?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            context = text[max(0, match.start() - 40): match.end() + 60]
            if re.search(r"with\s+events|event\s+count|events?\b", context, re.I) and not re.search(r"sample size|recruit", context, re.I):
                continue
            unit = match.group(2) if len(match.groups()) > 1 and match.group(2) else "participants"
            return f"{match.group(1)} {unit}"
    return NOT_EXPLICITLY_STATED


def _extract_duration(text: str, work_packages: list[str]) -> str:
    """Prefer the latest explicit project month over a first phase length."""
    max_end_month = 0
    for pattern in [
        r"months?\s*(\d{1,3})\s*[-–]\s*(\d{1,3})",
        r"month\s*start\s*(\d{1,3})\s*month\s*end\s*(\d{1,3})",
        r"month\s*(\d{1,3})\s*[:\-–]",
        r"month\s*end\s*(\d{1,3})",
    ]:
        for match in re.finditer(pattern, text, re.I):
            nums = [int(g) for g in match.groups() if g]
            if nums:
                max_end_month = max(max_end_month, nums[-1], *nums)
    for row in work_packages:
        for number in re.findall(r"month\s*(?:end\s*)?(\d{1,3})|months?\s*\d{1,3}\s*[-–]\s*(\d{1,3})", row, re.I):
            vals = [int(v) for v in number if v]
            if vals:
                max_end_month = max(max_end_month, *vals)
    if max_end_month:
        return str(max_end_month)
    labelled = re.search(r"(?:duration|over|programme|program|plan|runs?|single)\D{0,30}(\d{1,3})\s*[- ]?months?", text, re.I)
    if labelled:
        return labelled.group(1)
    return NOT_EXPLICITLY_STATED


STUDY_DESIGN_TERMS = [
    r"randomi[sz]ed", r"feasibility", r"pilot", r"trial", r"mixed-methods",
    r"implementation evaluation", r"process evaluation", r"two-arm", r"single-arm",
    r"cohort", r"qualitative", r"realist", r"observational", r"case study", r"evaluation",
]
BACKGROUND_TERMS = [r"workforce", r"constraint", r"burden", r"pressure", r"problem", r"background", r"many people", r"falls can"]


def _best_sentence(text: str, include: list[str], exclude: list[str] | None = None, limit: int = 320) -> str | None:
    scored: list[tuple[int, str]] = []
    for sentence in _sentences(text):
        if _is_noise(sentence):
            continue
        hits = sum(1 for pattern in include if re.search(pattern, sentence, re.I))
        if not hits:
            continue
        bad = sum(1 for pattern in (exclude or []) if re.search(pattern, sentence, re.I))
        if bad and hits < 2:
            continue
        labelled = 3 if re.search(r"(?:study\s+design|design|methods?)\s*[:\-]", sentence, re.I) else 0
        scored.append((hits * 3 + labelled - bad * 2, _short(re.sub(r"^(?:study\s+design|design|methods?)\s*[:\-]\s*", "", sentence, flags=re.I), limit)))
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], len(x[1])), reverse=True)
    return scored[0][1]



def _extract_sites_or_setting(text: str) -> str | None:
    """Prefer explicit NHS/service setting phrases over generic partner/team mentions."""
    for sentence in _sentences(text):
        if _is_noise(sentence) or re.match(r"partners? include", sentence, re.I):
            continue
        match = re.search(
            r"(NHS\s+community[^.;,\n]{0,140}(?:services?|clinics?|teams?|trusts?|sites?|settings?|rehabilitation))",
            sentence,
            re.I,
        )
        if match:
            return _short(match.group(1), 180)
    for sentence in _sentences(text):
        if _is_noise(sentence) or re.match(r"partners? include", sentence, re.I):
            continue
        if re.search(r"community rehabilitation|primary care|secondary care|social care", sentence, re.I):
            return _short(sentence, 180)
    return None


def _extract_study_design(text: str) -> str | None:
    return _best_sentence(text, STUDY_DESIGN_TERMS, BACKGROUND_TERMS, 260)


def _extract_target_population(text: str) -> str | None:
    explicit = _find_first(text, FIELD_PATTERNS["target_population"])
    if explicit:
        return explicit[0]
    patterns = [
        r"participants?\s+(aged\s+\d+\s+(?:and\s+over|or\s+over|\+)[^.;\n]{0,90})",
        r"((?:older adults?|adults|children|patients|people|service users)\s+(?:aged\s+\d+\s+(?:and\s+over|or\s+over|\+))?[^.;\n]{0,100}(?:risk of fall|falls risk|balance confidence|with [^.;\n]{3,60}))",
        r"designed to help\s+((?:older adults?|adults|children|patients|people|service users)[^.;\n]{0,100})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return _short(m.group(1), 180)
    return None


def _extract_clinical_need(text: str) -> str | None:
    explicit = _find_first(text, FIELD_PATTERNS["clinical_or_social_care_need"])
    if explicit:
        return explicit[0]
    sentence = _best_sentence(text, [r"falls? prevention", r"reduce risk of falling", r"balance", r"mobility rehabilitation", r"confidence", r"independence", r"rehabilitation"], [], 220)
    if not sentence:
        return None
    fragments: list[str] = []
    for pat in [r"falls? prevention", r"falls? risk", r"risk of falling", r"reduce risk of falling", r"balance(?: confidence)?", r"mobility rehabilitation", r"confidence", r"independence", r"rehabilitation"]:
        for m in re.finditer(pat, sentence, re.I):
            val = m.group(0).lower()
            if val not in fragments:
                fragments.append(val)
    return _short(", ".join(fragments) or sentence, 180)


def _extract_technology_type(text: str) -> str | None:
    explicit = _find_first(text, FIELD_PATTERNS["technology_type"])
    if explicit:
        return explicit[0]
    concepts: list[str] = []
    for pat in [r"AI-enabled wearable digital therapeutic", r"wearable digital therapeutic", r"movement quality assessment (?:engine|platform)", r"digital therapeutic", r"wearable", r"platform", r"software as a medical device", r"algorithm"]:
        if re.search(pat, text, re.I):
            val = re.search(pat, text, re.I).group(0)
            if val.lower() not in [c.lower() for c in concepts]:
                concepts.append(val)
    return _short(" / ".join(concepts[:3]), 180) if concepts else None


def _extract_weighted_plan(text: str, patterns: list[str], weaker: list[str] | None = None, max_items: int = 4) -> str | None:
    scored: list[tuple[int, str]] = []
    for sentence in _sentences(text):
        if _is_noise(sentence):
            continue
        hits = sum(1 for p in patterns if re.search(p, sentence, re.I))
        if not hits:
            continue
        weak_hits = sum(1 for p in (weaker or []) if re.search(p, sentence, re.I))
        if re.match(r"\s*(?:WP\d+|WP\s+\d+|Month\s+\d+|Endpoints include)", sentence, re.I) and hits < 3:
            continue
        score = hits * 3 + weak_hits
        scored.append((score, _short(sentence, 400)))
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    out=[]
    for _, sentence in scored:
        if sentence not in out:
            out.append(sentence)
        if len(out) >= max_items:
            break
    return "; ".join(out)


REGULATORY_STRONG = [r"UKCA", r"DTAC", r"ISO\s*14971", r"ISO\s*13485", r"IEC\s*62304", r"MHRA", r"medical device classification", r"technical documentation", r"risk management", r"software lifecycle", r"quality management system"]
REGULATORY_WEAK = [r"ethics", r"IRAS"]
HEALTH_ECON_STRONG = [r"health economist", r"perspective", r"EQ-5D", r"HRQoL", r"QALY", r"resource use", r"micro-costing", r"cost-effectiveness", r"decision-analytic", r"economic model", r"budget impact", r"ICER", r"sensitivity", r"scenario", r"commissioning", r"value proposition"]
HEALTH_ECON_WEAK = [r"comparator", r"current care", r"usual care"]
PPIE_LEADERSHIP = [r"named\s+PPIE?\s+lead", r"PPIE?\s+leadership", r"PPIE?\s+coordinat(?:or|ion)", r"co-applicant[^.]{0,80}PPIE?\s+coordination", r"public contributor lead", r"lived experience advisory group lead", r"dedicated\s+PPIE?\s+lead"]

PPIE_ONLY_RE = re.compile(r"\b(?:PPIE?|public contributors?|public advisory group|payment|expenses|Community Voice)\b", re.I)
INCLUSION_STRONG = [r"inclusive research", r"named inclusion lead", r"sex", r"gender", r"ethnicity", r"deprivation", r"language", r"literacy", r"digital exclusion", r"mobility", r"skin tone", r"community access", r"underserved", r"accessibility"]


def _extract_ppie_leadership(text: str) -> str | None:
    return _sentence_with(text, PPIE_LEADERSHIP, 300)


def _extract_research_inclusion(text: str) -> str | None:
    candidates: list[tuple[int, str]] = []
    for sentence in _sentences(text):
        if _is_noise(sentence):
            continue
        hits = sum(1 for p in INCLUSION_STRONG if re.search(p, sentence, re.I))
        if not hits:
            continue
        if PPIE_ONLY_RE.search(sentence) and hits < 2:
            continue
        labelled = 6 if re.search(r"inclusive research|named inclusion lead|sex and gender", sentence, re.I) else 0
        candidates.append((hits * 3 + labelled, _short(sentence, 420)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], len(x[1])))
    return candidates[0][1]


def _extract_uploads(text: str) -> list[str]:
    patterns = [r"Gantt chart(?: is)? included", r"project management plan(?: is)? (?:included|uploaded|provided)", r"references? (?:uploaded|included|provided)", r"flow diagram(?: is)? (?:included|uploaded|provided)", r"logic model(?: is)? (?:included|uploaded|provided)", r"SoECAT(?: is)? (?:included|uploaded|provided)", r"budget spreadsheet(?: is)? (?:included|uploaded|provided)", r"CVs? (?:uploaded|included|provided)", r"letters? of support (?:uploaded|included|provided)"]
    return _sentences_with(text, patterns, 10, 180)


def _extract_references(text: str) -> str | None:
    for sentence in _sentences(text):
        if re.search(r"^(references|bibliography)\s*[:\-]", sentence, re.I) or re.search(r"references?\s+(?:uploaded|included|provided)", sentence, re.I):
            return _short(sentence, 180)
    return None


def _extract_trl(text: str) -> tuple[str, str, str, list[str]]:
    progression = re.search(r"TRL\s*(\d\s*(?:[-–]\s*\d)?)\s*(?:to|→|->|progress(?:es)?\s+to)\s*TRL?\s*(\d\s*(?:[-–]\s*\d)?)", text, re.I)
    if progression:
        return f"TRL {progression.group(1).replace(' ', '')}", f"TRL {progression.group(2).replace(' ', '')}", _short(progression.group(0)), []
    current = re.search(r"current\s+TRL\s*[:\-]?\s*(\d\s*(?:[-–]\s*\d)?)", text, re.I)
    target = re.search(r"target\s+TRL\s*[:\-]?\s*(\d\s*(?:[-–]\s*\d)?)", text, re.I)
    if current or target:
        cur = f"TRL {current.group(1).replace(' ', '')}" if current else NOT_EXPLICITLY_STATED
        tar = f"TRL {target.group(1).replace(' ', '')}" if target else NOT_EXPLICITLY_STATED
        return cur, tar, "; ".join(x for x in [cur, tar] if x != NOT_EXPLICITLY_STATED), []
    trls = re.findall(r"TRL\s*\d\s*(?:[-–]\s*\d)?", text, re.I)
    if trls:
        return _short(trls[0]), _short(trls[1]) if len(trls) > 1 else NOT_EXPLICITLY_STATED, "; ".join(trls[:3]), []
    return NOT_EXPLICITLY_STATED, NOT_EXPLICITLY_STATED, NOT_EXPLICITLY_STATED, []


def _extract_gantt_rows(text: str) -> list[str]:
    rows: list[str] = []
    line_patterns = [
        r"^\s*(?:WP\s*\d+|Work package\s*\d+)[:\-– ]+.{8,220}$",
        r"^\s*[^\n|]{3,90}\|\s*Month\s*\d{1,3}\s*\|\s*Month\s*\d{1,3}\s*\|.{0,180}$",
        r"^\s*(?:WP\s*\d+\s+)?[^\n]{3,100}\s+Month\s+start\s+\d{1,3}\s+Month\s+end\s+\d{1,3}[^\n]{0,160}$",
    ]
    for raw_line in text.splitlines():
        line = _short(raw_line, 240)
        if not line or _is_noise(line):
            continue
        if any(re.search(p, line, re.I) for p in line_patterns):
            if len(line) <= 240 and line not in rows:
                rows.append(line)
    if rows:
        return rows[:30]
    # Some document loaders flatten table rows; recover concise WP rows from running text.
    for match in re.finditer(r"\b(WP\s*\d+[:\-– ]+.{8,180}?)(?=\s+WP\s*\d+[:\-– ]+|\n|$)", text, re.I | re.S):
        row = _short(match.group(1), 240)
        if row and len(row.split()) <= 28 and row not in rows:
            rows.append(row)
    return rows[:30]


def _extract_milestones(text: str) -> list[str]:
    milestones: list[str] = []
    excluded = [r"^milestones$", r"^timeline and milestones$", r"gantt chart (?:is )?included"]
    for raw_line in text.splitlines():
        line = _short(raw_line, 220)
        match = re.match(r"^\s*Month\s*(\d{1,3})\s*[:\-– ]\s*(.{8,180})$", line, re.I)
        if not match:
            continue
        action = _short(match.group(2), 180)
        if any(re.search(p, action, re.I) for p in excluded):
            continue
        if not re.search(r"[a-z]{4,}", action, re.I):
            continue
        value = _short(f"Month {match.group(1)}: {action}", 220)
        if value not in milestones:
            milestones.append(value)
    if milestones:
        return milestones[:20]
    for match in re.finditer(r"\bMonth\s*(\d{1,3})\s*[:\-– ]\s*([^\n.]{8,180})", text, re.I):
        action = _short(match.group(2), 180)
        if any(re.search(p, action, re.I) for p in excluded):
            continue
        if not re.search(r"[a-z]{4,}", action, re.I):
            continue
        value = _short(f"Month {match.group(1)}: {action}", 220)
        if value not in milestones:
            milestones.append(value)
    return milestones[:20]


GENERIC_OUTCOME_LABELS = {"endpoint", "endpoints", "primary endpoint", "secondary endpoint", "outcome", "outcomes", "primary outcome", "secondary outcome"}

OUTCOME_CANONICAL_PATTERNS = [
    (r"prediction of delayed wound healing by 30 days", "prediction of delayed wound healing by 30 days"),
    (r"wound area change", "wound area change"),
    (r"time to healing", "time to healing"),
    (r"referrals?", "referrals"),
    (r"nurse documentation time", "nurse documentation time"),
    (r"usability", "usability"),
    (r"recruitment", "recruitment"),
    (r"retention", "retention"),
    (r"adherence", "adherence"),
    (r"fidelity", "fidelity"),
    (r"EQ-5D-5L", "EQ-5D-5L"),
    (r"safety", "safety"),
    (r"Berg Balance Scale", "Berg Balance Scale"),
    (r"Timed Up and Go", "Timed Up and Go"),
    (r"Activities-specific Balance Confidence(?: scale)?", "Activities-specific Balance Confidence scale"),
    (r"SUS", "SUS"),
    (r"PSSUQ", "PSSUQ"),
    (r"interviews?", "interviews"),
]


def _clean_outcome_candidate(value: str) -> str:
    cleaned = _short(value, 220)
    cleaned = re.sub(r"^(?:primary|secondary)\s+(?:endpoint|outcome)s?\s*[:\-]\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^(?:endpoint|outcome)s?\s*(?:include|includes|are|:|-)\s*", "", cleaned, flags=re.I)
    return _short(cleaned, 220)


def _outcome_measures_in_text(value: str) -> list[str]:
    measures: list[str] = []
    for pattern, label in OUTCOME_CANONICAL_PATTERNS:
        if re.search(rf"\b{pattern}\b", value, re.I) and label.lower() not in [m.lower() for m in measures]:
            measures.append(label)
    return measures


def _extract_endpoints(text: str) -> list[str]:
    endpoints: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        cleaned = _clean_outcome_candidate(value)
        key = cleaned.lower().strip(" .;:")
        if not key or key in GENERIC_OUTCOME_LABELS:
            return
        if key not in seen:
            seen.add(key)
            endpoints.append(cleaned)

    for sentence in _sentences_with(text, [r"endpoint", r"outcome measure", r"primary outcome", r"secondary outcome", r"primary endpoint", r"secondary endpoint", r"outcomes? include"], 12, 300):
        for measure in _outcome_measures_in_text(sentence):
            add(measure)

    for match in ENDPOINT_RE.finditer(text):
        for measure in _outcome_measures_in_text(match.group(0)) or [match.group(0)]:
            add(measure)

    return endpoints[:12]


def _extract_project_management_plan(text: str, duration_months: str, work_packages: list[str], milestones: list[str]) -> str | None:
    if not re.search(r"project management|work packages?|Gantt|milestones?|go/no-go|steering group|risk register|project board", text, re.I):
        return None
    bits: list[str] = []
    if duration_months != NOT_EXPLICITLY_STATED:
        bits.append(f"{duration_months}-month plan")
    wp_count = len(work_packages)
    explicit_wp_count = re.search(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2})\s+work packages?\b",
        text,
        re.I,
    )
    if explicit_wp_count:
        raw_count = explicit_wp_count.group(1).lower()
        word_counts = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        }
        count = word_counts.get(raw_count, int(raw_count) if raw_count.isdigit() else 0)
        bits.append(f"{count} work package" if count == 1 else f"{count} work packages")
    elif wp_count == 1:
        bits.append("1 work package")
    elif wp_count > 1:
        bits.append(f"{wp_count} work packages")
    elif re.search(r"work packages?", text, re.I):
        bits.append("work packages present")
    if re.search(r"Gantt(?:-style)?|timeline", text, re.I):
        bits.append("Gantt-style timeline")
    if milestones or re.search(r"milestones?", text, re.I):
        bits.append("milestones")
    if re.search(r"go/no-go|go no go", text, re.I):
        bits.append("go/no-go criteria")
    if re.search(r"operational meetings?", text, re.I):
        bits.append("operational meetings")
    if re.search(r"project board", text, re.I):
        bits.append("project board")
    if re.search(r"steering group", text, re.I):
        bits.append("steering group")
    if re.search(r"risk register", text, re.I):
        bits.append("risk register")
    deduped=[]
    for bit in bits:
        if bit.lower() not in [b.lower() for b in deduped]:
            deduped.append(bit)
    return _short(", ".join(deduped), 260) if deduped else None

def _extract_market_or_impact(text: str) -> str | None:
    patterns = [r"market and adoption", r"IP and commercialisation", r"knowledge mobilisation", r"dissemination and impact", r"commissioner", r"commercialisation"]
    candidates: list[tuple[int, str]] = []
    for sentence in _sentences(text):
        if _is_noise(sentence) or _is_disclaimer(sentence):
            continue
        if re.search(r"health economics|budget impact|QALY|cost-utility|sensitivity analysis", sentence, re.I):
            continue
        hits = sum(1 for p in patterns if re.search(p, sentence, re.I))
        if hits:
            labelled = 6 if re.search(r"market and adoption|IP and commercialisation|knowledge mobilisation", sentence, re.I) else 0
            candidates.append((hits * 3 + labelled, _short(sentence, 360)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], len(x[1])))
    return candidates[0][1]


def _actual_budget_sentence(text: str) -> str | None:
    """Return real budget evidence, not PPIE/inclusion-cost mentions alone."""
    strong_budget = [
        r"budget and finance", r"budget section", r"budget spreadsheet", r"cost justification", r"justification of costs",
        r"staff costs", r"equipment costs?", r"travel (?:and )?subsistence", r"AcoRD", r"SoECAT",
        r"current rates", r"funding rate", r"scheme cap", r"total grant requested", r"cost categor(?:y|ies)",
        r"detailed budget",
    ]
    ppie_only = [r"PPIE? payment", r"PPIE? costs", r"public contributor", r"expenses"]
    candidates: list[tuple[int, str]] = []
    for sentence in _sentences(text):
        if _is_noise(sentence):
            continue
        if re.search(r"\bno\s+(?:real\s+)?budget|budget[^.]{0,40}(?:not|isn['’]?t|not provided)|no budget spreadsheet", sentence, re.I):
            continue
        hits = sum(1 for p in strong_budget if re.search(p, sentence, re.I))
        if not hits:
            continue
        if any(re.search(p, sentence, re.I) for p in ppie_only) and hits < 2:
            continue
        labelled = 8 if re.search(r"budget and finance|budget section|justification of costs", sentence, re.I) else 0
        candidates.append((hits * 3 + labelled, _short(sentence, 420)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], len(x[1])))
    return candidates[0][1]


def _add_evidence(evidence: list[dict[str, str]], field: str, quote: str, docs: list[LoadedDocument]) -> None:
    source = next((doc.name for doc in docs if quote and quote in doc.text), "application/supporting documents")
    evidence.append({"source_document": source, "section_or_context": field, "quote": _short(quote, 220), "why_it_matters": f"Supports {field.replace('_', ' ')}."})


def _is_valid_project_title(candidate: str) -> bool:
    """Return True only for explicit or clearly title-like project titles."""
    cleaned = _short(candidate or "", 180).strip(" \"'“”")
    words = cleaned.split()
    if not cleaned or cleaned == NOT_EXPLICITLY_STATED:
        return False
    if len(cleaned) > 140:
        return False
    if _is_noise(cleaned):
        return False
    if re.match(r"^(?:Month|WP\s*\d*|Work package|Milestone|Output|Appendix|Gantt)\b", cleaned, re.I):
        return False
    if re.search(r"governance confirmed|final analysis|commercial plan|\bcomplete\b|dissemination|work package|month start|month end", cleaned, re.I):
        return False
    if re.search(r"SYNTHETIC|TRAINING|DUMMY|FICTIONAL|EXEMPLAR|HIGH-SIMILARITY TEST", cleaned, re.I):
        return False
    if re.match(r"^(?:Summary|Background|Project management|Gantt(?:/workplan)?|Workplan|Endpoints?)$", cleaned, re.I):
        return False
    if re.match(r"^(?:This project will|The project will|This proposal|We will)\b", cleaned, re.I):
        return False
    if DANGLING_TERMINAL_WORDS_RE.search(cleaned):
        return False
    alpha_words = [w for w in words if re.search(r"[A-Za-z]", w)]
    if alpha_words and cleaned.upper() == cleaned:
        # Accept acronym-containing titles only if they include enough descriptive words; reject generic banners/labels.
        if len(alpha_words) <= 5 or re.search(r"(?:PROPOSAL|APPLICATION|SUMMARY|BACKGROUND|ENDPOINTS?|WORKPLAN|GANTT|PROJECT MANAGEMENT)$", cleaned, re.I):
            return False
    if len(words) < 2:
        return False
    return True


def _is_narrative_title_candidate(candidate: str) -> bool:
    return bool(
        re.match(
            r"(?i)^(this|the|our)\s+project\b|^we\s+will\b|^this\s+(?:application|proposal)\b|^to\s+(?:test|develop|evaluate)\b",
            candidate,
        )
    )


def _valid_labelled_project_title(candidate: str) -> bool:
    """Accept clear labelled titles while rejecting narrative descriptions."""
    cleaned = _short(candidate, 160).strip(" \"'“”")
    return bool(
        _is_valid_project_title(cleaned)
        and not _is_narrative_title_candidate(cleaned)
        and not re.search(r"(?i)funding call|lead applicant|partners? include|sample size|target population|study design|duration|abstract", cleaned)
    )


def _looks_like_project_title(candidate: str) -> bool:
    """Return True for generic title-like leading lines, not narrative sentences/headings."""
    cleaned = _short(candidate, 140).strip(" \"'“”")
    if not _is_valid_project_title(cleaned):
        return False
    words = cleaned.split()
    if not 3 <= len(words) <= 18:
        return False
    if cleaned.endswith(('.', '?', '!')):
        return False
    if _is_narrative_title_candidate(cleaned):
        return False
    if re.search(r"(?i)funding call|lead applicant|partners? include|sample size|target population|study design|duration|abstract|summary", cleaned):
        return False
    if re.search(r"\s[:–-]\s", cleaned):
        return True
    titlecase_words = sum(1 for word in words if re.match(r"[A-Z][A-Za-z0-9-]+$", word))
    has_acronym = any(re.match(r"[A-Z0-9-]{3,}$", word.strip("():")) and not _is_generic_acronym(word.strip("():")) for word in words)
    return has_acronym or titlecase_words >= max(2, len(words) // 2)


def _fallback_project_title(text: str) -> str | None:
    explicit = _find_first(text, FIELD_PATTERNS["project_title"])
    if explicit and _valid_labelled_project_title(explicit[0]):
        return explicit[0]
    for line in text.splitlines()[:20]:
        candidate = re.sub(r"^title\s*[:\-]\s*", "", _short(line, 140), flags=re.I).strip()
        if _looks_like_project_title(candidate):
            return candidate
    return None


def _extract_project_title(text: str) -> str | None:
    """Extract a project title from application text using explicit labels or title-like leading lines."""
    return _fallback_project_title(text)

def _extract_claimed_call(text: str) -> str | None:
    """Extract the funding call claimed in the application text."""
    return _fallback_claimed_call(text)


def _fallback_claimed_call(text: str) -> str | None:
    explicit = _find_first(text, FIELD_PATTERNS["application_claimed_call"])
    if explicit:
        return explicit[0]
    for pattern in [
        r"\b(NIHR\s+i4i\s+Product Development Award)\b",
        r"\b(i4i\s+Product Development Award)\b",
        r"\b(NIHR\s+i4i\s+PDA)\b",
        r"\b(PDA\s+application)\b",
    ]:
        match = re.search(pattern, text, re.I)
        if match:
            return _short(match.group(1), 120)
    return None


def _call_optional_extractor(name: str, fallback, text: str) -> str | None:
    extractor = globals().get(name)
    if callable(extractor):
        return extractor(text)
    return fallback(text)


def extract_application_facts(documents: Iterable[LoadedDocument]) -> ApplicationFacts:
    docs = list(documents)
    combined = _clean_text("\n".join(doc.text for doc in docs))
    facts = ApplicationFacts()
    evidence_entries: list[dict[str, str]] = []

    for field, patterns in FIELD_PATTERNS.items():
        found = _find_first(combined, patterns)
        if found:
            value, quote = found
            if field == "project_title" and not _valid_labelled_project_title(value):
                continue
            setattr(facts, field, value)
            _add_evidence(evidence_entries, field, quote, docs)

    project_title = _extract_project_title(combined)
    if project_title:
        facts.project_title = project_title
        _add_evidence(evidence_entries, "project_title", project_title, docs)
    claimed_call = _extract_claimed_call(combined)
    if claimed_call:
        facts.application_claimed_call = claimed_call
        _add_evidence(evidence_entries, "application_claimed_call", claimed_call, docs)

    explicit_product = facts.product_or_intervention if _valid_product_candidate(facts.product_or_intervention) else None
    product = _first_matching_product(combined)
    if explicit_product:
        facts.product_or_intervention = explicit_product
    elif product:
        facts.product_or_intervention = product
        _add_evidence(evidence_entries, "product_or_intervention", product, docs)
    elif not _valid_product_candidate(facts.product_or_intervention):
        facts.product_or_intervention = NOT_EXPLICITLY_STATED
    acronym = _first_acronym(combined, facts.product_or_intervention)
    if acronym:
        facts.acronym_or_short_name = acronym
        _add_evidence(evidence_entries, "acronym_or_short_name", acronym, docs)
    elif _is_generic_acronym(str(facts.acronym_or_short_name)):
        facts.acronym_or_short_name = NOT_EXPLICITLY_STATED

    if not _is_valid_project_title(facts.project_title):
        facts.project_title = NOT_EXPLICITLY_STATED

    current, target, trl_evidence, contradictions = _extract_trl(combined)
    facts.current_trl_or_stage = current
    facts.target_trl_or_stage = target
    facts.trl_evidence = trl_evidence
    facts.contradictions_or_uncertainties = contradictions

    facts.sample_size = _extract_sample_size(combined)
    facts.work_packages = _extract_gantt_rows(combined)
    facts.milestones = _extract_milestones(combined)
    facts.duration_months = _extract_duration(combined, facts.work_packages)
    facts.endpoints = _extract_endpoints(combined)

    refined_extractors = {
        "target_population": _extract_target_population,
        "clinical_or_social_care_need": _extract_clinical_need,
        "technology_type": _extract_technology_type,
        "study_design": _extract_study_design,
        "sites_or_setting": _extract_sites_or_setting,
        "regulatory_plan": lambda text: _extract_weighted_plan(text, REGULATORY_STRONG, REGULATORY_WEAK),
        "health_economics_plan": lambda text: _extract_weighted_plan(text, HEALTH_ECON_STRONG, HEALTH_ECON_WEAK),
        "research_inclusion_plan": _extract_research_inclusion,
        "market_or_impact_evidence": _extract_market_or_impact,
    }
    for field, extractor in refined_extractors.items():
        value = extractor(combined)
        if value:
            setattr(facts, field, value)
            _add_evidence(evidence_entries, field, value, docs)

    ppie_leadership = _extract_ppie_leadership(combined)
    if ppie_leadership:
        facts.ppie_leadership_evidence = ppie_leadership
        _add_evidence(evidence_entries, "ppie_leadership_evidence", ppie_leadership, docs)

    fallback_map = {
        "target_population": KEYWORDS["population"],
        "clinical_or_social_care_need": KEYWORDS["need"],
        "technology_type": KEYWORDS["technology"],
        "study_design": KEYWORDS["study_design"],
        "sites_or_setting": [r"NHS[^.\n]{0,120}(?:setting|service|team|clinic|rehabilitation)", r"(?:sites?|setting)[:\-]", r"community rehabilitation", r"primary care", r"secondary care", r"social care"],
        "regulatory_plan": KEYWORDS["regulatory"],
        "health_economics_plan": KEYWORDS["health_economics"],
        "ppie_plan": KEYWORDS["ppie"],
        "research_inclusion_plan": KEYWORDS["inclusion"],
        "market_or_impact_evidence": [r"market", r"adoption", r"commercial", r"\bIP\b", r"commissioning", r"knowledge mobilisation", r"dissemination", r"impact"],
        "next_stage_plan": [r"next stage", r"future work", r"next step", r"later-stage", r"definitive trial", r"scale-up", r"follow-on"],
    }
    for field, patterns in fallback_map.items():
        if getattr(facts, field) == NOT_EXPLICITLY_STATED:
            sentence = _sentence_with(combined, patterns)
            if sentence and not _is_noise(sentence) and not (field == "market_or_impact_evidence" and _is_disclaimer(sentence)):
                setattr(facts, field, sentence)
                _add_evidence(evidence_entries, field, sentence, docs)


    if facts.ppie_leadership_evidence == NOT_EXPLICITLY_STATED and re.search(r"named\s+PPIE?\s+lead", facts.ppie_plan, re.I):
        facts.ppie_leadership_evidence = _short(facts.ppie_plan, 300)
        _add_evidence(evidence_entries, "ppie_leadership_evidence", facts.ppie_leadership_evidence, docs)

    comparator = _sentence_with(combined, [r"usual care", r"standard care", r"control arm", r"comparator", r"current care"])
    if comparator:
        facts.comparator_or_control = comparator
        if facts.health_economics_plan == NOT_EXPLICITLY_STATED:
            facts.health_economics_plan = comparator

    if facts.project_management_plan == NOT_EXPLICITLY_STATED:
        pm_plan = _extract_project_management_plan(combined, facts.duration_months, facts.work_packages, facts.milestones)
        if pm_plan:
            facts.project_management_plan = pm_plan

    budget = _actual_budget_sentence(combined)
    if budget:
        facts.finance_or_budget_evidence = budget
        _add_evidence(evidence_entries, "finance_or_budget_evidence", budget, docs)
    else:
        facts.finance_or_budget_evidence = NOT_EXPLICITLY_STATED

    facts.partners = _sentences_with(combined, [r"partner", r"collaborator", r"co-applicant"], 8)
    facts.uploads_detected = _extract_uploads(combined)
    refs = _extract_references(combined)
    if refs:
        facts.references_detected = refs

    # Only explicit Yes/No or declaration wording counts for AI/conflicts.
    ai = _sentence_with(combined, [r"AI[- ]use declaration", r"generative AI\s*[:\-]\s*(yes|no)", r"artificial intelligence\s*[:\-]\s*(yes|no)"])
    if ai:
        facts.ai_use_declaration = ai
    conflicts = _sentence_with(combined, [r"conflicts?\s*[:\-]\s*(yes|no|none|declared)", r"competing interests?\s*[:\-]\s*(yes|no|none)"])
    if conflicts:
        facts.conflicts_declaration = conflicts

    # Add concise evidence for important inferred fields.
    for field in ["sample_size", "duration_months", "project_management_plan", "trl_evidence"]:
        value = getattr(facts, field)
        if value != NOT_EXPLICITLY_STATED:
            _add_evidence(evidence_entries, field, str(value), docs)

    facts.evidence = evidence_entries
    return facts
