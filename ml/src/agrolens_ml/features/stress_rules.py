"""Rule-based stress-type attribution (brief §8.2, D4).

Task-05 SHELL: always ["other"]. Task 12 implements the rules with the thresholds in config.py.
"""

from __future__ import annotations


def attribute_stress(row: dict) -> list[str]:
    """Stress types (subset of STRESS_TYPES) suggested by the drivers in a feature row."""
    del row  # used from task 12
    return ["other"]
