"""Bounded, sequential preliminary experiments using the real zone-70 export.

The engine is unchanged. Only input movement and aggregate output collection differ.
"""
import argparse
import csv
import gzip
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT.parent / 'Simulation'
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ROOT / 'scripts'))
from delineo_local import read_json, save_json, sha256, git_info
from simulator.patterns_codec import decode_patterns_binary, BinaryPatterns

DATA = ROOT / 'data/local/barnsdall-study'
RUNS = ROOT / 'runs/preliminary'


def prepare():
    DATA.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'data/local/source-audit/zone70.bulk'
    with source.open('rb') as f:
        pap = json.loads(f.readline())
        bp = decode_patterns_binary(f.read())
    keep = np.array(bp.ts_minutes) <= 40320
    matrix = bp.loc_matrix[keep].copy()
    times = np.array(bp.ts_minutes)[keep].tolist()
    assert times == list(range(60, 40321, 60))
    assert len(bp.pids) == len(set(bp.pids)) and set(bp.pids) == set(pap['people'])
    assert set(bp.loc_ids[:bp.n_homes]) == set(pap['homes'])
    assert set(bp.loc_ids[bp.n_homes:]) == set(pap['places'])
    assert matrix.min() >= 0 and matrix.max() < len(bp.loc_ids)
    home_lookup = {pid: i for i, pid in enumerate(bp.loc_ids[:bp.n_homes])}
    homes = np.array([home_lookup[str(pap['people'][pid]['home'])] for pid in bp.pids], dtype=matrix.dtype)
    peaks = np.zeros(len(bp.loc_ids), dtype=int)
    visits = np.zeros(len(bp.loc_ids), dtype=np.int64)
    for row in matrix:
        counts = np.bincount(row, minlength=len(peaks))
        peaks = np.maximum(peaks, counts)
        visits += counts
    # Paper-inspired 20% of observed peak occupancy, not engineering capacities.
    caps = np.floor(0.2 * peaks).astype(int)
    capped = matrix.copy()
    uniform = matrix.copy()
    rng = np.random.default_rng(90210)
    uniform_rng = np.random.default_rng(90211)
    denied = []
    for t, row in enumerate(matrix):
        away = np.flatnonzero(row >= bp.n_homes)
        shuffled = rng.permutation(away)
        order = np.argsort(row[shuffled], kind='stable')
        cols = shuffled[order]
        locs = row[cols]
        starts = np.r_[0, np.flatnonzero(np.diff(locs)) + 1] if len(locs) else []
        rejected = []
        for start, end in zip(starts, list(starts[1:]) + [len(cols)]):
            rejected.extend(cols[start + caps[locs[start]]:end])
        rejected = np.asarray(rejected, dtype=int)
        capped[t, rejected] = homes[rejected]
        chosen = uniform_rng.choice(away, size=len(rejected), replace=False)
        uniform[t, chosen] = homes[chosen]
        denied.append(len(rejected))
    assert np.array_equal((capped >= bp.n_homes).sum(1), (uniform >= bp.n_homes).sum(1))
    save_json(DATA / 'pap.json', pap)
    save_json(DATA / 'tables.json', {'pids': bp.pids, 'loc_ids': bp.loc_ids,
                                   'n_homes': bp.n_homes, 'ts_minutes': times})
    for name, m in [('baseline', matrix), ('cap20', capped), ('uniform_matched', uniform)]:
        np.save(DATA / f'{name}.npy', m)
    school_ids = [pid for pid, place in pap['places'].items()
                  if place.get('label') in ['Avant Public School', 'St John Catholic School']]
    assert len(school_ids) == 2, school_ids
    seed_ids = np.random.default_rng(871).choice(bp.pids, 20, replace=False).tolist()
    config = read_json(ROOT / 'configs/teaching-dmp.json')
    config.update(czone_id=70, length=40320, initial_infected_count=20,
                  initial_infected_ids=seed_ids, model_path_by_variant={'Delta':'variant.Delta.general'})
    save_json(DATA / 'config.json', config)
    with (DATA / 'occupancy.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['place_id','label','category','peak_occupancy','person_hours','cap20'])
        for i in range(bp.n_homes,len(bp.loc_ids)):
            p=pap['places'][bp.loc_ids[i]]
            w.writerow([bp.loc_ids[i],p.get('label'),p.get('top_category'),peaks[i],visits[i],caps[i]])
    save_json(DATA / 'provenance.json', {'source_url':'https://covidmod.isi.jhu.edu/api/patterns/70?length=40320',
        'source_sha256':sha256(source),'population':len(bp.pids),'homes':bp.n_homes,
        'places':len(pap['places']),'source_frames':len(bp.ts_minutes),'used_frames':len(times),
        'hours_removed_cap':int(sum(denied)),'baseline_poi_person_hours':int((matrix>=bp.n_homes).sum()),
        'school_ids':school_ids,'policy_mobility_seeds':[90210,90211],
        'note':'Full current zone export, synthetic agents/generated mobility. Not historical run-187 exact reproduction. Server returned 720 hours; explicitly truncated to 672.'})
    print('Prepared full population',len(bp.pids),'school IDs',school_ids,flush=True)


def worker(arm, seed, out):
    def blocked(*a, **kw):
        raise RuntimeError('Study worker is offline')
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    os.environ['DELINEO_SOA_ENGINE']='1'
    os.environ['DMP_INPROCESS']='1'
    from simulator.runner import SimulationRunner
    pap=read_json(DATA/'pap.json'); tables=read_json(DATA/'tables.json')
    cfg=read_json(DATA/'config.json'); cfg['random_seed']=seed
    movement=arm if arm in ['cap20','uniform_matched'] else 'baseline'
    if arm.startswith('schools'):
        cfg['disabled_poi_ids']=read_json(DATA/'provenance.json')['school_ids']
    if arm.endswith('lowvent'): cfg['ventilation_coeff']=4.5
    if arm.endswith('highvent'): cfg['ventilation_coeff']=18.0
    bp=BinaryPatterns(np.load(DATA/f'{movement}.npy'), **tables)
    save_json(out/'config.json',cfg)
    rows=[]
    class CompactRunner(SimulationRunner):
        def write_snapshot(self, context, ts):
            store=context.simulator.membership
            counts=store.incidence_snapshot()
            ever=int(store.infected_mask.sum())
            home=int(counts['hinc']); poi=int(sum(counts['pinc']))
            if home+poi+len(context.initial_infected_ids)!=ever:
                raise AssertionError('Incidence accounting failed')
            rows.append({'minute':int(ts),'ever_infected':ever,'home':home,'poi':poi,
                         'infectious':int(((store.snap_state & 2)>0).sum())})
            self.last_context=context
    runner=CompactRunner(cfg,enable_logging=False,output_dir=str(out),data_loader=lambda *a,**kw:(pap,bp))
    result=runner.run()
    if 'error' in result: raise RuntimeError(result['error'])
    assert result['metadata']['timeline_source_counts']['fallback']==0
    assert len(rows)==672 and rows[-1]['minute']==40320
    with (out/'hourly.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    store=runner.last_context.simulator.membership
    with (out/'poi.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['place_id','label','category','infections'])
        for i,(pid,is_home) in enumerate(store.idx_to_loc):
            if not is_home:
                p=pap['places'][pid];w.writerow([pid,p.get('label'),p.get('top_category'),int(store.incidence[i])])
    summary=dict(rows[-1],arm=arm,seed=seed,secondary=rows[-1]['ever_infected']-20,
                 peak_infectious=max(x['infectious'] for x in rows),metadata=result['metadata'])
    save_json(out/'summary.json',summary)


def run(arm,seed):
    out=RUNS/f'{arm}-{seed}'
    if out.exists():
        if (out/'manifest.json').exists() and read_json(out/'manifest.json')['status']=='complete':
            return
        raise RuntimeError(f'Incomplete existing run: {out}')
    if psutil.virtual_memory().available<3*1024**3: raise RuntimeError('Need 3 GiB available RAM')
    out.mkdir(parents=True)
    manifest={'status':'running','engine':git_info(ENGINE),'arm':arm,'seed':seed,
              'script_sha256':sha256(__file__),'inputs':{p.name:sha256(p) for p in DATA.iterdir() if p.is_file()},
              'dmp_sha256':sha256(ENGINE/'dmp/app/state_machine/state_machines.db')}
    save_json(out/'manifest.json',manifest)
    start=time.monotonic();peak=0;reason=None
    with (out/'run.log').open('w') as log:
        proc=subprocess.Popen([sys.executable,__file__,'worker','--arm',arm,'--seed',str(seed)],stdout=log,stderr=log)
        monitor=psutil.Process(proc.pid)
        try:
            while proc.poll() is None:
                processes=[monitor]+monitor.children(recursive=True)
                mem=0
                for p in processes:
                    try: mem+=p.memory_info().rss
                    except psutil.NoSuchProcess: pass
                peak=max(peak,mem)
                if mem>2*1024**3: reason='2 GiB RAM budget exceeded'
                if time.monotonic()-start>600: reason='600 s timeout'
                if psutil.virtual_memory().available<768*1024**2: reason='system RAM reserve'
                if reason: break
                time.sleep(.2)
        finally:
            if proc.poll() is None:
                for p in monitor.children(recursive=True):
                    try:p.kill()
                    except psutil.NoSuchProcess:pass
                proc.kill()
            proc.wait()
    manifest.update(status='complete' if proc.returncode==0 and not reason else 'failed',
                    seconds=round(time.monotonic()-start,2),peak_mib=round(peak/1024**2,1),error=reason)
    save_json(out/'manifest.json',manifest)
    if manifest['status']!='complete': raise RuntimeError(f'Run failed: {out}; {reason}')
    print(arm,seed,manifest['seconds'],'s',manifest['peak_mib'],'MiB',read_json(out/'summary.json')['secondary'],'secondary',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run','worker','suite'])
    p.add_argument('--arm',default='baseline');p.add_argument('--seed',type=int,default=100)
    p.add_argument('--replicates',type=int,default=10)
    a=p.parse_args()
    if a.command=='prepare':prepare()
    elif a.command=='worker':worker(a.arm,a.seed,RUNS/f'{a.arm}-{a.seed}')
    elif a.command=='run':run(a.arm,a.seed)
    else:
        for seed in range(100,100+a.replicates):
            for arm in ['baseline','cap20','uniform_matched','schools','baseline_lowvent','schools_lowvent','baseline_highvent','schools_highvent']:
                run(arm,seed)
