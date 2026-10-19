# Project audit — 19 October 2026

The original folder had a README, requirements file, `delineo use_case-demo.ipynb`, and `xuanyi_jayden.pdf`. The old README linked to a nonexistent notebook directory and missing documentation. The new README uses actual paths; the notebook and PDF remain unchanged.

The notebook downloads hosted runs 187–196, audits metadata and compares POIs. The presentation suggests hotspots, intervention timing, community comparisons, demographics and hospital planning. These are useful hypotheses, not completed controlled experiments.

The saved notebook reports mismatched intervention schedules and different initial infections, with zero POI incidence in run 187. These historical findings were read from existing files, not revalidated against the live API here. Its initial state-summary table precedes the audit. Use run IDs for descriptive historical comparisons and verified schedules for new experiments.

The neighboring `Simulation` checkout at `693e98c1391ae5878bdd869f5b1314ea927d5dc3` provides direct input injection, explicit seeds, aggregate transmission, area-aware ventilation, disabled venues and local DMP. The separate legacy `PandemicModel` repository was inspected for orientation, not modified or installed.

The wrapper requires one variant/aggregate transmission and suppresses per-contact logging. It exports its own CSVs rather than reproducing the website result-processing pipeline. State flags can overlap.

Outstanding research issues: explicit-seed description mismatch in upstream metadata; natural-history timing and demographic match validation; absent historical input bundle; conversion of binary/delta mobility to the strict local contract; calibration of ventilation/boundary assumptions. The initial workflow does not automate calibration, matched-cost policy selection or publication figures. Its memory monitor is sampled, not a hard OS limit.
