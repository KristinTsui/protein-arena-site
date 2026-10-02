# ProteinArena website

A single self-contained `index.html` combines the recorded BCMA arena with the experimental verification benchmark. No backend, external assets, or computation service is required to view it. The active tab alone is decompressed and mounted to limit memory use.

This fixed release includes 4 of 6 completed arena rounds, 135 verified prediction samples and 24 pending samples. Further simulation and validation continue separately. Pending results are not inferred or promoted to verified results. Arena designs have not been experimentally validated.

The benchmark retains its experimental binding labels, assays, measurements, units, score calculations, source citations, structures and provenance hashes. ProteinBase data are attributed to ProteinBase and the original contributors; source studies are linked in the dashboard. Bundled 3Dmol and third-party license notices are included under About & credits.

Personal machine paths and signed profile-image URLs have been removed from the public export. Only the site and its release receipt belong on this branch. The private source branch and simulation campaign are separate.

`release.json` records the exact embedded payload hashes and checkpoint. Later releases should use a newly validated immutable arena snapshot, preserve the verified benchmark payload, rebuild this file and repeat browser/data-integrity checks before publication.

Current presentation: antigen mutation sites use saturated coral (`#ff4d4d`) and minibinder mutation sites use electric cyan (`#00e5ff`), with explicit legends. The benchmark displays EGFR, HER2, ProteinBase EGFR and ProteinBase TREM2. C5, CD22 and ProteinBase FGFR1 are hidden; their source records and computed scores remain preserved. Overall scores summarize visible datasets only.
