"""BCMA Arena descriptive ranking policy, version 2026-10-20.

Scores are utilities for comparing computational evidence, not probabilities
of binding or measured affinities. Raw scores must share one declared protocol.
"""
from math import isfinite
from decimal import Decimal

POLICY_VERSION = "bcma-arena-2026-10-20-v2-max"


def finite(value):
    return type(value) in (int, float) and isfinite(value)


def confidence(iptm, ipsae_max):
    """Equal weights; a missing component is never replaced or reweighted."""
    if iptm is None or ipsae_max is None:
        return None
    if not all(finite(x) and 0 <= x <= 1 for x in (iptm, ipsae_max)):
        raise ValueError("Confidence components must be finite values in [0, 1]")
    return 100 * (iptm + ipsae_max) / 2


def physics_percentile(energy, frozen_wt_energies):
    """Midpoint empirical CDF; lower energy is better; one fixed WT reference.

    The reference must be explicitly frozen outside this function, complete for
    every required WT member, and exclude reference controls. It must contain
    at least two distinct binders. Equal energies receive the same percentile.
    """
    if energy is None or frozen_wt_energies is None:
        return None
    if not finite(energy):
        raise ValueError("Energy must be finite")
    if not all(finite(x) for x in frozen_wt_energies):
        raise ValueError("Incomplete or invalid frozen WT reference")
    if len(frozen_wt_energies) < 2 or len(set(frozen_wt_energies)) < 2:
        return None
    worse = sum(x > energy for x in frozen_wt_energies)
    equal = sum(x == energy for x in frozen_wt_energies)
    return 100 * (worse + equal / 2) / len(frozen_wt_energies)


def combined(model_score, physics_score):
    if model_score is None or physics_score is None:
        return None
    if not all(finite(x) and 0 <= x <= 100 for x in (model_score, physics_score)):
        raise ValueError("Component scores must lie in [0, 100]")
    return (model_score + physics_score) / 2


def competition_ranks(rows, score_key):
    """Descending shared ranks 1,1,3; IDs only order tied rows for display."""
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate binder IDs")
    eligible = []
    for row in rows:
        score = row.get(score_key)
        if score is not None:
            if not finite(score):
                raise ValueError("Invalid rank score")
            eligible.append(row)
    eligible.sort(key=lambda row: (-round(row[score_key], 6), row["id"]))
    ranks = {}
    last, rank = None, None
    for position, row in enumerate(eligible, 1):
        value = round(row[score_key], 6)
        if last is None or value != last:
            rank = position
        ranks[row["id"]] = rank
        last = value
    return ranks


def modeled_escape(wt, variant):
    """Declared, UNCALIBRATED joint-decline heuristic; never a biological call.

    False means the declared computational criterion was not met, not that
    biological escape is disproven. None means unevaluable. Constants below
    are ranking policy choices, not literature-derived discrimination cutoffs.
    """
    if not wt or not variant or wt.get("binding_supported") is not True:
        return None
    if wt.get("target_integrity_passed") is not True or variant.get("target_integrity_passed") is not True:
        return None
    if not wt.get("protocol_id") or wt.get("protocol_id") != variant.get("protocol_id"):
        return None
    if not wt.get("binder_id") or wt.get("binder_id") != variant.get("binder_id"):
        return None
    if wt.get("score_valid") is not True or variant.get("score_valid") is not True:
        return None
    if not wt.get("physics_reference_sha256") or wt.get("physics_reference_sha256") != variant.get("physics_reference_sha256"):
        return None
    keys = ("iptm", "ipsae_binder_to_target", "ipsae_target_to_binder")
    if not all(finite(item.get(k)) and 0 <= item[k] <= 1 for item in (wt, variant) for k in keys):
        return None
    e0, ev, p0, pv = (wt.get("interface_dg_reu"), variant.get("interface_dg_reu"),
                      wt.get("physics_score"), variant.get("physics_score"))
    if not all(finite(x) for x in (e0, ev, p0, pv)) or not (0 <= p0 <= 100 and 0 <= pv <= 100):
        return None
    dec = lambda value: Decimal(str(value))
    declines = all(dec(wt[k]) - dec(variant[k]) >= max(Decimal(".10"), Decimal(".25") * dec(wt[k])) for k in keys)
    return declines and ev > e0 and dec(p0) - dec(pv) >= 25


def escape_rate(calls, panel_size):
    """Rank only complete evidence on the same frozen WT-competent panel."""
    if type(panel_size) is not int or panel_size <= 0:
        return {"score": None, "escape_count": None, "evaluable_count": 0}
    if len(calls) != panel_size or any(x is not None and type(x) is not bool for x in calls):
        raise ValueError("Calls must preserve every fixed-panel member")
    evaluable = sum(x is not None for x in calls)
    successes = sum(x is True for x in calls)
    return {
        "score": 100 * successes / panel_size if evaluable == panel_size else None,
        "escape_count": successes if evaluable else None,
        "evaluable_count": evaluable,
    }
