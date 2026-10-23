# BCMA Arena dashboard

Published at https://kristintsui.github.io/protein-arena-site/bcma/.

The current paired snapshot has 23 approved contestants, B5/L10 controls, and five BCMA antigen states. It contains 125 Fast and 125 Boltz pair scores and their exact original CIF structures. The 302-design selection-stage archive is retained separately in data.json and evidence.json. Physics dispositions are reviewed: 123 accepted and two failed-null results.

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

Sensitivity columns show counts at 85% and 95% of the same frozen WT anchors. Fast thresholds are 0.57/0.37 and 0.63/0.42; Boltz thresholds are 0.76/0.65 and 0.85/0.73. Counts are not confidence intervals. Among complete contestants, all-five counts at 85% / 90% / 95% are Fast 9 / 8 / 7 (23 complete), Boltz counts are recalculated on all 23 complete contestants in the final snapshot. Cutoffs are not refitted as more pairs arrive; changing them requires an explicit policy revision.

## Final reviewed bundle (2026-10-21)

The current dataset has all 250 engine-pair rows, 250 original CIF assets, and 123 accepted Boltz-derived relaxed PDB assets. The exact approved roster remains 23 contestants plus B5/L10 reference controls. The two physics failures are BC-202d0f7e9723 WT and R27P; all their physics values and relaxed structures remain null.

Public final/RESULTS.json and final/STRUCTURES.json are publication derivatives of the independently reviewed bundle. The reviewed relaxed PDBs included private absolute paths on the BEGIN/END_POSE_ENERGIES_TABLE comment markers. Publication removes only those paths. Every other byte, including atom, disulfide and energy records, is preserved. The manifest records reviewed-source and sanitized-public hashes for all 123 affected files. Original CIFs and all raw scalar values are unchanged. No private review documents are published.

Confidence always belongs to the selected engine's original prediction, including while its relaxed display is selected. The relaxed PDB is a reviewed serialization of a scored in-memory pose, not a lossless internal pose. Surface and mutation features apply to both original and relaxed coordinates. Native BCMA maps are validated for both deletion variants. Physics has one beta_nov16 replicate, with per-pair implementation provenance retained. Native disulfide records are unmodified.

No complete WT physics reference exists: 22/23 required contestant WT energies were accepted. Do not use a reduced cohort, calculate physics percentiles, fill either failure, or redistribute the existing 50/50 confidence/physics weights. Combined and physics-supported Red escape ranks remain unavailable. Raw physics is descriptive; technically accepted output is not validated binding or experimental affinity.

Boltz provenance: seed 17, 3 recycles, 200 steps, one sample, single-sequence MSA. Common ipSAE scorer SHA-256 547e05340f1627925f7aa652b93b97393061b811497f8dfeb60f24ed3cff8fde. The 23 contestant WT Fast outputs are reused original evaluations; other pairs have their own exact outputs. Website import performs no molecular computation.

`source/import_final.py` reproduces the validated import from the original reviewed public bundle and existing frozen member metadata. `source/paired_ranking.py paired.json` recomputes display confidence/retention/Red ranks without changing the frozen thresholds. The background 302-design data.json and evidence.json remain historical snapshots; the UI marks approved contestants by joining the current frozen roster.


## Initial Q25A rational release · historical snapshot

The optional Rational Red cohort is separate from the unchanged literature benchmark. It contains the same 23 contestants and two reference controls against eight new antigen states: Q25A, F14A, N31D, E12Q, Y40F, S29T, Q38A and N42D. Q38A/N42D are contrast antigens and have no adversarial Red rank. WT is reused solely as the comparison baseline.

This frozen release contains 400 engine cells: 25 scored Fast Q25A pairs with their exact original CIFs, 25 Boltz Q25A pre-model failures, and 350 pending cells. The Boltz failures have no original structure, common score, physics attempt, or relaxed structure. Fast-derived physics is not applicable. Missing metrics remain null; numerical zeros remain zero. Later private campaign results are outside this release.

Confidence remains C = 50 × (native ipTM + maximum directional ipSAE). Rational overall Blue confidence uses half mean plus half worst across eight states, including the contrasts; all eight scores are required. Retention is a count out of eight with the original frozen engine-specific cutoffs and sensitivity margins. No rational overall Blue rank is currently available. Per-antigen ranks are available for Fast Q25A.

Each engine reuses its exact frozen 12-member WT-supported Red panel. All three raw metrics must decline under the existing rule; failed or pending cells cannot shrink the denominator. Fast Q25A has 1/12 provisional confidence-loss signals. Its rank is among currently evaluable challenges, not a full-panel winner. Biological surface expression and target integrity are unresolved for these prospective substitutions. No experimental binding or escape claim follows.

Use ?cohort=rational#blue for the rational view; the default remains literature. Nomination rationale, raw scalar/structure manifests, and a public frozen-policy subset are downloadable. The source importer pins this exact reviewed release. No private review documents, private paths, PAE, model caches, or unreviewed structures are published. No scientific computation was run for this website update.


## Initial F14A incremental release · historical snapshot

The current partial snapshot adds 25 Fast and 25 Boltz F14A scores, plus four qualified single-replicate Boltz F14A physics results. Across all 400 rational engine cells, 75 are scored (50 Fast and 25 Boltz), 25 Boltz Q25A rows remain reviewed missing-original nulls, and 300 remain pending. Later private results are outside this handoff. This is not campaign completion.

The 54 new assets are 50 exact original CIFs and four relaxed display PDBs. The earlier 25 Q25A CIFs remain unchanged, giving 79 rational assets in total. In the four PDBs only eight independently reviewed Rosetta energy-table delimiter metadata lines had private path tokens redacted. Separate source/public hashes, source/public sizes, changed-line hashes, and unchanged-other-byte proofs are retained in rational/release_f14a_r4/STRUCTURES.json and the normalized structure records. Coordinates, connectivity, disulfides, energies and scalar values remain unchanged. Relaxed display serialization is not byte-identical to the scored in-memory pose.

Accepted physics rows are B5 (reference control), BC-0fef1d499d46, BC-202d0f7e9723 and BC-6c30f596ff4a. The raw table and viewer expose metrics with units and per-pair implementation provenance. These are beta_nov16 Boltz-derived results with explicit native-disulfide preservation and separated-pose disulfide detection disabled; no Fast-derived physics exists. There are 171 pending Boltz physics rows, 25 missing-original not-evaluable rows with zero physics attempts, and 200 Fast not-applicable rows.

All ranking policies remain frozen. Fast Red F14A is 3/12 provisional signals (rank 1), Fast Q25A remains 1/12 (now rank 2 among the two evaluable challenges), and Boltz F14A is 1/12 (its only evaluable challenge). These are confidence-loss signals, not biological escape. Eight-state Blue overall ranks remain unavailable; per-antigen confidence and retention views are populated. The unchanged literature WT physics reference is 22 accepted / 23 required: no percentiles or combined ranks are calculated.

The F14A view is the rational cohort's initial antigen view. Default page entry remains the literature benchmark. The importer --incremental-f14a extends the exact pinned initial Q25A snapshot and refuses a different existing rational snapshot. Its output was independently reviewed before publication. No new molecular computation or scientific policy change was performed.


## N31D scores and completed F14A physics · historical snapshot

The current frozen partial release adds 50 N31D scores (25 Fast and 25 Boltz), the remaining 21 F14A Boltz physics records, and 11 reviewed Q38A missing-original nulls. It contains 400 rational engine cells: 125 scored (75 Fast, 50 Boltz), 36 genuine missing-original Boltz nulls (25 Q25A, 11 Q38A), and 239 pending. Exactly 25 F14A Boltz physics records are accepted; no N31D physics is included, even if later results exist elsewhere. All 200 Fast physics rows remain not applicable. Boltz has 25 accepted, 36 not-evaluable with zero attempts, and 139 pending physics records.

The 71 added structures are 50 byte-identical N31D original CIFs and 21 F14A relaxed display PDBs, totaling 9,178,875 bytes. All 79 earlier rational structures remain unchanged, for 150 rational assets alongside the unchanged 373 literature assets. The 21 PDBs have only the independently reviewed 42 energy-table delimiter metadata line redactions. Source/public hashes and sizes, line hashes, and unchanged-other-byte proofs are retained in rational/release_n31d_f14a_r1/STRUCTURES.json and normalized structure records. No coordinate, connectivity, disulfide, energy or scalar transformation was made during site integration.

All frozen policies and nomination information boundaries remain unchanged. Fast N31D is 1/12 provisional Red signals, tied rank 2 with Q25A; Boltz N31D is 0/12, rank 2. Zero is a scored observation, unlike technical nulls or pending results. F14A signals remain Fast 3/12 and Boltz 1/12. These are confidence-loss heuristics, not biological escape. Contrasts stay unranked; B5/L10 stay excluded from contestants. Eight-state Blue overall ranks remain unavailable. Original literature denominators remain five; the WT physics reference remains 22 accepted / 23 required with no percentiles, combined ranks or reallocated weights.

N31D is the rational cohort's initial antigen view. The expanded raw physics table shows all 23 contestants and two labelled binding controls for F14A, with original/relaxed viewing and exact implementation provenance. The default site entry remains the literature cohort. The --incremental-n31d-f14a importer option requires the exact prior F14A snapshot and the approved new bundle. Its bounded 50-score/21-physics/11-null change was independently reviewed. No new molecular computation or later private campaign result was introduced; this is not campaign completion.


## E12Q scores and completed N31D physics · 23 October 2026

This frozen partial release adds 50 E12Q scores (25 Fast and 25 Boltz) and 25 N31D Boltz physics records. The 400 rational engine cells contain 175 scored (100 Fast/75 Boltz), 36 reviewed missing-original Boltz nulls and 189 pending. Exactly 50 physics results are accepted: 25 F14A and 25 N31D. No E12Q physics is included. All 200 Fast physics rows remain not applicable; Boltz has 50 accepted, 36 not-evaluable with zero attempts and 114 pending.

The 75 added assets comprise 50 original E12Q CIFs and 25 N31D relaxed PDB displays, totaling 10,014,940 public bytes. All 150 prior rational assets and 373 literature assets are unchanged. The cumulative rational asset count is 225. Upstream redaction touched only 50 reviewed energy-table delimiter metadata lines in the 25 new PDBs. Source/public hashes, sizes and unchanged-other-byte proofs are preserved in rational/release_e12q_n31d_r1/STRUCTURES.json. Site integration performs no molecular computation.

Frozen policies, controls, nomination boundaries and WT panels are unchanged. Fast E12Q has 2/12 provisional confidence-loss signals (rank 2); Boltz E12Q has 0/12 (tied rank 2 with N31D). These are model-score heuristics, not biological escape. Eight-state Blue overall ranks remain unavailable. WT physics reference remains 22 accepted / 23 required, so no physics percentiles, combined ranks or weight reallocation are permitted.

E12Q is the rational cohort's initial antigen view. A separate physics antigen selector displays F14A or N31D, 25 rows each, with controls labelled and original/relaxed provenance retained. The default site entry remains the literature benchmark. The --incremental-e12q-n31d importer requires the exact preceding snapshot and approved bundle. Independent importer review and desktop/mobile checks bind this release. No later private results are included; this is not campaign completion.
