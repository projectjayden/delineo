# Validation record

19 October 2026; Windows; Python 3.12.4; engine `693e98c1391ae5878bdd869f5b1314ea927d5dc3`. The engine checkout remained clean. Tested package versions are in `requirements-local-lock.txt`; run manifests record input and database hashes.

| Check | Result |
| --- | --- |
| Seven input-contract unit tests | Passed: fixture, percent/fraction, duplicate location, missing hour, unknown seed ID, fallback-mode and nonfinite-parameter checks |
| Offline teaching run | 40 synthetic people, 72 hourly frames completed |
| Same-seed repeat | Parsed disease and movement snapshots exactly equal |
| Zero seeds and external force off | All 72 frames remained uninfected |
| Required local DMP | Completed; two DMP timelines and zero fallback timelines |
| Targeted closure | Closed teaching venue A had zero attributed infections |
| Timeout guard | One-second budget stopped the worker and recorded failed status |
| Environment | `pip check` found no broken requirements |

Sampled process-tree peak RAM: approximately 139 MiB for teaching and 154 MiB for DMP. Runtime after initial imports warmed: about 2.3 and 3.2 seconds respectively. These tiny-fixture measurements are not Barnsdall estimates.

The teaching run ended at 33 ever-infected people, with 15 venue-attributed infections. These are invented-population demonstration outcomes. The DMP run stayed at its two initial infected people over three days; this short smoke test does not validate natural-history timing or epidemic curves.

No real Barnsdall export was downloaded, historical website run reproduced, or empirical calibration performed. No second epidemic model was installed. The engine was not modified.

Re-run unit tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For integration checks, run the same configuration twice into new folders and compare parsed `simdata.json.gz` and `patterns.json.gz`. Compare JSON, not gzip bytes. Also run a zero-seed config with external force off. Repeat after engine/dependency/adapter changes.
