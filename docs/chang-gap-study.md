# Usages of Delineo, set against Chang et al. 2021

This note is the usage study for the local workflow. It maps published mobility-model experiments onto what Delineo can run, then reports one experiment that copies Chang et al.'s occupancy comparison and measures two things their model does not represent: individual stochastic replicates, and infections that occur at home after a denied visit.

The population is invented. It is not Chicago, not Barnsdall, and not a reproduction of the Nature paper. Disease timing is the engine's simplified timeline (`dmp_mode: off`), not a fitted natural history.

## What the papers did

Chang, Pierson, Koh, Gerardin, Redbird, Grusky, and Leskovec, [Mobility network models of COVID-19 explain inequities and inform reopening](https://doi.org/10.1038/s41586-020-2923-3), Nature 589, 82–87 (2021; online 10 November 2020), built an hourly census-block-group to point-of-interest network from SafeGraph and put a metapopulation SEIR model on it. Transmission at a venue scales with overlapping visits and inversely with floor area. They calibrated a few parameters to reported cases in ten metro areas. The results this study borrows are:

- A minority of venues account for most point-of-interest infections.
- Capping each venue at a fraction of its own peak occupancy (20% in the Chicago example) prevents more infections than deleting the same number of visits uniformly across hours. In Chicago the 20% cap cut predicted new infections by more than 80% while removing 42% of visits, because the cap only bites in crowded hours.
- Groups who keep visiting smaller, more crowded places have higher infection rates even when their visit counts match.

Their own FAQ says they did not test curfews, opening only some days, or people coming back at another time if they were turned away. Visits removed by a cap leave the mobility network; they are not reassigned to a household contact. Household transmission is a separate per-neighborhood base rate, not co-location of the people who stayed home. The model is a metapopulation: it does not track which person was turned away.

The KDD 2021 follow-up (Chang et al., [Supporting COVID-19 policy response with large-scale mobility-based modeling](https://cs.stanford.edu/~jure/pubs/covid-kdd21.pdf)) turns that model into a policy scanner over many mobility counterfactuals. The authors tell policymakers the data miss children and some venues, such as nursing homes, and that the model predicts the effect of a mobility change without saying which real lever produces that change.

Müller et al., PLOS One 2021 ([10.1371/journal.pone.0259037](https://doi.org/10.1371/journal.pone.0259037)), make the contrast explicit: Chang et al. have finer venue categories, but they do not simulate individual people. Müller et al. combine activity schedules, an agent model, and phone data. Aleta et al., Nature Human Behaviour 2020, study testing, tracing, and household quarantine, which Chang et al. cite and do not simulate. The 2020 ARIC mobility paper sends an agent home when a venue closes and finds that long school dwell times matter more than short restaurant visits.

## Where Delineo matches those uses

| Published use | Delineo counterpart in this workflow |
| --- | --- |
| Freeze a mobility trace, then compare policies on it | `pap.json` + hourly `patterns.json`, hashed in each run manifest |
| Occupancy cap versus a uniform cut with the same visit loss | Rewrite the hourly frames, then call `scripts/delineo_local.py` |
| Attribute infections to venues | `poi-incidence.csv` and `incidence.json` |
| Repeat stochastic draws | `random_seed` on an otherwise identical config |
| Area in the transmission term | `area_aware_ventilation` and each place's `area` |
| A non-mobility lever on the same trace | Intervention rows: `mask`, `vaccine`, `selfiso`, from a chosen hour |
| Close a named venue | `disabled_poi_ids`, which sends those visits home before the run |

The local runner is the wrong tool for Chang et al.'s full exercise: ten metros, 98 million people, and calibration to case time series. A Barnsdall export can support a smaller version of the same design once a frozen input bundle is in `data/local/`. This run uses a synthetic two-hall population so the mechanism is visible without that bundle.

## Gaps this run is built to fill

1. **Who stays home.** When Delineo closes a venue, or when this study deletes a visit to meet a cap, that person is in their household for that hour. Chang et al. drop the visit and do not add a household contact. Home versus venue incidence is therefore a Delineo output their reopening figure does not have.
2. **The same people, a new draw.** Rankings are compared on paired seeds with the mobility held fixed. A reversal or a tie is transmission noise, not a new mobility scenario.
3. **A policy that is not a mobility edit.** Half the population is masked from hour 24, in homes and in both halls. Chang et al.'s reopening section only changes visits.
4. **The density mechanism without a demographic claim.** Two groups of 40 have the same schedule. One meets in a 50 m² hall and one in a 1,000 m² hall. Any infection gap is the crowded-venue mechanism Chang et al. use to explain inequity. This population has no income or race attribute, so the result is not an equity prediction.

Not run here, though the engine supports them: ventilation-coefficient sweeps, DMP natural histories, self-isolation, and a real Barnsdall trace. The three-day DMP smoke test in `validation.md` produced no secondary infections, so this study stayed on the simplified timeline.

## Experiment

80 invented adults, 20 households of four, four simulated days (96 hourly frames). Hours 08:00, 12:00, and 17:00, every group is together in its hall (40 people). In the seven other daytime hours only 8 people are there. Nights are at home. One index case starts in each group (person `0` in the small hall's group, person `40` in the large hall's group). External introductions are off.

Arms, all on seeds 101–110:

| Arm | What changes | Venue person-hours |
| --- | --- | --- |
| Baseline | Recorded schedule | 1,408 |
| 20% peak cap | Each hall is held at 8 people, its peak of 40 times 0.2. Overflow stays home. Off-peak hours are already at 8, so they do not change. | 640 |
| Uniform, matched hours | Every daytime hour is thinned by the same fraction, lowest person ids kept, until 640 person-hours remain. Peaks stay at 18 instead of falling to 8. | 640 |
| Close the small hall | `disabled_poi_ids = ["2001"]`. Those visits go home. The large hall is unchanged. | 704 |
| Mask from hour 24 | Baseline mobility. From the start of day 2, people with intervention threshold ≤ 0.5 are masked at home and in both halls (41 of 80 people; the assignment does not depend on the epidemic seed). | 1,408 |

The cap and the uniform arm remove the same 768 person-hours. The closure removes 704, all of them from the small hall. Who keeps a visit is the lowest person id among people who would have attended. Both index cases are in that kept set for the cap and the uniform arm, so the policies do not work by deleting the index case.

Seed 100 was a discovery check only: the small hall was the hotspot, and the outbreak did not infect all 80 people. It is excluded from the numbers below. A zero-seed baseline with external force off stayed uninfected for all 96 hours.

Engine commit `693e98c1391ae5878bdd869f5b1314ea927d5dc3`, clean tree. Each run is one local-workflow invocation. Peak sampled RAM was about 150 MiB and each run took about 0.6 seconds.

## Results

Means over the ten evaluation seeds. Secondary infections exclude the two index cases. Home plus venue attribution matched that count in every run. No run died out.

| Arm | Secondary | At home | In a hall | Small hall | Large hall | Small-hall group | Large-hall group |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 43.4 | 25.0 | 18.4 | 17.8 | 0.6 | 38.7 | 4.7 |
| 20% peak cap | 7.7 | 6.1 | 1.6 | 1.4 | 0.2 | 4.5 | 3.2 |
| Uniform, matched hours | 16.4 | 11.1 | 5.3 | 5.2 | 0.1 | 13.9 | 2.5 |
| Close the small hall | 6.9 | 6.3 | 0.6 | 0.0 | 0.6 | 3.0 | 3.9 |
| Mask from hour 24 | 31.8 | 18.4 | 13.4 | 13.1 | 0.3 | 28.9 | 2.9 |

Paired differences are evaluation-seed minus treatment-seed, so a positive number is infections avoided by the treatment. Intervals are 95% bootstrap intervals of the ten-seed mean (10,000 resamples, seed 742). They describe Monte Carlo error for this fixed scenario, not uncertainty about real transmission parameters.

| Comparison | Infections avoided | 95% interval | Seeds with a strict drop |
| --- | --- | --- | --- |
| Cap versus baseline | 35.7 | 32.9 to 38.8 | 10 of 10 |
| Uniform versus baseline | 27.0 | 23.1 to 32.0 | 10 of 10 |
| Cap versus uniform | 8.7 | 5.6 to 11.6 | 9 of 10; seed 102 was a tie at 3 |
| Close small hall versus baseline | 36.5 | 35.3 to 38.1 | 10 of 10 |
| Mask versus baseline | 11.6 | 6.6 to 17.5 | 10 of 10 |

What this says about usage:

- **The Chang comparison is a Delineo usage.** With visit-hours matched, the cap avoided 8.7 more secondary infections than uniform thinning. The advantage sits in the crowded group (9.4 more infections avoided there, interval 6.3 to 12.3, 9 of 10 seeds). The spacious group does not benefit more from the cap than from uniform thinning (the paired difference there is −0.7, interval −1.4 to 0.0).
- **Superspreader venues are an individual-level output.** Under the baseline, 17.8 of 18.4 venue infections were in the 50 m² hall. Attendance was identical. The large hall is not a useful target.
- **Closing that hall is a targeted policy with an explicit household residual.** It avoided 36.5 infections while removing fewer person-hours than the cap (704 versus 768) and leaving the large hall open. Of the 6.9 infections that remained, 6.3 were at home. Sending the small-hall group home did not recreate the baseline outbreak. It also did not reliably protect the other group: their paired reduction has an interval that crosses zero (−0.3 to 2.3).
- **Households are where most baseline infections were counted** (25.0 of 43.4). That split is available because people have homes. It is the quantity Chang et al. cannot report from a denied visit. In this scenario the cap cut home infections as well as hall infections (18.9 and 16.8 avoided), because the home cases were downstream of the crowded hall rather than a rebound from staying home.
- **Density alone produced the group gap.** Baseline secondary infections were 38.7 in the small-hall group and 4.7 in the large-hall group. Under the cap those means are 4.5 and 3.2. This is the mechanism behind Chang et al.'s equity result, isolated from income, race, and differences in how much people travel.
- **Masking is a usable non-mobility arm, and it did less here.** Avoiding 11.6 infections, with a wider interval than the mobility arms, is the comparison their reopening figure does not contain. Masks started on day 2, after a day of unmasked mixing, and covered about half the population.

## What would overclaim

These runs do not estimate Chicago reopening, Barnsdall school closure, or the effect of a real 20% occupancy rule. The simplified timeline infects quickly; a reviewed DMP model could change the size of every contrast. People who lose a visit go home rather than to another hall or a later hour, which is the engine's closure rule and is one of the policies Chang et al. said they had not tested. Keeping the lowest person ids is a reproducible allocation, not a model of who queues. Ten seeds are enough to see that the cap ranking is stable in this scenario, not enough to pin a percentage reduction for a city.

## Rerun

From `delineo`, with the local environment installed:

```powershell
.\.venv\Scripts\python.exe scripts\chang_gap_study.py prepare
.\.venv\Scripts\python.exe scripts\chang_gap_study.py discover
.\.venv\Scripts\python.exe scripts\chang_gap_study.py zero
.\.venv\Scripts\python.exe scripts\chang_gap_study.py evaluate --seeds 101-110
.\.venv\Scripts\python.exe scripts\chang_gap_study.py analyze --seeds 101-110
```

`prepare` refuses to overwrite `data/local/chang-gap`. Evaluation skips runs whose manifest is already `complete`. Tables are in `results/chang-gap/`. Per-run manifests, state curves, and venue incidence are in `runs/chang-gap/`.
