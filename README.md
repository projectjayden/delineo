# Delineo: POI-level simulation analysis

An exploratory analysis of Delineo simulation runs for the **Barnsdall, Oklahoma convenience zone**, focusing on where infections occur, how hotspots vary across runs, and how to design reproducible intervention comparisons.

This repository contains an analysis notebook, not the Delineo simulator itself. Simulations are generated using the [Delineo simulator](https://covidmod.isi.jhu.edu/simulator); the notebook retrieves and analyzes their outputs.

## Current status

The notebook registers runs **187–196**, retrieves chart and map data, validates their structure, and produces six POI comparison figures. It pays particular attention to **St John Catholic School** and **Avant Public School**, which frequently rank highly in runs with substantial POI transmission.

**These runs are exploratory, not a validated ten-policy experiment.** Cached server metadata differs from the intended labels for nine runs, and initial infected individuals differ. The notebook includes a parameter audit and labels POI plots by run ID. Outcome differences must not be interpreted as causal intervention effects. See [analysis notes](docs/analysis-notes.md) for the evidence and interpretation limits.

## Contents

| File | Purpose |
| --- | --- |
| [`notebooks/delineo_use_case_demo.ipynb`](notebooks/delineo_use_case_demo.ipynb) | Current English-language analysis notebook; saved execution outputs are cleared |
| [`docs/analysis-notes.md`](docs/analysis-notes.md) | Data definitions, metadata discrepancies, figure interpretation, and two-school research questions |
| [`docs/experiment-plan.md`](docs/experiment-plan.md) | Proposed A/B/C follow-up experiments and additional data requirements |
| [`requirements.txt`](requirements.txt) | Python packages needed to run the notebook |
| [`.gitignore`](.gitignore) | Excludes generated caches, exports, notebook checkpoints, and local environments |

## Setup

Use Python 3.11 or later in a separate environment:

```bash
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Then install packages and open JupyterLab:

```bash
python -m pip install -r requirements.txt
python -m jupyter lab
```

Open `notebooks/delineo_use_case_demo.ipynb` and run its cells in order. Internet access to the Delineo API is required on the first data load. API availability and retention of these run IDs are controlled by the upstream service.

## Workflow

1. **Register runs.** `RUNS` holds each actual `run_id`, its intended label, initial settings, and intervention schedule. Editing this list does not create or modify a simulation.
2. **Generate URLs.** The notebook constructs result-page, `chartdata`, `map`, and snapshot URLs automatically.
3. **Load and cache.** Each run's chart and map responses are cached. Set `REFRESH_CACHE = True` when a fresh API read is needed; otherwise existing cached responses are reused.
4. **Validate a snapshot.** `SELECTED_LABEL` selects the run for detailed checks. `SNAPSHOT_API_TIME = None` selects its last available snapshot. API timestamps and intervention hours are distinct; use returned `timesteps` for snapshot requests.
5. **Inspect disease-state data.** The `Infected` state is analyzed under its raw field name. It has not been established here as equivalent to the website's aggregate active-infection metric.
6. **Audit metadata before interpreting comparisons.** The POI section compares registered schedules with cached server schedules and checks the zone, population/mobility identifiers, observation horizon, and POI alignment.
7. **Generate figures and CSV tables.** Counts are aligned across runs by unique `placekey` values.

The existing state-summary cell precedes the POI audit and retains registered scenario names. Treat that table as provisional; consult the audit before using those names in a report.

## Figures

| Figure | Question |
| --- | --- |
| POI Top-N rankings | Which POIs have the most attributed infections in each run? |
| Absolute-reduction heatmap | Which locations have fewer or more infections than the selected reference run? |
| Hotspot rank shifts | How do the same POIs change rank between two runs? |
| Top-10 Jaccard overlap | How similar are hotspot sets across runs? Ties at the cutoff are included. |
| Home/POI counts and shares | How do absolute transmission totals and location composition differ? |
| POI category heatmap | Which categories carry the largest infection burden? |

The default reference is run 187, which has **zero POI-attributed infections**. Consequently, positive POI reductions relative to it are impossible and percentage reductions are undefined. The rank-shift example instead compares runs 189 and 194 descriptively. Change `BASELINE_RUN_ID`, `RANK_RUN_IDS`, and `TOP_N` when appropriate for a new analysis.

## Generated files

`EXPORT_DIR = Path("delineo_exports")` is relative to the notebook kernel's working directory. It contains URL registries, cached API responses under `raw/`, state summaries, and figures/tables under `poi_comparison/`. These generated files are excluded from Git.

Raw API caches, individual trajectories, unrelated local documents, and credentials are not bundled. The repository copy preserves the current notebook's code and markdown while removing execution outputs and local execution metadata.

## Validation and next steps

The POI analysis has been exercised against local cached responses for all ten runs, aligning **3,180 POIs across ten runs** and generating six figures. The publication copy passes notebook-format and Python-syntax validation. This does not establish scientific validity, verify the live API, or guarantee reproducibility of stochastic simulations without recorded seeds and model versions.

Planned work: verify submitted intervention schedules, run controlled A/B/C experiments with repeated seeds, and extract hourly attendance and infection-attribution series for the two focal schools. The [experiment plan](docs/experiment-plan.md) separates planned work from current functionality.

## References

- [Delineo simulator](https://covidmod.isi.jhu.edu/simulator)
- [Delineo project overview](https://covidmod.isi.jhu.edu/about)
- [Delineo Fullstack repository](https://github.com/Delineo-Disease-Modeling/Fullstack)

This analysis repository is not an official release of Delineo. Model results describe simulated populations and should not be presented as measured risk at real schools.
