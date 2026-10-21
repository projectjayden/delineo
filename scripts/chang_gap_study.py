"""Synthetic Chang-style occupancy study on the local Delineo workflow.

The population is invented. It encodes the mechanism in Chang et al., Nature
2021: the same number of people visit a small hall and a large hall, so risk
differs by density. Two partial-reopening arms remove the same number of
venue person-hours. One caps each hall at 20% of its observed peak. The other
thins every hour by the same fraction. People who lose a visit stay home,
which this engine does and which Chang et al. did not model as extra household
contact. A full closure of the small hall and a delayed masking policy are the
gap arms.

This script only writes inputs and calls scripts/delineo_local.py. It does not
modify the engine.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
RUNNER = ROOT / "scripts" / "delineo_local.py"
DATA = ROOT / "data" / "local" / "chang-gap"
RUNS = ROOT / "runs" / "chang-gap"
OUT = ROOT / "results" / "chang-gap"

DAYS = 4
HOURS = DAYS * 24
LENGTH = HOURS * 60
N_GROUP = 40
PEAK_HOURS = (8, 12, 17)
OFFPEAK_HOURS = (9, 10, 11, 13, 14, 15, 16)
# Counts that make uniform thinning remove the same person-hours as a 20% peak cap.
UNIFORM_KEEP = {8: 18, 12: 18, 17: 18, 9: 4, 10: 4, 11: 4, 13: 4, 14: 4, 15: 3, 16: 3}
CAP = 8
CROWDED = "2001"
SPACIOUS = "2002"
SEED_IDS = ["0", "40"]
ARMS = ("baseline", "cap20", "uniform", "close_crowded", "mask_day2")
MOBILITY = {"baseline": "baseline", "cap20": "cap20", "uniform": "uniform",
            "close_crowded": "baseline", "mask_day2": "baseline"}


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2), encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def group_ids(start):
    return [str(start + i) for i in range(N_GROUP)]


def baseline_present(start, hour_of_day):
    if hour_of_day in PEAK_HOURS:
        return group_ids(start)
    if hour_of_day in OFFPEAK_HOURS:
        return group_ids(start)[:CAP]
    return []


def keep(ids, n):
    return ids[:n]


def present(start, hour_of_day, mode):
    base = baseline_present(start, hour_of_day)
    if mode == "baseline" or not base:
        return base
    if mode == "cap20":
        return keep(base, CAP)
    if mode == "uniform":
        return keep(base, UNIFORM_KEEP[hour_of_day])
    raise ValueError(mode)


def person_hours(mode):
    total = 0
    for hour in range(HOURS):
        hod = hour % 24
        total += len(present(0, hod, mode)) + len(present(N_GROUP, hod, mode))
    return total


def build_pap():
    people = {}
    for i in range(N_GROUP * 2):
        people[str(i)] = {"age": 30, "sex": i % 2, "home": str(i // 4)}
    homes = {str(i): {"cbg": "synthetic"} for i in range(N_GROUP // 2)}
    places = {
        CROWDED: {"cbg": "synthetic", "label": "Small hall", "area": 50, "capacity": 40,
                  "group": "dense-visit"},
        SPACIOUS: {"cbg": "synthetic", "label": "Large hall", "area": 1000, "capacity": 40,
                   "group": "sparse-visit"},
    }
    return {"people": people, "homes": homes, "places": places}


def build_patterns(mode):
    people_home = {str(i): str(i // 4) for i in range(N_GROUP * 2)}
    patterns = {}
    for minute in range(60, LENGTH + 1, 60):
        hour = minute // 60 - 1
        hod = hour % 24
        frame = {"homes": {}, "places": {}}
        at_venue = set(present(0, hod, mode)) | set(present(N_GROUP, hod, mode))
        for pid, home in people_home.items():
            if pid in at_venue:
                loc = CROWDED if int(pid) < N_GROUP else SPACIOUS
                frame["places"].setdefault(loc, []).append(pid)
            else:
                frame["homes"].setdefault(home, []).append(pid)
        patterns[str(minute)] = frame
    return patterns


def base_config(seed, arm):
    interventions = [
        {"time": 0, "mask": 0.0, "vaccine": 0.0, "capacity": 1.0, "lockdown": 0.0, "selfiso": 0.0}
    ]
    if arm == "mask_day2":
        interventions.append(
            {"time": 24, "mask": 0.5, "vaccine": 0.0, "capacity": 1.0, "lockdown": 0.0, "selfiso": 0.0}
        )
    return {
        "czone_id": 0,
        "length": LENGTH,
        "random_seed": seed,
        "randseed": False,
        "initial_infected_count": 2,
        "initial_infected_ids": SEED_IDS,
        "disease_name": "COVID-19",
        "variants": ["Delta"],
        "dmp_mode": "off",
        "aggregate_transmission": True,
        "area_aware_ventilation": True,
        "ventilation_coeff": 9.0,
        "external_foi": False,
        "external_prevalence": 0.0,
        "external_emit_factor": 1.0,
        "seed_age_spread_days": 0.0,
        "disabled_poi_ids": [CROWDED] if arm == "close_crowded" else [],
        "interventions": interventions,
    }


def prepare():
    if DATA.exists():
        raise SystemExit(f"{DATA} already exists; reuse it or remove it before regenerating")
    pap = build_pap()
    hours = {mode: person_hours(mode) for mode in ("baseline", "cap20", "uniform")}
    if hours["cap20"] != hours["uniform"]:
        raise SystemExit(f"Cap and uniform person-hours differ: {hours}")
    provenance = {
        "synthetic": True,
        "population": N_GROUP * 2,
        "days": DAYS,
        "description": (
            "Invented two-hall population for a methods comparison. Not Barnsdall, "
            "not Chicago, and not a reproduction of Chang et al. 2021."
        ),
        "groups": {
            "dense-visit": {"person_ids": "0-39", "place_id": CROWDED, "area_m2": 50},
            "sparse-visit": {"person_ids": "40-79", "place_id": SPACIOUS, "area_m2": 1000},
        },
        "schedule": {
            "peak_hours_local": list(PEAK_HOURS),
            "offpeak_hours_local": list(OFFPEAK_HOURS),
            "peak_attendance": N_GROUP,
            "offpeak_attendance": CAP,
            "cap20_attendance": CAP,
            "uniform_keep_by_hour": UNIFORM_KEEP,
        },
        "venue_person_hours": hours,
        "person_hours_removed_vs_baseline": hours["baseline"] - hours["cap20"],
        "assumption": (
            "People who lose a venue visit are placed in their own home for that hour. "
            "They do not choose another open venue and they do not defer the visit."
        ),
        "disease": "Engine simplified timeline (dmp_mode off). Not a calibrated natural history.",
        "seeds": SEED_IDS,
    }
    for mode in ("baseline", "cap20", "uniform"):
        folder = DATA / mode
        folder.mkdir(parents=True)
        save_json(folder / "pap.json", pap)
        save_json(folder / "patterns.json", build_patterns(mode))
        save_json(folder / "provenance.json", provenance | {"mobility_mode": mode})
    config_dir = ROOT / "configs" / "chang-gap"
    config_dir.mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        save_json(config_dir / f"{arm}.json", base_config(100, arm))
    print("venue person-hours", hours)
    print("removed", hours["baseline"] - hours["cap20"])


def run_one(arm, seed, zero_seeds=False):
    out = RUNS / f"{arm}-{seed}"
    if (out / "manifest.json").exists() and read_json(out / "manifest.json").get("status") == "complete":
        print("skip", out.name)
        return
    if out.exists():
        raise SystemExit(f"Incomplete run exists: {out}")
    cfg = base_config(seed, arm)
    if zero_seeds:
        cfg["initial_infected_count"] = 0
        cfg["initial_infected_ids"] = []
        out = RUNS / f"{arm}-zero"
        if (out / "manifest.json").exists():
            print("skip", out.name)
            return
    cfg_path = RUNS / "configs" / f"{out.name}.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(cfg_path, cfg)
    cmd = [PY, str(RUNNER), "run", "--data", str(DATA / MOBILITY[arm]),
           "--config", str(cfg_path), "--output", str(out),
           "--max-memory-mb", "768", "--timeout-seconds", "180"]
    subprocess.run(cmd, check=True)


def final_infected(simdata_gz):
    with gzip.open(simdata_gz, "rt", encoding="utf-8") as handle:
        blob = json.load(handle)
    last_key = max(blob, key=lambda k: int(k))
    states = next(iter(blob[last_key].values()))
    return set(states)


def analyze(seeds):
    import numpy as np
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in seeds:
        for arm in ARMS:
            folder = RUNS / f"{arm}-{seed}"
            manifest = read_json(folder / "manifest.json")
            if manifest["status"] != "complete":
                raise SystemExit(f"Incomplete {folder}")
            incidence = read_json(folder / "incidence.json")
            poi = {row["place_id"]: int(row["attributed_infections"])
                   for row in csv.DictReader((folder / "poi-incidence.csv").open(encoding="utf-8"))}
            infected = final_infected(folder / "simdata.json.gz")
            ever = len(infected)
            secondary = ever - 2
            home = int(incidence["home"])
            poi_total = sum(poi.values())
            if home + poi_total != secondary:
                raise SystemExit(f"Incidence accounting failed for {folder.name}: {home}+{poi_total}!={secondary}")
            dense = len([pid for pid in infected if int(pid) < N_GROUP]) - 1
            sparse = len([pid for pid in infected if int(pid) >= N_GROUP]) - 1
            rows.append({
                "arm": arm, "seed": seed, "ever_infected": ever, "secondary": secondary,
                "home": home, "poi": poi_total,
                "small_hall": poi.get(CROWDED, 0), "large_hall": poi.get(SPACIOUS, 0),
                "dense_group_secondary": dense, "sparse_group_secondary": sparse,
                "seconds": manifest["elapsed_seconds"], "peak_mib": manifest["sampled_peak_rss_mib"],
            })
    fieldnames = list(rows[0])
    with (OUT / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def boot(values):
        a = np.asarray(values, dtype=float)
        rng = np.random.default_rng(742)
        means = rng.choice(a, size=(10000, len(a)), replace=True).mean(1)
        return float(a.mean()), float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))

    by = {(r["arm"], r["seed"]): r for r in rows}
    pairs = [("cap20", "baseline"), ("uniform", "baseline"), ("cap20", "uniform"),
             ("close_crowded", "baseline"), ("mask_day2", "baseline")]
    effects = []
    for treatment, reference in pairs:
        for metric in ("secondary", "home", "poi", "dense_group_secondary", "sparse_group_secondary"):
            delta = [by[reference, s][metric] - by[treatment, s][metric] for s in seeds]
            mean, lo, hi = boot(delta)
            effects.append({
                "comparison": f"{reference}_minus_{treatment}", "metric": metric, "n": len(seeds),
                "mean_avoided_by_treatment": round(mean, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3),
                "treatment_lower_on_n_seeds": sum(d > 0 for d in delta),
            })
    with (OUT / "paired-effects.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(effects[0]))
        writer.writeheader()
        writer.writerows(effects)
    summary = []
    for arm in ARMS:
        part = [r for r in rows if r["arm"] == arm]
        summary.append({
            "arm": arm,
            "mean_secondary": round(sum(r["secondary"] for r in part) / len(part), 2),
            "mean_home": round(sum(r["home"] for r in part) / len(part), 2),
            "mean_poi": round(sum(r["poi"] for r in part) / len(part), 2),
            "mean_small_hall": round(sum(r["small_hall"] for r in part) / len(part), 2),
            "mean_large_hall": round(sum(r["large_hall"] for r in part) / len(part), 2),
            "mean_dense_group_secondary": round(sum(r["dense_group_secondary"] for r in part) / len(part), 2),
            "mean_sparse_group_secondary": round(sum(r["sparse_group_secondary"] for r in part) / len(part), 2),
            "extinct": sum(r["secondary"] == 0 for r in part),
        })
    with (OUT / "arm-summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print("arm summary")
    for row in summary:
        print(row)
    print("paired secondary effects (positive means the treatment had fewer infections)")
    for row in effects:
        if row["metric"] == "secondary":
            print(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "discover", "evaluate", "zero", "analyze"))
    parser.add_argument("--seeds", default="101-108")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
        return
    if args.command == "discover":
        for arm in ARMS:
            run_one(arm, 100)
        return
    if args.command == "zero":
        run_one("baseline", 0, zero_seeds=True)
        return
    if "-" in args.seeds:
        start, end = args.seeds.split("-")
        seeds = list(range(int(start), int(end) + 1))
    else:
        seeds = [int(s) for s in args.seeds.split(",")]
    if args.command == "evaluate":
        for seed in seeds:
            for arm in ARMS:
                run_one(arm, seed)
        return
    analyze(seeds)


if __name__ == "__main__":
    main()
