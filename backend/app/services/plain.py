"""Plain-language wording for risk, written and tested in ONE place (brief §10.5, D19).

Pure functions, no I/O beyond reading config/plain.yaml once. The frontend shows these strings
as they are and never re-derives them.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from functools import lru_cache

import yaml

from core.config import APP_DIR


@lru_cache
def config() -> dict:
    return yaml.safe_load((APP_DIR / "config" / "plain.yaml").read_text(encoding="utf-8"))


def frequency_text(p: float) -> str:
    """Natural frequency of a risk: out of 10 years, or out of 20 below 10%."""
    f = config()["frequency"]
    if p < f["rare_below"]:
        return "less than 1 year in 20"
    if p < f["per_20_below"]:
        return "about 1 year in 20"
    if p >= f["almost_every_from"]:
        return "almost every year"
    n = math.floor(10 * p + 0.5)  # round half up, on purpose (not banker's rounding)
    return f"about {n} year{'' if n == 1 else 's'} in 10"


def level(p: float) -> str:
    levels = config()["levels"]
    if p < levels["medium_from"]:
        return "low"
    return "medium" if p < levels["high_from"] else "high"


def dominant_type(stress_types: Iterable[str]) -> str:
    """The one type that names a month; `other` when nothing specific is known."""
    present = set(stress_types)
    return next((t for t in config()["type_priority"] if t in present), "other")


def label(risk_level: str, stress_types: Iterable[str]) -> str:
    """OK | Dry | Wet | Heat | Frost | Unclear."""
    labels = config()["labels"]
    return labels["ok"] if risk_level == "low" else labels[dominant_type(stress_types)]


def month_name(month: int) -> str:
    return config()["months"][month - 1]


def crop_words(crop_name: str | None) -> str:
    return crop_name.lower() if crop_name else config()["default_crop_words"]


def riskiest_month(months: Sequence[dict]) -> int | None:
    """Month with the highest displayed risk; ties go to the earlier month."""
    if not months:
        return None
    return max(months, key=lambda m: (m["risk"], -m["month"]))["month"]


def headline(months: Sequence[dict], crop_name: str | None) -> str:
    """One sentence for the answer screen. `months`: [{month, risk, stress_types, frequency?}].

    `risk` (crop-weighted when a crop is chosen) picks the month; the words "N years in 10"
    describe `frequency`, the counted weather, so the sentence can be checked against memory.
    """
    crop = crop_words(crop_name)
    top_month = riskiest_month(months)
    top = next((m for m in months if m["month"] == top_month), None)
    if top is None or level(top["risk"]) == "low":
        return f"No month stands out as risky for {crop} here."
    start = f"{month_name(top['month'])} is the riskiest month for {crop} here."
    often = frequency_text(top.get("frequency", top["risk"]))
    kind = dominant_type(top["stress_types"])
    if kind == "other":
        return f"{start} In {often} crops here do worse than normal, cause unclear."
    return f"{start} In {often} it is too {config()['too_words'][kind]}."


def join_years(years: Sequence[int]) -> str:
    """[2018, 2006, 2022] -> "2018, 2006 and 2022"."""
    words = [str(y) for y in years]
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def evidence_text(month: int, kind: str, hit: int, total: int, years: Sequence[int]) -> str:
    """The counted fact behind a month: a sentence the farmer can check against memory."""
    cfg = config()
    start = f"{month_name(month)} {cfg['was_words'][kind]} here in {hit} of the last {total} years"
    shown = list(years)[: cfg["evidence_years"]]
    if not shown:
        return f"{start}."
    if hit <= len(shown):
        return f"{start}: {join_years(shown)}."
    return f"{start}, for example {join_years(shown)}."


def soil_facts(soil) -> list[tuple[str, str]]:
    """(label, text) pairs for the "Your soil" card: what the maps say, with no judgement."""
    facts = []
    words = config()["drainage_words"].get(soil.drainage_class)
    if words:
        facts.append(("Drainage", words))
    if soil.clay is not None and soil.sand is not None:
        facts.append(
            ("Soil mix", f"About {soil.clay:.0f} parts clay and {soil.sand:.0f} parts sand in 100")
        )
    if soil.phh2o is not None:
        facts.append(("Acidity", f"pH about {soil.phh2o:.1f} (7 is neutral, lower is more acid)"))
    if soil.slope_deg is not None:
        facts.append(("Slope", f"About {soil.slope_deg:.0f} degrees"))
    return facts


def greenness_text(lowest_years: Sequence[int]) -> str:
    """Caption of the summer greenness chart."""
    start = "How green the land around your field was each summer, seen by NASA satellites."
    if not lowest_years:
        return start
    word = "summer was" if len(lowest_years) == 1 else "summers were"
    return f"{start} The least green {word} {join_years(lowest_years)}."


def aria_label(
    month: int,
    crop_name: str | None,
    month_label: str,
    often: str,
    interval: tuple[float, float],
    kind: str | None = None,
) -> str:
    """Screen-reader text for one month tile. The only place a percentage is spoken.

    `kind` is the counted stress type of the month and `often` how often it was counted;
    None means no risky weather was counted in any year.
    """
    cfg = config()
    ok = cfg["labels"]["ok"]
    word = month_label if month_label == ok else month_label.lower()
    start = f"{month_name(month)}, {crop_words(crop_name)}: {word}."
    if kind not in cfg["too_words"]:
        return f"{start} No risky weather was counted here."
    low, high = (round(100 * x) for x in interval)
    return (
        f"{start} In {often} it is too {cfg['too_words'][kind]} here. "
        f"Uncertainty {low} to {high} percent."
    )


def driver_text_ok(text: str, feature_names: Iterable[str] = ()) -> bool:
    """False if a driver text from ML leaks a technical term or a raw feature name."""
    if not text or not text.strip():
        return False
    lowered = text.lower()
    if any(term.lower() in lowered for term in config()["banned_terms"]):
        return False
    return not any(name.lower() in lowered for name in feature_names if "_" in name)
