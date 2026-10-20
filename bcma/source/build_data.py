"""Build the public BCMA dashboard snapshot from the verified scalar export."""
import argparse
import hashlib
import json
from pathlib import Path
from ranking import POLICY_VERSION, confidence, competition_ranks


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source, output):
    raw = json.loads(source.read_text())
    assert raw["campaign_id"] == "bcma_restart_20261017"
    assert len(raw["binders"]) == len({r["id"] for r in raw["binders"]}) == 302
    assert sum(r["fast"] is not None for r in raw["binders"]) == 108
    assert sum(r["af2"] is not None for r in raw["binders"]) == 14
    assert {x["id"] for x in raw["targets"]} == {"WT", "R27P", "S30del", "P34del", "P33S"}
    rows = []
    for original in raw["binders"]:
        screen = original["fast"]
        model = None
        fast = None
        if screen is not None:
            assert screen["ranking_eligible"] is True and screen["status"] == "scored"
            assert screen["protocol_id"] == "esmfold2-fast-wt54-seed17" and screen["target_id"] == "WT"
            metrics = screen["metrics"]
            assert metrics["ipsae_min"] == min(metrics["ipsae_binder_to_target"], metrics["ipsae_target_to_binder"])
            model = confidence(metrics["iptm"], metrics["ipsae_min"])
            fast = dict(metrics, geometry=screen["geometry"], source_ids=screen["source_ids"],
                        protocol_id=screen["protocol_id"])
        if original["af2"]:
            assert original["af2"]["ranking_eligible"] is False
        rows.append(dict(
            id=original["id"], label=original["id"], team=original["team"],
            parent=original.get("assigned_parent_id") or ", ".join(original["parent_ids"]),
            parent_ids=original["parent_ids"], length=original["length"],
            native_status=original["native_status"], native_labels=original["native_labels"],
            native_accepted=original["native_accepted"], sequence_sha256=original["sequence_sha256"],
            fast=fast, af2=original["af2"], model_score=model,
            physics_score=None, interface_dg_reu=None, combined_score=None,
            provisional_rank=None, combined_rank=None,
            status="Fast scored" if screen else "Not common-scored",
            score_regime="ESMFold2-Fast / WT54 / seed 17" if screen else None,
            final_status="Awaiting held-out prediction and physics",
            final_nominee=False, provenance=original["provenance"],
        ))
    ranks = competition_ranks(rows, "model_score")
    for row in rows:
        row["provisional_rank"] = ranks.get(row["id"])
    rows.sort(key=lambda r: (r["provisional_rank"] is None, r["provisional_rank"] or 0, r["id"]))
    antigens = []
    for target in raw["targets"]:
        tid = target["id"]
        antigens.append(dict(
            id=tid, label=target["name"], mutation="Wild type" if tid == "WT" else tid,
            role="baseline" if tid == "WT" else "control" if tid == "P33S" else "challenge",
            native_edit=target["native_edit"], length=target["construct_length"],
            escape_score=None, escape_rank=None, escape_count=None, evaluable_count=0, panel_size=None,
            status="Baseline" if tid == "WT" else "Awaiting paired evaluation",
            interpretation="Reference state" if tid == "WT" else
                "Variant control; behavior against these new binders remains unknown" if tid == "P33S" else
                "Clinical reagent-specific challenge; no escape from these new binders established",
            sequence_sha256=target["sequence_sha256"],
        ))
    methods = {
        "version": POLICY_VERSION,
        "confidence_formula": "C = 100 × [0.5 × native ipTM + 0.5 × min(ipSAE binder→target, ipSAE target→binder)]",
        "physics_formula": "P(E) = 100 × [number of frozen WT energies > E + 0.5 × number equal to E] / N",
        "combined_formula": "Blue score = 0.5 × C + 0.5 × P",
        "red_formula": "Red score = 100 × modeled escapes / N eligible WT-supported binders, with complete coverage of the same frozen panel",
        "current_rank": "The 108 scored binders use the provisional Fast confidence score C only. This is not the final combined rank. The other 194 inventory members remain unranked.",
        "final_rank": "Final ranks are per antigen, using the common held-out Boltz prediction and one reviewed beta_nov16 physics replicate. Fast screening and confounded AF2 diagnostics are not substituted for that final protocol.",
        "physics_reference": "Lower interface_dG_REU is better. Freeze the complete WT nominee reference cohort, excluding published controls, before inspecting energies. Use that same reference for every variant. At least two distinct energies are required; do not drop failed members to create a favorable subset.",
        "escape_rule": "Modeled escapes use an explicitly uncalibrated joint-decline rule. Each of native ipTM and both directional ipSAE values must fall by at least max(0.10, 25% of its WT value). Variant interface energy must be less favorable than WT, and its fixed-reference physics percentile must fall by at least 25 points.",
        "escape_eligibility": "Require reviewed model-supported WT binding, reviewed WT and mutant target integrity, accepted structures and chemistry, matched binder identity and evaluator settings, and complete confidence/physics evidence. A failed or missing computation is unknown. The rule not being met does not prove retained biological binding.",
        "escape_controls": "WT is a baseline and P33S is a variant control, displayed outside the competitive Red ranks. A future P33S modeled-escape count is not forced to zero. R27P, S30del and P34del are clinical reagent-specific challenges; the clinical evidence does not establish escape from these new binders.",
        "uncalibrated_policy": "The equal weights and Red thresholds are declared policy choices, not experimentally calibrated discrimination thresholds. No escape calls are currently available. Single predictions/replicates cannot establish stochastic robustness.",
        "missing_and_ties": "A missing, failed, confounded or unreviewed required component leaves the score unavailable. No zero filling or weight redistribution. Rank scores rounded to six decimals with shared competition ranks (1, 2, 2, 4); stable IDs order ties without breaking them. Display scores to two decimals.",
        "limitations": "Scores are computational utilities, not binding probabilities or measured affinities. Confidence components are correlated. Rosetta energies are protocol- and interface-size-dependent; percentiles depend on the frozen cohort. Family-related binders are not independent replicates. Ranking is not final nomination or proof of design-method superiority.",
        "af2_diagnostics": "All 14 candidate AF2 predictions are excluded from active ranking because of a shared target-conformation issue reproduced by B5/L10 controls. This does not demonstrate biological nonbinding. Native scalar pLDDT is unavailable and is not inferred.",
        "minimum_ipsae": "The campaign uses the conservative minimum of two directional ipSAE fields. Canonical ipSAE reports the maximum; canonical published cutoffs are not applied to this custom minimum.",
        "reproducibility": "Download the public snapshot and scalar evidence. Source hashes, cohort identities and ranking source are retained; no new predictions or molecular rescoring were performed for this site.",
    }
    methods["sections"] = [
        dict(title="01 / Provisional confidence", formula=methods["confidence_formula"],
             description=methods["current_rank"], notes=[methods["minimum_ipsae"]]),
        dict(title="02 / Combined Blue ranking", formula=methods["combined_formula"],
             description=methods["final_rank"], notes=[methods["physics_formula"], methods["physics_reference"]]),
        dict(title="03 / Modeled escapes", formula=methods["red_formula"],
             description=methods["escape_rule"], notes=[methods["escape_eligibility"], methods["uncalibrated_policy"]]),
        dict(title="04 / References and missing evidence", description=methods["escape_controls"],
             notes=[methods["missing_and_ties"], methods["af2_diagnostics"]]),
        dict(title="05 / Interpretation", description=methods["limitations"],
             notes=["The score is an explicitly chosen ranking utility; no experimental binding or escape success is inferred."]),
        dict(title="06 / Reproducible snapshot", description=methods["reproducibility"],
             notes=["Current scope: BCMA restart only. All generated designs remain listed, including native generator rejections. Published controls do not receive competitive ranks.",
                    "Threshold comparisons use decimal representations of stored values to preserve exact policy boundaries."]),
    ]
    sources = [
        {"title": "Original ipSAE implementation", "url": "https://github.com/DunbrackLab/IPSAE"},
        {"title": "Rosetta InterfaceAnalyzer definitions", "url": "https://docs.rosettacommons.org/docs/latest/application_documentation/analysis/interface-analyzer"},
        {"title": "Rosetta energy units", "url": "https://docs.rosettacommons.org/docs/latest/rosetta_basics/Units-in-Rosetta"},
        {"title": "Primary BCMA escape study", "url": "https://www.nature.com/articles/s41591-023-02491-5"},
    ]
    methods_sha = hashlib.sha256(json.dumps(methods, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    document = {
        "schema": "protein-arena.bcma.website.v1",
        "campaign": dict(raw["campaign"], id=raw["campaign_id"], updated=raw["snapshot_date"],
                         stage="Common WT screening",
                         description="302 generated designs. Three design arms. Five BCMA states. Explore the evidence from first screening to confidence, physics, and modeled escape."),
        "coverage": dict(generated=302, fast_scored=108, unscored=194, physics_scored=0,
                         combined_scored=0, variants_evaluated=0, target_states=5,
                         af2_diagnostics=14, controls=2, final_nominees=0),
        "teams": raw["campaign"]["counts"]["by_team"],
        "binders": rows, "antigens": antigens, "controls": raw["controls"],
        "methods": methods, "sources": sources,
        "ranking_policy": {
            "version": POLICY_VERSION, "sha256": methods_sha,
            "confidence_weights": {"native_iptm": .5, "minimum_directional_ipsae": .5},
            "combined_weights": {"confidence": .5, "physics": .5},
            "red_rule": "red_joint_decline_heuristic_v1",
            "red_calibrated": False,
            "red_thresholds": {"absolute_confidence_decline": .1, "relative_confidence_decline": .25,
                               "physics_percentile_point_decline": 25, "energy_must_worsen": True},
            "frozen_wt_reference": None, "frozen_wt_competent_panel": None,
            "calibrated_escape_counts": None,
        },
        "protocols": raw["protocols"], "provenance": raw["provenance"],
        "build": {"input_sha256": sha(source), "ranking_source_sha256": sha(Path(__file__).with_name("ranking.py")),
                  "input_sources_verified": len(raw["provenance"]), "new_molecular_calculations": 0},
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return {"binders": len(rows), "ranked": len(ranks), "antigens": len(antigens), "data_sha256": sha(output)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.input, args.output)))
