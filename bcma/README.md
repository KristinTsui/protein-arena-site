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

The existing confidence-plus-physics policy remains unchanged. Do not fill missing physics values, substitute WT for variants, average engines, or attribute Boltz-derived physics to Fast. New releases must refresh reviewed score collections and exact matching structures and rerun the checks. A complete WT cohort is required before freezing a Red panel. Recompute every rank for the entire snapshot after adding cells.

## Selection-stage archive

```sh
python3 -B source/build_data.py --input evidence.json --output data.json
```

This command rebuilds only the original 302-design archive, not the paired evaluation. GitHub Pages is static; it does not poll CoreHPC. Historical root pages are preserved.

Viewer: 3Dmol.js 2.5.5, distributed with its licenses in vendor/.
