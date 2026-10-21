# Delineo: local simulation and research workflow

Run the existing JHU Delineo engine from PowerShell/Python without opening the website or starting a web server. This folder contains the experiment wrapper and analysis; the engine remains in the neighboring `../Simulation` checkout.

**Start with [the detailed workflow](docs/local-workflow.md).** See the [research plan](docs/experiment-plan.md), [project audit](docs/analysis-notes.md), and [validation record](docs/validation.md).

## Run now

The environment and teaching inputs have already been created on this machine. From this folder:

```powershell
.\.venv\Scripts\python.exe scripts\delineo_local.py run --output runs\my-first-run
.\.venv\Scripts\python.exe scripts\delineo_local.py run --config configs\teaching-dmp.json --output runs\my-first-dmp-run
```

Use a new output directory each time. The example uses 40 invented people, two venues and three simulated days. The first config uses simplified disease timelines; the second requires the local disease-progression database. Both execute the actual Delineo engine with network calls blocked. These examples are not calibrated Barnsdall simulations.

## Contents

| File | Purpose |
| --- | --- |
| `scripts/delineo_local.py` | Offline runner, validation, memory monitoring, provenance and CSV export |
| `configs/teaching.json` | Small synthetic example with simplified progression |
| `configs/teaching-dmp.json` | Example requiring local DMP progression |
| `requirements-local-lock.txt` | Exact environment tested on Windows/Python 3.12.4 |
| `requirements-local.txt` | Direct runner dependencies |
| `docs/local-workflow.md` | Setup, execution, inputs, interpretation and repeated experiments |
| `docs/experiment-plan.md` | Publication-oriented questions and study design |
| `docs/chang-gap-study.md` | Chang et al. 2021 usage map and the two-hall experiment |
| `delineo use_case-demo.ipynb` | Original analysis of hosted runs 187–196, preserved |
| `xuanyi_jayden.pdf` | Original project presentation, preserved |
| `requirements.txt` | Original notebook dependencies |

Generated inputs live in `data/local/` and outputs in `runs/`; both are ignored by Git. Local results have a different schema from website responses, so use the exported CSVs rather than substituting raw files into the original notebook.

The likely requested reference is Chang et al., [Mobility network models of COVID-19 explain inequities and inform reopening](https://doi.org/10.1038/s41586-020-2923-3), Nature 589, 82–87 (2021; online November 2020). This identification is provisional. The plan draws on its experimental approach, without claiming a reproduction.

Historical runs are exploratory: registered intervention labels and server metadata differ, and initial infections differ. A fixed-input, repeated-seed comparison on an invented two-hall population is in [docs/chang-gap-study.md](docs/chang-gap-study.md). It is a methods study, not a calibrated city result.
