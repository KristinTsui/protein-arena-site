# ProteinArena website

A single self-contained `index.html` combines the recorded BCMA arena with the experimental verification benchmark. No backend, external assets, or computation service is required to view it. The active tab alone is decompressed and mounted to limit memory use.

This fixed release includes 3 of 6 completed arena rounds, 105 verified prediction samples and 30 pending samples. Further simulation and validation continue separately. Pending results are not inferred or promoted to verified results. Arena designs have not been experimentally validated.

The benchmark retains its experimental binding labels, assays, measurements, units, score calculations, source citations, structures and provenance hashes. ProteinBase data are attributed to ProteinBase and the original contributors; source studies are linked in the dashboard. Bundled 3Dmol and third-party license notices are included under About & credits.

Personal machine paths and signed profile-image URLs have been removed from the public export. Only the site and its release receipt belong on this branch. The private source branch and simulation campaign are separate.

`release.json` records the exact embedded payload hashes and checkpoint. Later releases should use a newly validated immutable arena snapshot, preserve the verified benchmark payload, rebuild this file and repeat browser/data-integrity checks before publication.
