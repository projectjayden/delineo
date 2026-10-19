"""Aggregate completed preliminary runs; paired bootstrap describes seed variability only."""
from pathlib import Path
import itertools
import json
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
RUNS=ROOT/'runs/preliminary'
OUT=ROOT/'results/preliminary'
ARMS=['baseline','cap20','uniform_matched','schools','baseline_lowvent','schools_lowvent','baseline_highvent','schools_highvent']
LABELS=['Baseline','20% peak cap','Uniform, matched hours','Two schools closed','Baseline / low ventilation','Schools closed / low ventilation','Baseline / high ventilation','Schools closed / high ventilation']


def interval(values):
    a=np.asarray(values,dtype=float)
    rng=np.random.default_rng(742)
    boot=rng.choice(a,size=(10000,len(a)),replace=True).mean(1)
    return float(a.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975)),float(a.std(ddof=1)/np.sqrt(len(a)))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]; poi={}; curves={}
    for seed in range(100,110):
        for arm in ARMS:
            folder=RUNS/f'{arm}-{seed}'
            manifest=json.loads((folder/'manifest.json').read_text())
            if manifest['status']!='complete':raise ValueError(folder)
            s=json.loads((folder/'summary.json').read_text())
            assert s['metadata']['timeline_source_counts']['fallback']==0
            assert s['home']+s['poi']==s['secondary']
            rows.append({k:v for k,v in s.items() if k!='metadata'}|{'seconds':manifest['seconds'],'peak_mib':manifest['peak_mib']})
            poi[arm,seed]=pd.read_csv(folder/'poi.csv',dtype={'place_id':str})
            curves[arm,seed]=pd.read_csv(folder/'hourly.csv')
    df=pd.DataFrame(rows);df.to_csv(OUT/'runs.csv',index=False)
    means=df.groupby('arm')[['secondary','home','poi','peak_infectious','seconds','peak_mib']].agg(['mean','std','min','max'])
    means.to_csv(OUT/'arm-summary.csv')
    pairs=[('cap20','baseline'),('uniform_matched','baseline'),('cap20','uniform_matched'),
           ('schools','baseline'),('schools_lowvent','baseline_lowvent'),('schools_highvent','baseline_highvent')]
    effects=[]
    for treatment,reference in pairs:
        a=df[df.arm==reference].set_index('seed');b=df[df.arm==treatment].set_index('seed')
        for metric in ['secondary','home','poi']:
            delta=a[metric]-b[metric]
            mean,lo,hi,se=interval(delta)
            effects.append(dict(treatment=treatment,reference=reference,metric=metric,n=len(delta),
                                mean_avoided=mean,ci_low=lo,ci_high=hi,monte_carlo_se=se,
                                positive_seeds=int((delta>0).sum())))
    eff=pd.DataFrame(effects);eff.to_csv(OUT/'paired-effects.csv',index=False)
    rank_rows=[];top_sets={};concentration=[]
    for seed in range(100,110):
        p=poi['baseline',seed].sort_values(['infections','place_id'],ascending=[False,True])
        cutoff=p['infections'].nlargest(10).min()
        top_sets[seed]=set(p.loc[(p.infections>=cutoff)&(p.infections>0),'place_id'])
        concentration.append({'seed':seed,'top10percent_share':p.infections.nlargest(int(np.ceil(len(p)*.1))).sum()/p.infections.sum(),
                              'positive_venues':int((p.infections>0).sum())})
        ranks=p.infections.rank(ascending=False,method='min')
        for idx,row in p.iterrows():
            rank_rows.append({'seed':seed,'place_id':row.place_id,'label':row.label,'infections':row.infections,'rank':ranks.loc[idx]})
    ranks=pd.DataFrame(rank_rows);ranks.to_csv(OUT/'baseline-venue-ranks.csv',index=False)
    conc=pd.DataFrame(concentration);conc.to_csv(OUT/'concentration.csv',index=False)
    overlap=[]
    for a,b in itertools.combinations(top_sets,2):
        overlap.append({'seed_a':a,'seed_b':b,'jaccard':len(top_sets[a]&top_sets[b])/len(top_sets[a]|top_sets[b])})
    pd.DataFrame(overlap).to_csv(OUT/'top10-overlap.csv',index=False)
    # Descriptive category concentrations, not causal reopening effects.
    cat=pd.concat([p.assign(seed=s) for (a,s),p in poi.items() if a=='baseline'])
    cat.groupby(['seed','category']).infections.sum().reset_index().to_csv(OUT/'category-incidence.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(9,5))
    for _,r in df[df.arm.isin(ARMS[:4])].groupby('seed'):
        r=r.set_index('arm').reindex(ARMS[:4]);ax.plot(range(4),r.secondary,color='#92a7b6',alpha=.55,lw=1)
    ax.scatter([ARMS.index(a) for a in df[df.arm.isin(ARMS[:4])].arm],df[df.arm.isin(ARMS[:4])].secondary,color='#176a8c',s=20)
    ax.set_xticks(range(4),LABELS[:4]);ax.set_ylabel('Secondary infections by day 28');ax.set_title('Full Barnsdall simulation: 10 paired seeds\nUncalibrated preliminary experiment')
    fig.tight_layout();fig.savefig(OUT/'policy-comparison.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4.6))
    m=df.groupby('arm')[['home','poi']].mean().reindex(ARMS[:4])
    axs[0].bar(range(4),m.home,label='Home',color='#176a8c');axs[0].bar(range(4),m.poi,bottom=m.home,label='Venue',color='#e7a349')
    axs[0].set_xticks(range(4),['Base','Cap','Uniform','Schools']);axs[0].set_ylabel('Mean attributed infections');axs[0].legend();axs[0].set_title('Where infections occur')
    for arm,label in [('baseline','Baseline'),('cap20','20% cap'),('uniform_matched','Uniform'),('schools','Schools closed')]:
        stack=np.array([curves[arm,s].ever_infected.to_numpy()-20 for s in range(100,110)])
        days=curves[arm,100].minute/1440
        axs[1].plot(days,stack.mean(0),label=label);axs[1].fill_between(days,stack.min(0),stack.max(0),alpha=.10)
    axs[1].set(xlabel='Simulated day',ylabel='Secondary infections',title='Mean curves; bands show seed range');axs[1].legend()
    fig.tight_layout();fig.savefig(OUT/'locations-and-curves.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for i,(a,b,label) in enumerate([('schools_lowvent','baseline_lowvent','4.5'),('schools','baseline','9 (default)'),('schools_highvent','baseline_highvent','18')]):
        r=eff[(eff.treatment==a)&(eff.reference==b)&(eff.metric=='secondary')].iloc[0]
        ax.errorbar(i,r.mean_avoided,yerr=[[r.mean_avoided-r.ci_low],[r.ci_high-r.mean_avoided]],fmt='o',capsize=5,color='#176a8c')
    ax.axhline(0,color='gray',lw=.8);ax.set_xticks(range(3),['4.5','9 (default)','18']);ax.set(xlabel='Venue ventilation coefficient',ylabel='Secondary infections avoided by closing two schools',title='Sensitivity to an uncalibrated transmission assumption\n95% paired-seed bootstrap intervals')
    fig.tight_layout();fig.savefig(OUT/'school-sensitivity.png',dpi=180);plt.close(fig)
    key=eff[eff.metric=='secondary']
    print(key.to_string(index=False));print('Concentration',conc.top10percent_share.mean());print('Top10 mean Jaccard',np.mean([r['jaccard'] for r in overlap]));print('Max RAM',df.peak_mib.max());print('total seconds',df.seconds.sum())
    stats={'effects':key.to_dict('records'),'means':df.groupby('arm')[['secondary','home','poi']].mean().to_dict('index'),
           'concentration_mean':float(conc.top10percent_share.mean()),'jaccard_mean':float(np.mean([r['jaccard'] for r in overlap])),
           'max_peak_mib':float(df.peak_mib.max()),'total_worker_seconds':float(df.seconds.sum())}
    (OUT/'statistics.json').write_text(json.dumps(stats,indent=2))


if __name__=='__main__':main()
