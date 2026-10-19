# Website-free Delineo workflow

## 1. Architecture and scope

Use `delineo` as the experiment workspace and `../Simulation` as the engine. The wrapper imports `simulator.runner.SimulationRunner`, supplies local population and movement through its `data_loader` argument, and executes the engine directly. No Flask, browser, database server, or hosted job submission is needed.

The older `../PandemicModel` repository has a different structure and older environment instructions; do not mix it into this workflow. The original notebook only retrieves existing results. Changing its `RUNS` list does not create simulations.

| Mode | Progression source | Use |
| --- | --- | --- |
| `dmp_mode: off` | Engine's simplified fallback timeline | Learn inputs, outputs, movement and experiment mechanics |
| `dmp_mode: required` | Bundled DMP database or explicitly supplied CSV model | Experiments after reviewing model selection and timing |

`auto` is rejected to prevent silently mixed timeline sources. Worker network calls are blocked. A successful required-mode run proves execution, not empirical calibration or correct disease timing.

## 2. Install once

Open PowerShell in `C:\Users\Jayden\Desktop\delineo`. Use Python 3.12 (tested: 3.12.4). The neighboring `Simulation` folder must contain `simulator/runner.py` and, for DMP, `dmp/app/state_machine/state_machines.db`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local-lock.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Already completed on this machine. Calling the environment's Python directly avoids activation-policy issues. The lock preserves tested transitive versions; `requirements-local.txt` lists direct dependencies. Streamlit is needed because upstream DMP utilities import it; no Streamlit server is launched. The notebook has separate dependencies in `requirements.txt`.

If the engine moves, pass `--engine 'C:\path\to\Simulation'`. Preserve the engine revision and modifications: a recorded commit and dirty-status list cannot reconstruct uncommitted code. Commit or archive it before a paper experiment.

## 3. Generate and inspect local inputs

```powershell
.\.venv\Scripts\python.exe scripts\delineo_local.py fixture
```

This creates `data/local/teaching/` and refuses to overwrite it. It already exists here; use `--output data/local/teaching-2` for another copy.

The fixture contains 40 invented adults, ten homes, two venues, and 72 hourly movement frames. People visit venues during the synthetic daytime schedule and return home otherwise. It does not represent Barnsdall demographics or schools. `provenance.json` labels it synthetic. The config fixes initial people `0` and `1` and seed 20261019.

## 4. Run the engine

```powershell
.\.venv\Scripts\python.exe scripts\delineo_local.py run --output runs\baseline-001
.\.venv\Scripts\python.exe scripts\delineo_local.py run --config configs\teaching-dmp.json --output runs\dmp-001
```

Output directories must be new to prevent stale-result reuse. A nonzero exit code means failure. Read `run.log` and `manifest.json`; exclude incomplete runs rather than analyzing partial files.

Defaults: one worker, a 1,024 MiB worker-process-tree RAM budget, a 300-second timeout, and 512 MiB of available system RAM reserved. The monitor samples every 0.1 seconds; this is a practical stop mechanism, not an operating-system allocation limit. Parent input validation happens before worker monitoring; each input is therefore capped at 32 MiB. This is a small JSON pilot workflow, not a city-scale loader.

```powershell
.\.venv\Scripts\python.exe scripts\delineo_local.py run --output runs\longer-pilot --max-memory-mb 1024 --timeout-seconds 600
```

At inspection the machine had approximately 16 GiB installed and 3.2 GiB available. Keep experiments sequential. Snapshots stream to compressed files and summaries read one timestep at a time, but input movement frames and engine state still occupy RAM. Increase dataset size only after measuring a coherent pilot.

## 5. Read outputs correctly

| File | Meaning |
| --- | --- |
| `manifest.json` | Status, revision, explicit seed, input/database hashes, runtime and sampled peak RAM |
| `config.json` | Requested parameters |
| `effective-config.json` | Normalized parameters and engine/environment defaults |
| `environment.txt` | Installed package versions |
| `result.json` | Engine metadata, actual initial IDs, schedule, timeline-source and redirect counts |
| `states.csv` | Hourly disease-state flags and ever-infected count |
| `poi-incidence.csv` | Final cumulative attributed infections by POI |
| `incidence.json` | Home total, POI counts and location/person decode metadata |
| `simdata.json.gz` | Raw per-person state snapshots |
| `patterns.json.gz` | Raw movement and cumulative incidence snapshots |
| `run.log` | Diagnostics |

State columns can overlap: someone may be infectious and symptomatic. Do not sum them to get population or total infections. `Infected` is one engine flag, not a verified active-case measure. `ever_infected` counts cumulative infection history. Do not relabel `Removed` as deaths without checking the selected model's mapping.

Initial seeded cases are not venue-acquired infections. Home plus POI incidence need not equal ever-infected; for a closed-system run, check the difference against initial seeds. `pinc` is cumulative attributed incidence, not infectious attendance. Derive hourly attributed incidence by differencing cumulative snapshots, checking nonnegative differences and totals first.

Known upstream issue: `result.json` can say `random_seed_behavior: deterministic:0` despite an explicit nonzero seed. Use the actual seed in the manifest/config; the engine seeds Python and NumPy with that value. Repeatability tests compare parsed JSON snapshots, not gzip bytes, whose headers can differ.

## 6. Change one policy

Close teaching venue A for the full run:

```powershell
$scenario = Get-Content configs\teaching.json -Raw | ConvertFrom-Json
$scenario.disabled_poi_ids = @('1001')
$scenario | ConvertTo-Json -Depth 20 | Set-Content configs\close-venue-a.json
.\.venv\Scripts\python.exe scripts\delineo_local.py run --config configs\close-venue-a.json --output runs\close-venue-a-001
```

The engine redirects disabled-venue visits home, which can shift transmission to households. It does not model visitors selecting alternative open venues. The disabled list applies to the full run; timed targeted closures are not implemented by this wrapper.

Add 50% masking at hour 12:

```powershell
$scenario = Get-Content configs\teaching.json -Raw | ConvertFrom-Json
$scenario.interventions += [pscustomobject]@{
    time=12; mask=0.5; vaccine=0.0; capacity=1.0; lockdown=0.0; selfiso=0.0
}
$scenario | ConvertTo-Json -Depth 20 | Set-Content configs\mask-hour12.json
.\.venv\Scripts\python.exe scripts\delineo_local.py run --config configs\mask-hour12.json --output runs\mask-hour12-001
```

Each row is a complete policy. Intervention `time` is in **hours**; `length` and movement keys are in **minutes**. Fractions are 0–1, not percentages. Venue area is square metres. Hour 12 applies at minute 720. Capacity multipliers need valid positive listed capacities; check redirects rather than assuming a policy affected movement.

## 7. Repeat seeds sequentially

Use identical population, mobility, horizon, initial IDs and model settings across paired arms. A shared seed does not guarantee identical draws after policies alter execution paths.

After creating the closure config above, run a ten-replicate pilot:

```powershell
New-Item -ItemType Directory -Force runs\pilot-configs | Out-Null
foreach ($seed in 100..109) {
    foreach ($arm in @('teaching', 'close-venue-a')) {
        $scenario = Get-Content "configs\$arm.json" -Raw | ConvertFrom-Json
        $scenario.random_seed = $seed
        $configPath = "runs\pilot-configs\$arm-$seed.json"
        $scenario | ConvertTo-Json -Depth 20 | Set-Content $configPath
        .\.venv\Scripts\python.exe scripts\delineo_local.py run --config $configPath --output "runs\pilot-$arm-$seed"
        if ($LASTEXITCODE -ne 0) { throw "Failed $arm seed $seed; inspect run.log" }
    }
}
```

This is a demonstration, not a calibrated experiment. For research, start from reviewed DMP settings and the actual input bundle. Ten seeds are a pilot, not an adequate-precision guarantee. Report extinction frequency and unconditional outcomes; never omit zero-spread runs merely because they seem uninteresting.

## 8. Use Barnsdall without the website

The current folder has historical result IDs but not the original reusable population/mobility bundle. Result maps are not substitutes for those inputs. Obtain an export from the project/backend with zone ID, population/movement identifiers, generation settings, time origin, version, permissions and hashes.

The engine's read-only input endpoint is `patterns/{czone_id}?length={minutes}`, relative to `DELINEO_DB_URL`. It differs from the notebook's `simdata/{run_id}/map` result endpoint. `StreamDataLoader.load_bulk` reads a PAP JSON line followed by JSON or binary patterns. Endpoint availability and export size were not tested here; do not load a full zone blindly with limited RAM.

The wrapper accepts this local JSON contract:

```text
data/local/barnsdall-pilot/
  pap.json         {"people": {ID: {"age": ..., "sex": ..., "home": HOME_ID}},
                    "homes": {HOME_ID: {...}}, "places": {POI_ID: {...}}}
  patterns.json    {"60": {"homes": {HOME_ID: [PERSON_ID, ...]},
                          "places": {POI_ID: [PERSON_ID, ...]}}, ...}
  provenance.json  source identifiers, generation settings, licensing, time origin
```

All IDs are strings. Every person must occur exactly once per hourly frame, minute 60 through `length`. Binary or sparse/delta exports require a converter that reconstructs complete occupancy and preserves IDs. Automated download and this converter are not implemented here; an existing complete JSON export can be used directly after validation.

Create a matching config with true zone ID, duration, seed IDs and reviewed disease settings:

```powershell
.\.venv\Scripts\python.exe scripts\delineo_local.py run --data data\local\barnsdall-pilot --config configs\barnsdall-pilot.json --output runs\barnsdall-pilot-001
```

This is a template: those Barnsdall files are not present. For a subset, preserve coherent households/venues/movement and document boundary assumptions. Arbitrarily truncating people changes connectivity. Extending duration requires corresponding movement frames; repeating synthetic data is an assumption, not observed mobility.

## 9. Before publication experiments

1. Re-run input tests, same-seed repeats, zero-seed controls and closure checks on the final revision.
2. Audit DMP transition distributions and units. Engine time is minutes, policy time hours, and disease timing passes through additional conversion. Validate sampled durations against the intended model before interpreting curves.
3. Verify DMP coverage and matched paths for age, sex, vaccination and variant groups. Zero fallback does not establish correct matching.
4. Check occupancy, floor area, capacities and school identifiers against source data. Freeze and hash inputs.
5. For empirical accuracy, define observed targets and reporting/delay models; simulated infections are not reported cases. Separate calibration and validation periods before fitting.
6. Freeze metrics, policy arms, uncertainty/stopping rules and exclusions, then run sequential ensembles.
7. Archive source revisions, configs, dependency lock, data provenance, numerical tables and figure scripts.

See [experiment-plan.md](experiment-plan.md) for the proposed paper design.

## 10. Troubleshooting

| Symptom | Action |
| --- | --- |
| Engine missing | Supply `--engine` pointing to the current Simulation checkout |
| Import failure | Use `.venv` Python and the tested lock |
| Output exists | Choose a new folder; preserve prior results |
| Missing/duplicate person in movement | Repair the export, not the validator |
| DMP failure or blocked connection | Inspect the local model/database/dependencies; use `off` only for the simplified example |
| Memory budget exceeded | Reduce coherent dataset size or close applications; keep runs sequential |
| No secondary infections | Check infectious timing, occupancy and parameters; extinction can also be a valid stochastic result |
| Notebook rejects output | Use local CSVs; the website's result schema differs |
