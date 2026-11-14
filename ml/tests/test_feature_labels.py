"""Every feature has farmer-word text with no technical terms (PRD DD-13)."""

from __future__ import annotations

import pytest

from agrolens_ml import FEATURE_NAMES
from agrolens_ml.features import feature_labels as fl


@pytest.mark.parametrize("feature", FEATURE_NAMES)
@pytest.mark.parametrize("value, contrib", [(-1.5, 0.1), (1.5, -0.1), (None, None), (0.0, 0.0)])
def test_text_for_every_feature(feature, value, contrib):
    t = fl.text(feature, value, contrib)
    assert t.strip()
    assert not any(term in t for term in fl.BANNED_TERMS), t


def test_every_feature_is_covered():
    covered = set(fl.ANOMALY_TEXTS) | set(fl.SUBJECTS)
    assert set(FEATURE_NAMES) <= covered, set(FEATURE_NAMES) - covered


def test_sign_semantics():
    assert "drier" in fl.text("p_minus_et0_3m_l1_z", -1.8)
    assert "wetter" in fl.text("p_minus_et0_3m_l1_z", 1.2)
    assert "more likely" in fl.text("precip_l1", 40.0, 0.05)
    assert "less likely" in fl.text("precip_l1", 40.0, -0.05)
