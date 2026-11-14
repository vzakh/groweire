"""Farmer-facing wording for a strategy: headline, one-line why, vs current, advisor questions.

PRD DD-8 / DD-9. No percentages and no jargon here; numbers stay under "More detail".
"""

from __future__ import annotations

from models.rotations import SameCropNote, VsCurrent
from services.rotation.catalog import Catalog
from services.rotation.explain import better_criteria
from services.rotation.generate import Candidate
from services.rotation.score import Result

SAME_BAND = 0.05  # +-5% reads as "same" (brief §10.3)
MIN_QUESTIONS, MAX_QUESTIONS = 2, 4
WHY_PHRASES = {
    "pest_break": "Breaks the disease cycle",
    "nitrogen_fixing": "Adds nitrogen",
    "soil_cover": "Less bare soil",
    "climate_risk": "Lower weather risk",
    "water_use": "Uses less water",
    "simplicity": "Less work",
    "forage_value": "More feed for your animals",
    "market_suitability": "Easier to sell",
    "income_stability": "Spreads your income over more crops",
}


def _list(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _short(crop_id: str, catalog: Catalog) -> str:
    return catalog.crop(crop_id).name.lower().replace("spring field beans", "beans")


def headline(cand: Candidate, current: Candidate, catalog: Catalog) -> str:
    distinct = list(dict.fromkeys(cand.sequence))
    if cand.is_current:
        if len(distinct) == 1:
            return f"Your rotation: {_short(distinct[0], catalog)} every year"
        return f"Your rotation: {_list([_short(c, catalog) for c in distinct])}"
    new = [c for c in distinct if c not in current.sequence]
    if not new:
        if cand.cover and not current.cover:
            return "Keep your crops and add a winter cover crop"
        return "Change the order of your crops"
    if len(new) == 1 and cand.sequence.count(new[0]) == 1:
        year = cand.sequence.index(new[0]) + 1
        return f"Add {_short(new[0], catalog)} in year {year}"
    return f"Bring in {_list([_short(c, catalog) for c in new[:3]])}"


def same_crop_note(current: Candidate, catalog: Catalog) -> SameCropNote | None:
    """A plain note when one arable crop is grown every year. No numbers (hard rule 1).

    The yield claim is made only for cereals, where the catalogue's Teagasc source covers it;
    for other crops the note states the build-up risk and points to the advisor.
    """
    distinct = list(dict.fromkeys(current.sequence))
    if len(distinct) != 1 or len(current.sequence) < 2:
        return None
    crop = catalog.crop(distinct[0])
    if crop.family == "ley":  # grass every year is normal farming, not a rotation problem
        return None
    name = _short(crop.id, catalog)
    if crop.family == "cereal":
        return SameCropNote(
            text=f"You grow {name} every year. With one cereal year after year, its diseases "
            "and weeds build up in the soil, and yields often fall. A different crop in "
            "between can break that cycle.",
            source="teagasc_rotation",
        )
    return SameCropNote(
        text=f"You grow {name} every year. With one crop year after year, its diseases, pests "
        "and weeds can build up in the soil. Ask your advisor if that could be holding "
        "your yields back.",
        source=None,
    )


def one_line_why(
    scores: dict, current_scores: dict, weight_by_criterion: dict, is_current: bool
) -> str:
    if is_current:
        return "This is what you grow now. We compare the others against it."
    better = better_criteria(scores, current_scores, weight_by_criterion)
    if not better:
        return "A different mix to compare with what you grow now."
    return ". ".join(WHY_PHRASES[c] for c in better[:2]) + "."


def _compare(value: float, base: float, words: tuple[str, str, str]) -> str:
    """words = (lower, same, higher)."""
    if abs(value - base) <= SAME_BAND * max(abs(base), 1e-9):
        return words[1]
    return words[0] if value < base else words[2]


def vs_current(result: Result, current: Result) -> VsCurrent:
    p, c = result.parts, current.parts
    return VsCurrent(
        risk=_compare(p["stress"], c["stress"], ("lower", "same", "higher")),
        bare_soil=_compare(-p["bare"], -c["bare"], ("less", "same", "more")),
        workload=_compare(p["complexity"], c["complexity"], ("less", "same", "more")),
    )


def advisor_questions(codes: list[str], catalog: Catalog) -> list[str]:
    """2-4 questions, highest impact first (the order of data/advisor_questions.json)."""
    order = list(catalog.advisor_questions)
    missing = [c for c in codes if c not in catalog.advisor_questions]
    if missing:
        raise KeyError(f"no advisor question for codes {missing}")
    ranked = sorted(dict.fromkeys(codes), key=order.index)
    questions = list(dict.fromkeys(catalog.advisor_questions[c] for c in ranked))
    picked = questions[:MAX_QUESTIONS]
    # Keep the soil-test question in view even when many specific risks fire.
    soil_test = catalog.advisor_questions.get("no_soil_test")
    if soil_test in questions and soil_test not in picked:
        picked[-1] = soil_test
    if len(picked) < MIN_QUESTIONS:
        raise ValueError("every strategy needs at least 2 advisor questions")
    return picked
