# ProteinArena

A single-file website combining the recorded BCMA design arena and the experimental verification benchmark.

This fixed release includes all 6 completed arena rounds and 315 verified prediction samples, with no predictions pending. All six decisions passed the independent campaign audit. Arena designs have not been experimentally validated.

The benchmark shows EGFR, HER2, ProteinBase EGFR and ProteinBase TREM2. C5, CD22 and FGFR1 are temporarily hidden, with their records retained. Scientific measurements and calculations are unchanged.

All heatmaps use light-to-green colors, with darker shades indicating higher confidence or more favorable values. Actual values is the default: ipSAE/ipTM have a fixed 0–1 scale, while lower interface energies and KD/EC50 values are darker. Relative ranks use the same palette with rank 1 darkest. Agreement also uses green with 1 darkest; its labels distinguish agreement from structural confidence. The row summary matches the selected Concordance/AUROC benchmark metric; Spearman remains in Ranks.

The arena preserves distinct bright antigen (#ff4d4d) and binder (#00e5ff) mutation highlights, aligned complexes, camera controls and all per-model scores.

`release.json` records the embedded payload hashes and checkpoint. Future releases should use a newly validated immutable arena snapshot, preserve the benchmark data, and pass browser and data-integrity checks before publication.

Experimental data retain their source citations, including ProteinBase and the original study authors. Molecular viewer licenses are included in the website’s About & credits panel. Only the static public site is published; computation sources and private run paths are excluded.
