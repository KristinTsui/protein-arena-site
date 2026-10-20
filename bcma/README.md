# BCMA Arena dashboard

Published at https://kristintsui.github.io/protein-arena-site/bcma/.

The current paired snapshot has 23 approved contestants, B5/L10 controls, and five BCMA antigen states. It contains 125 Fast and 52 Boltz pair scores and their exact original CIF structures. The 302-design selection-stage archive is retained separately in data.json and evidence.json. Physics results are pending scientific scalar review.

## Reproduce provisional pair ranks

```sh
python3 -B source/paired_ranking.py paired.json
python3 -B -m unittest discover -s source -p 'test_*.py'
```

The paired file retains raw metrics, original-coordinate hashes, chain roles, target residue maps, scoring collection hashes, and the frozen roster hash. The viewer verifies each structure SHA-256 before parsing it. Coordinate assets were also checked against both input sequence hashes and expected chains. Structure downloads are exact source CIF bytes.

Blue overall score is half mean confidence plus half minimum confidence across all five states; all five are required. Red uses the explicitly provisional confidence-loss rule documented in paired.json and on the site. Neither score establishes binding or escape. Separate engine rankings never average Fast and Boltz. Controls do not enter contestant ranks; P33S is an unranked reference and its observed signals are retained.

Confidence now uses maximum directional ipSAE in both the paired results and WT inventory. Combined weights and the joint confidence-plus-physics escape criterion remain unchanged. Do not fill missing physics values, substitute WT for variants, average engines, or attribute Boltz-derived physics to Fast. New releases must refresh reviewed score collections and exact matching structures and rerun the checks. A complete WT cohort is required before freezing a Red panel. Recompute every rank for the entire snapshot after adding cells.

## Selection-stage archive

```sh
python3 -B source/build_data.py --input evidence.json --output data.json
```

This command rebuilds only the original 302-design archive, not the paired evaluation. GitHub Pages is static; it does not poll CoreHPC. Historical root pages are preserved.

Viewer: 3Dmol.js 2.5.5, distributed with its licenses in vendor/.

## Whole-chain surfaces and mutation sites

The viewer displays the entire saved binder plus the full modeled BCMA extracellular domain, native residues 1–54 (53 residues for deletions). No full-length receptor reference has been added. Independent whole-chain van der Waals surfaces have adjustable opacity; ribbons and side chains remain optional. Gold patches/sticks and labels identify substitutions, or the surviving native flanks of a deletion. The deleted residue is never represented by invented atoms. All native-to-coordinate mappings are checked against the selected structure. Show whole complex restores the full view after focusing a mutation.

The surface features do not change original CIF bytes or raw ranking inputs.

## Confidence and predicted retention (policy v2)

Pair C = 50 × (native ipTM + max(ipSAE binder→target, ipSAE target→binder)). The overall confidence score remains half mean plus half worst C across five states. This replaces the former minimum-direction confidence everywhere; the approved 23-contestant roster stays fixed. The Red eligibility panel (WT C ≥ 50) is recomputed consistently; its three-raw-metric decline rule is unchanged.

The Blue switch independently ranks predicted retention: the number of five states meeting BOTH native ipTM and maximum-direction ipSAE cutoffs. Fast uses 0.60 / 0.40; Boltz uses 0.80 / 0.69. Five states include WT and the P33S control. All five evaluations are required for an overall rank. Incomplete counts show unknowns, never implied failures. Equal counts share ranks without a confidence tiebreaker. A per-antigen view uses only that state's confidence or screen outcome. The inventory is a separate WT-only archive.

Cutoffs are frozen at floor(100 × 0.90 × lower B5/L10 WT value) / 100 for each metric within each engine. Frozen anchors and thresholds are in source/paired_ranking.py and paired.json. This is a provisional reference-relative confidence screen. The 90% allowance and rounding are policy choices, not a learned or validated biological cutoff; no labeled nonbinder set is available here to estimate specificity. Counts across engines are not directly calibrated. Passing does not establish binding; failing does not establish nonbinding or a Red escape.

Sensitivity columns show counts at 85% and 95% of the same frozen WT anchors. Fast thresholds are 0.57/0.37 and 0.63/0.42; Boltz thresholds are 0.76/0.65 and 0.85/0.73. Counts are not confidence intervals. Among complete contestants, all-five counts at 85% / 90% / 95% are Fast 9 / 8 / 7 (23 complete), Boltz 3 / 3 / 2 (8 complete). Cutoffs are not refitted as more pairs arrive; changing them requires an explicit policy revision.
