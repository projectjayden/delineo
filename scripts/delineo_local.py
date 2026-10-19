"""Run the existing sibling Simulation engine offline; no web server required."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def validate(config, pap, patterns):
    """Strict teaching-workflow contract; refuses ambiguous units and bad inputs."""
    allowed = {"czone_id", "length", "random_seed", "randseed", "initial_infected_count",
               "initial_infected_ids", "disease_name", "variants", "dmp_mode", "interventions",
               "aggregate_transmission", "area_aware_ventilation", "ventilation_coeff",
               "external_foi", "external_prevalence", "external_emit_factor", "disabled_poi_ids",
               "seed_age_spread_days", "model_path_by_variant", "matrix_csv_by_variant"}
    if set(config) - allowed:
        raise ValueError(f"Unknown config keys: {sorted(set(config) - allowed)}")
    integer(config.get("length"), "length (minutes)", 60)
    if config["length"] % 60:
        raise ValueError("length must be a multiple of 60 minutes")
    integer(config.get("random_seed"), "random_seed")
    if config["random_seed"] >= 2**32:
        raise ValueError("random_seed must be below 2**32")
    integer(config.get("czone_id"), "czone_id")
    integer(config.get("initial_infected_count"), "initial_infected_count")
    if config.get("dmp_mode") not in ("off", "required"):
        raise ValueError("Use dmp_mode='off' for teaching or 'required' for DMP; auto is forbidden")
    if not isinstance(config.get("variants"), list) or len(config["variants"]) != 1:
        raise ValueError("This workflow supports exactly one variant")
    for name in ("randseed", "aggregate_transmission", "area_aware_ventilation", "external_foi"):
        if type(config.get(name)) is not bool:
            raise ValueError(f"{name} must be explicitly true or false")
    if not config["aggregate_transmission"]:
        raise ValueError("This workflow requires aggregate_transmission=true for incidence output")
    for name in ("ventilation_coeff", "external_prevalence", "external_emit_factor", "seed_age_spread_days"):
        v = config.get(name)
        if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
            raise ValueError(f"{name} must be explicitly finite and nonnegative")
    if config["ventilation_coeff"] == 0 or config["external_prevalence"] > 1:
        raise ValueError("ventilation_coeff must be positive; external_prevalence must be <=1")
    for key in ("people", "homes", "places"):
        if not isinstance(pap.get(key), dict) or not pap[key]:
            raise ValueError(f"pap.{key} must be a nonempty ID-keyed dictionary")
    people = pap["people"]
    if config["initial_infected_count"] > len(people):
        raise ValueError("More initial infections than people")
    seeds = config.get("initial_infected_ids", [])
    if not isinstance(seeds, list) or len(seeds) != len(set(seeds)) or set(seeds) - set(people):
        raise ValueError("Initial IDs must be unique existing string person IDs")
    if seeds and len(seeds) != config["initial_infected_count"]:
        raise ValueError("Explicit initial IDs must match initial_infected_count")
    for pid, person in people.items():
        if str(person.get("home")) not in pap["homes"]:
            raise ValueError(f"Person {pid} has no valid home")
        if not {"age", "sex"} <= person.keys():
            raise ValueError(f"Person {pid} lacks age/sex")
    if set(config.get("disabled_poi_ids", [])) - set(pap["places"]):
        raise ValueError("Unknown disabled POI ID")
    rows = config.get("interventions", [])
    if not rows or rows[0].get("time") != 0:
        raise ValueError("An initial intervention row at hour 0 is required")
    last = -1
    fields = {"mask", "vaccine", "capacity", "lockdown", "selfiso"}
    for row in rows:
        if set(row) != fields | {"time"}:
            raise ValueError("Each policy must specify time, mask, vaccine, capacity, lockdown, selfiso")
        integer(row["time"], "intervention time (hours)")
        if not last < row["time"] < config["length"] / 60:
            raise ValueError("Policy hours must increase and precede the end of the run")
        last = row["time"]
        for key in fields:
            v = row[key]
            if type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError(f"{key} is a fraction in [0,1], not a percentage")
    expected = {str(t) for t in range(60, config["length"] + 1, 60)}
    if not isinstance(patterns, dict) or set(patterns) != expected:
        raise ValueError("Patterns must have exactly one frame per hour, keyed by minutes 60..length")
    for t, frame in patterns.items():
        seen = set()
        for kind in ("homes", "places"):
            for loc, ids in frame[kind].items():
                if loc not in pap[kind]:
                    raise ValueError(f"Unknown {kind} location {loc} at {t}")
                for pid in ids:
                    if pid not in people or pid in seen:
                        raise ValueError(f"Unknown or multiply located person {pid} at {t}")
                    seen.add(pid)
        if seen != set(people):
            raise ValueError(f"Incomplete population movement frame at {t}")


def fixture(target):
    target.mkdir(parents=True, exist_ok=False)
    people = {str(i): {"age": 30, "sex": i % 2, "home": str(i // 4)} for i in range(40)}
    pap = {"people": people, "homes": {str(i): {"cbg": "synthetic"} for i in range(10)},
           "places": {"1001": {"cbg": "synthetic", "label": "Teaching venue A", "area": 150, "capacity": 40},
                      "1002": {"cbg": "synthetic", "label": "Teaching venue B", "area": 300, "capacity": 40}}}
    patterns = {}
    for t in range(60, 4321, 60):
        frame = {"homes": {}, "places": {}}
        for pid, p in people.items():
            daytime = 8 <= (t // 60) % 24 < 18
            kind = "places" if daytime else "homes"
            loc = str(1001 + int(pid) % 2) if daytime else p["home"]
            frame[kind].setdefault(loc, []).append(pid)
        patterns[str(t)] = frame
    save_json(target / "pap.json", pap)
    save_json(target / "patterns.json", patterns)
    save_json(target / "provenance.json", {"synthetic": True, "population": 40,
              "description": "Invented teaching population; not Barnsdall or measured JHU data."})
    print(target.resolve())


def git_info(engine):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(engine), *args], text=True).strip()
    return {"commit": git("rev-parse", "HEAD"), "status": git("status", "--porcelain")}


def summarize(out, pap, length):
    import gzip
    import ijson
    # One timestep at a time; never materialize the complete output history.
    rows = 0
    with gzip.open(out / "simdata.json.gz", "rb") as f, (out / "states.csv").open("w", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=["time_minutes", "ever_infected", "Infected", "Infectious",
                                              "Symptomatic", "Hospitalized", "Recovered", "Removed"])
        writer.writeheader()
        previous = 0
        for key, frame in ijson.kvitems(f, ""):
            t = int(key)
            states = next(iter(frame.values()))
            if t <= previous or len(states) > len(pap["people"]):
                raise ValueError("Output time/population validation failed")
            previous = t
            row = {"time_minutes": t, "ever_infected": len(states)}
            for name, bit in [("Infected", 1), ("Infectious", 2), ("Symptomatic", 4),
                              ("Hospitalized", 8), ("Recovered", 16), ("Removed", 32)]:
                row[name] = sum(bool(int(s) & bit) for s in states.values())
            writer.writerow(row)
            rows += 1
    if rows != length // 60 or previous != length:
        raise ValueError("Output does not cover the requested horizon")
    with gzip.open(out / "patterns.json.gz", "rb") as f:
        final = None
        meta = None
        for key, value in ijson.kvitems(f, ""):
            if key == "meta":
                meta = value
            else:
                final = value
    if final is None or "pinc" not in final or meta is None:
        raise ValueError("Engine did not emit numeric incidence snapshots")
    poi_ids = meta["loc_ids"][int(meta["n_homes"]):]
    if len(poi_ids) != len(final["pinc"]):
        raise ValueError("POI incidence/decode metadata length mismatch")
    with (out / "poi-incidence.csv").open("w", newline="", encoding="utf-8") as dst:
        writer = csv.writer(dst)
        writer.writerow(["place_id", "label", "attributed_infections"])
        for pid, count in zip(poi_ids, final["pinc"]):
            writer.writerow([pid, pap["places"][pid].get("label", pid), int(count)])
    # Preserve engine decode metadata; do not assume sorted IDs match engine array order.
    save_json(out / "incidence.json", {"home": int(final["hinc"]),
              "places_in_engine_order": [int(x) for x in final["pinc"]], "decode_metadata": meta})


def worker(args):
    out = args.output.resolve()
    # No network access from the simulation, including accidental DMP HTTP fallback.
    def no_network(*a, **kw):
        raise RuntimeError("Offline runner blocked a network call; provide local data/DMP")
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    socket.create_connection = no_network
    sys.path.insert(0, str(args.engine.resolve()))
    os.environ["DELINEO_SOA_ENGINE"] = "1"
    os.environ["DMP_INPROCESS"] = "1"
    from simulator.runner import SimulationRunner
    from simulator.config import INFECTION_MODEL, SIMULATION, DMP_API
    config = read_json(out / "config.json")
    pap = read_json(args.data / "pap.json")
    patterns = read_json(args.data / "patterns.json")
    validate(config, pap, patterns)
    runner = SimulationRunner(config, enable_logging=False, output_dir=str(out),
                              data_loader=lambda *a, **kw: (pap, patterns))
    save_json(out / "effective-config.json", {"simdata": runner.simdata, "infection_model": INFECTION_MODEL,
              "simulation_defaults": SIMULATION, "dmp": DMP_API})
    result = runner.run()
    if "error" in result:
        raise RuntimeError(result["error"])
    save_json(out / "result.json", result)
    if config["dmp_mode"] == "required" and result["metadata"]["timeline_source_counts"]["fallback"]:
        raise RuntimeError("Required DMP run used fallback timelines")
    summarize(out, pap, config["length"])


def run(args):
    import psutil
    if args.max_memory_mb < 128 or args.timeout_seconds <= 0:
        raise ValueError("Use memory budget >=128 MiB and positive timeout")
    engine = args.engine.resolve()
    if not (engine / "simulator" / "runner.py").is_file():
        raise ValueError(f"Simulation engine not found: {engine}")
    files = [args.config, args.data / "pap.json", args.data / "patterns.json"]
    for path in files:
        if path.stat().st_size > 32 * 1024**2:
            raise ValueError(f"{path} exceeds this JSON pilot workflow's 32 MiB/file limit")
    config, pap, patterns = map(read_json, files)
    validate(config, pap, patterns)
    del pap, patterns
    provenance = args.data / "provenance.json"
    if provenance.exists():
        files.append(provenance)
    if psutil.virtual_memory().available < (args.max_memory_mb + 512) * 1024**2:
        raise RuntimeError("Insufficient available RAM for requested budget plus 512 MiB reserve")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    save_json(out / "config.json", config)
    db = engine / "dmp" / "app" / "state_machine" / "state_machines.db"
    manifest = {"status": "running", "engine": str(engine), "engine_git": git_info(engine),
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "python": sys.version, "inputs": {str(p.resolve()): sha256(p) for p in files},
                "wrapper_sha256": sha256(__file__), "seed": config["random_seed"],
                "dmp_db_sha256": sha256(db) if db.exists() else None,
                "memory_limit_mib": args.max_memory_mb,
                "scope": "educational; uncalibrated", "network": "blocked in worker"}
    save_json(out / "manifest.json", manifest)
    (out / "environment.txt").write_text(subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], text=True), encoding="utf-8")
    command = [sys.executable, str(Path(__file__).resolve()), "_worker", "--engine", str(engine),
               "--data", str(args.data.resolve()), "--output", str(out)]
    start = time.monotonic()
    peak = 0
    reason = None
    with (out / "run.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        monitored = psutil.Process(proc.pid)
        try:
            while proc.poll() is None:
                try:
                    tree = [monitored] + monitored.children(recursive=True)
                    rss = 0
                    for process in tree:
                        try:
                            rss += process.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                    peak = max(peak, rss)
                except psutil.NoSuchProcess:
                    break
                if peak > args.max_memory_mb * 1024**2:
                    reason = "worker exceeded RAM budget"
                if time.monotonic() - start > args.timeout_seconds:
                    reason = "worker exceeded time budget"
                if psutil.virtual_memory().available < 512 * 1024**2:
                    reason = "system available RAM fell below 512 MiB reserve"
                if reason:
                    break
                time.sleep(0.1)
        finally:
            if proc.poll() is None:
                for child in monitored.children(recursive=True):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                proc.kill()
            proc.wait()
    manifest.update(status="complete" if proc.returncode == 0 and not reason else "failed",
                    elapsed_seconds=round(time.monotonic() - start, 3),
                    sampled_peak_rss_mib=round(peak / 1024**2, 2), exit_code=proc.returncode,
                    failure=reason)
    save_json(out / "manifest.json", manifest)
    if manifest["status"] != "complete":
        raise RuntimeError(f"Run failed ({reason or 'see run.log'}): {out}")
    print(f"Complete: {out} | {manifest['elapsed_seconds']} s | sampled peak {manifest['sampled_peak_rss_mib']} MiB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("fixture", help="Create an invented 40-person, three-day population")
    demo.add_argument("--output", type=Path, default=ROOT / "data" / "local" / "teaching")
    for name in ("run", "_worker"):
        p = sub.add_parser(name)
        p.add_argument("--engine", type=Path, default=ROOT.parent / "Simulation")
        p.add_argument("--data", type=Path, default=ROOT / "data" / "local" / "teaching")
        p.add_argument("--output", type=Path, required=True)
        if name == "run":
            p.add_argument("--config", type=Path, default=ROOT / "configs" / "teaching.json")
            p.add_argument("--max-memory-mb", type=int, default=1024)
            p.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        if args.command == "fixture":
            fixture(args.output)
        elif args.command == "run":
            run(args)
        else:
            worker(args)
    except Exception as exc:
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
