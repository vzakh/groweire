"""The five explanation blocks per strategy (J2), built only from metrics and sources (D11).

Every risk and gap has a CODE. `present.py` turns codes into questions for the advisor, so a
code used here must exist in data/advisor_questions.json (checked at startup and in tests).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.rotations import Constraints, Evidence, Explanation
from services import plain
from services.rotation.catalog import Catalog
from services.rotation.generate import Candidate
from services.rotation.score import Env, Result, sensitivity

# Every code this module can emit.
CODES = (
    "shared_disease_sclerotinia",
    "shared_disease_clubroot",
    "take_all_pressure",
    "wild_oat_resistance",
    "rule_2_of_4",
    "wet_autumn_sowing",
    "wet_harvest",
    "dry_summer_risk",
    "market_access_new_crop",
    "new_equipment",
    "livestock_needed",
    "outside_pilot",
    "crop_sensitivity_unverified",
    "crop_parameter_missing",
    "climate_unavailable",
    "tillage_area_unknown",
    "equipment_not_asked",
    "livestock_not_asked",
    "no_soil_test",
    "local_fit",
)

CRITERION_WORDS = {
    "climate_risk": "lower weather risk for the crops",
    "income_stability": "income spread over more crops",
    "simplicity": "less work",
    "soil_cover": "less bare soil",
    "water_use": "less water needed",
    "forage_value": "more feed for animals",
    "nitrogen_fixing": "more nitrogen fixed by the crops",
    "pest_break": "more breaks in the disease cycle",
    "market_suitability": "crops that are easier to sell",
}
MIN_GAIN = 0.05
SAME_BAND = 0.05  # a change inside +-5% reads as "same" (brief §10.3)


@dataclass
class Explained:
    explanation: Explanation
    codes: list[str] = field(default_factory=list)  # risks first, then gaps


def better_criteria(scores: dict, current: dict, weight_by_criterion: dict) -> list[str]:
    """Criteria where this option beats the current rotation, most important first."""
    gains = {c: scores[c] - current[c] for c in scores if scores[c] - current[c] > MIN_GAIN}
    return sorted(gains, key=lambda c: (-(weight_by_criterion.get(c, 0) + 0.1) * gains[c], c))


def _names(crop_ids, catalog: Catalog) -> str:
    names = [catalog.crop(c).name.lower() for c in dict.fromkeys(crop_ids)]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def explain(
    cand: Candidate,
    result: Result,
    scores: dict[str, float],
    current: Candidate,
    current_result: Result,
    current_scores: dict[str, float],
    weight_by_criterion: dict[str, int],
    env: Env,
    catalog: Catalog,
    constraints: Constraints,
    pilot: bool,
) -> Explained:
    crops = [catalog.crop(c) for c in cand.sequence]
    n = len(crops)
    m, cm = result.metrics, current_result.metrics
    risks: list[tuple[str, str]] = []
    gaps: list[tuple[str, str]] = []
    evidence: list[Evidence] = []
    benefits: list[str] = []
    new_crops = [c for c in crops if c.id not in current.sequence]

    # ---- risks needing local review ----
    sclerotinia = [c.id for c in crops if "sclerotinia" in c.disease_groups]
    if len(set(sclerotinia)) >= 2:
        risks.append(
            (
                "shared_disease_sclerotinia",
                f"{_names(sclerotinia, catalog).capitalize()} share sclerotinia. "
                "Check how far apart they should be.",
            )
        )
    brassica_cover = any("clubroot" in catalog.crop(c).disease_groups for c in cand.cover.values())
    if brassica_cover and any("clubroot" in c.disease_groups for c in crops):
        risks.append(
            ("shared_disease_clubroot", "A brassica cover crop can carry clubroot to oilseed rape.")
        )
    pairs = [(crops[i], crops[(i + 1) % n]) for i in range(n)]
    if any("take_all" in a.disease_groups and "take_all" in b.disease_groups for a, b in pairs):
        risks.append(
            ("take_all_pressure", "Wheat or barley after wheat or barley can build up take-all.")
        )
        evidence.append(
            Evidence(
                claim="Continuous cereals accumulate take-all and grass-weed pressure",
                source="teagasc_rotation",
            )
        )
    if len(set(cand.sequence)) == 1 and crops[0].family == "cereal" and crops[0].season == "spring":
        risks.append(
            (
                "wild_oat_resistance",
                f"Herbicide-resistant wild oats risk in continuous {crops[0].name.lower()}.",
            )
        )
    if not m["rule_compliance"]["ie_crop_rotation_2_of_4"]:
        risks.append(
            (
                "rule_2_of_4",
                "One crop every year may not meet the crop rotation rule for arable land.",
            )
        )
        evidence.append(
            Evidence(
                claim="Irish conditionality asks for crop rotation on arable land",
                source="dafm_conditionality",
            )
        )
    wet = {
        mo
        for mo, (p, kind) in env.risk.items()
        if kind == "waterlogging" and plain.level(p) != "low"
    }
    if any(c.autumn_sown and (c.sow_month in wet or c.sow_month - 1 in wet) for c in crops):
        risks.append(
            ("wet_autumn_sowing", "Autumn sowing falls in a month that is often too wet here.")
        )
    if any(c.harvest_month in wet for c in crops if c.harvest_month):
        risks.append(("wet_harvest", "Harvest falls in a month that is often too wet here."))
    dry = [
        mo for mo, (p, kind) in env.risk.items() if kind == "drought" and plain.level(p) != "low"
    ]
    if any((sensitivity(c, mo, "drought") or 0) >= 0.5 for c in crops for mo in dry):
        risks.append(
            (
                "dry_summer_risk",
                "Some of these crops are in a sensitive stage in the dry-risk months.",
            )
        )
    if not cand.is_current and new_crops:
        risks.append(
            (
                "market_access_new_crop",
                f"Check there is a buyer for {_names([c.id for c in new_crops], catalog)} near you.",
            )
        )
        current_kit = {e for c in current.sequence for e in catalog.crop(c).equipment}
        if any(set(c.equipment) - current_kit for c in new_crops):
            risks.append(
                ("new_equipment", "A new crop may need different machinery or a contractor.")
            )
    if any(c.requires_livestock for c in crops) and constraints.has_livestock is not True:
        risks.append(
            ("livestock_needed", "This rotation grows forage. It needs animals or a buyer.")
        )
    if not pilot:
        risks.append(("outside_pilot", "The risk model is built for Ireland, not for this place."))
    risks.append(
        ("local_fit", "Local soil, weather and markets can change which rotation suits this field.")
    )

    # ---- information gaps ----
    gaps.append(
        (
            "crop_sensitivity_unverified",
            "How much each crop suffers in each month is a first estimate, not yet checked.",
        )
    )
    if result.missing_parameters:
        gaps.append(
            (
                "crop_parameter_missing",
                "No water-use figures for: " + ", ".join(result.missing_parameters).lower() + ".",
            )
        )
    if env.et0 is None:
        gaps.append(
            ("climate_unavailable", "Weather history was not available for this comparison.")
        )
    gaps.append(
        (
            "tillage_area_unknown",
            "We do not know your tillage area, so we did not check the two-crop rule.",
        )
    )
    if constraints.equipment is None:
        gaps.append(("equipment_not_asked", "We did not ask which machinery you have."))
    if constraints.has_livestock is None:
        gaps.append(("livestock_not_asked", "We did not ask if you keep animals."))
    gaps.append(
        ("no_soil_test", "No field-level soil test provided (soil values are map estimates).")
    )

    # ---- evidence ----
    if cand.template is not None:
        evidence.append(Evidence(claim=cand.template.rationale, source=cand.template.source))
    if any("take_all" in b.disease_groups and "take_all" in a.pest_break_for for a, b in pairs):
        evidence.append(
            Evidence(
                claim="Wheat and barley grown after a break crop avoid the take-all build-up "
                "seen in continuous cereals",
                source="teagasc_rotation",
            )
        )
    if m["n_fixing_years"]:
        evidence.append(
            Evidence(
                claim="Legumes such as beans and clover fix nitrogen from the air",
                source="teagasc_crops",
            )
        )
    if cand.cover:
        evidence.append(
            Evidence(
                claim="Cover crops keep the soil covered over winter and take up leftover nitrogen",
                source="teagasc_cover_crops",
            )
        )
    if m["water_demand_mm"] is not None:
        evidence.append(
            Evidence(
                claim="Crop water demand is estimated from FAO-56 crop coefficients and local "
                "reference evapotranspiration",
                source="fao56_table12",
            )
        )
    evidence.append(
        Evidence(
            claim=f"Bare soil for {m['bare_months_per_year']} months a year, from the crop calendars",
            source="bare_months_per_year",
        )
    )

    # ---- benefits + why ----
    if cand.is_current:
        why = "Baseline for comparison."
        benefits.append("Familiar operations")
        fits = sorted({k for c in crops for k in c.market} & set(env.market_contracts))
        if fits:
            benefits.append(f"Fits your {fits[0].replace('_', ' ')} contract")
    else:
        better = better_criteria(scores, current_scores, weight_by_criterion)
        words = [CRITERION_WORDS[c] for c in better[:2]]
        why = (
            "Suggested because it does better than your current rotation on: "
            + " and ".join(words)
            + "."
            if words
            else "Shown as another mix to compare with your current rotation."
        )
        if m["bare_months_per_year"] < cm["bare_months_per_year"]:
            benefits.append(
                f"Bare soil months drop from {cm['bare_months_per_year']} to "
                f"{m['bare_months_per_year']} a year"
            )
        if m["pest_break_score"] > cm["pest_break_score"]:
            count = round(m["pest_break_score"] * n)
            benefits.append(f"{count} of {n} crop changes break a disease cycle")
        if m["n_fixing_years"] > cm["n_fixing_years"]:
            benefits.append(f"A nitrogen-fixing crop in {m['n_fixing_years']} of {n} years")
        if m["crop_weighted_stress"] < cm["crop_weighted_stress"] * (1 - SAME_BAND):
            benefits.append("Lower weather stress on the crops in the risky months")
        if None not in (m["water_demand_mm"], cm["water_demand_mm"]) and (
            m["water_demand_mm"] < cm["water_demand_mm"] * (1 - SAME_BAND)
        ):
            benefits.append("Less water needed in the growing season")
        if m["forage_score"] > cm["forage_score"] and constraints.has_livestock:
            benefits.append("More feed for livestock")
        if (
            m["rule_compliance"]["ie_crop_rotation_2_of_4"]
            and not cm["rule_compliance"]["ie_crop_rotation_2_of_4"]
        ):
            benefits.append("Meets the crop rotation rule for arable land")
        if not benefits:
            benefits.append("Another option to weigh against your current rotation")

    return Explained(
        explanation=Explanation(
            why_suggested=why,
            evidence=evidence,
            benefits=benefits,
            information_gaps=[text for _, text in gaps],
            risks_needing_local_review=[text for _, text in risks],
        ),
        codes=[code for code, _ in risks] + [code for code, _ in gaps],
    )
