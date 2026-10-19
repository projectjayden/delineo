# From a working simulation to a paper

## First candidate study

**Question:** How robust are venue-targeted intervention rankings to stochastic seeding, household displacement, and occupancy-related transmission assumptions in Delineo?

This turns the existing two-school hotspot exercise into a reproducible model study. It could support a methods or educational modeling paper. Novelty needs a focused literature review; it is not established by this plan.

## Literature and open-source comparisons

The likely requested reference is Chang et al., [Mobility network models of COVID-19 explain inequities and inform reopening](https://doi.org/10.1038/s41586-020-2923-3), Nature 589, 82–87 (2021; online November 2020). Its community-to-venue mobility approach motivates occupancy-policy comparisons. Delineo uses individual movement and a different transmission implementation, so this is inspiration rather than reproduction. Borrow held-out checks, uncertainty across plausible parameters, and comparisons on fixed mobility inputs.

| Model | Role | Decision |
| --- | --- | --- |
| Existing Delineo Simulation | Main engine and project contribution | Executed locally in this pass |
| [Stanford covid-mobility](https://github.com/snap-stanford/covid-mobility) | Closest code for the likely Nature reference | Study equations/design first; its documented full pipeline used large server resources and source mobility datasets |
| [Covasim](https://github.com/starsimhub/covasim) | Possible independent intervention comparator | Later small pilot in a separate environment; current repository notes integration with Starsim, so pin the chosen API/version |
| [OpenABM-Covid19](https://github.com/BDI-pathogens/OpenABM-Covid19) | Alternative contact-network comparator | Add only when a particular mechanism comparison justifies it |

No second epidemic model was installed: the existing engine solves the immediate local-execution need. Cross-model agreement would test qualitative robustness, not establish empirical validity.

## Experiment design

1. Freeze one coherent Barnsdall population/mobility bundle, horizon, engine revision and DMP database. Identify focal schools from source records and stable place identifiers, not numeric IDs copied across exports.
2. Use discovery seeds to choose hotspot targets, then evaluate policies on fresh seeds. Selecting and evaluating on the same realized outbreaks biases targeting comparisons.
3. Arms: A baseline; B close school 1; C close school 2; D close both; E a prespecified comparison policy. Current full-run closures are supported. Timed targeted closures and venue-specific masking remain future extensions.
4. Compare costs as well as outcomes. Two closures and whole-community lockdown have different burdens. Report displaced visits/person-hours. Tune any matched-cost comparator using discovery mobility, then freeze it before outcome evaluation. Derive targeted-closure displacement from input movement: general redirect counters may not count disabled-POI preprocessing.
5. Start with ten paired seeds to estimate variance/runtime. Preserve initial IDs within each pair. Study alternative seed households separately; distinguish stochastic variability, parameter uncertainty and input uncertainty.
6. Primary outcome: total secondary infections over a common horizon. Report paired absolute differences, unconditional means/medians/quantiles, extinction frequency, and home/POI incidence. Percentage reductions are undefined when baseline is zero.
7. Prespecify a Monte Carlo precision target and resource ceiling. Expand replication based on pilot paired variance. Use paired-seed bootstrap intervals; account for correlated population/mobility realizations when applicable. Report Monte Carlo error separately from model uncertainty.
8. Sensitivity: area-aware ventilation on/off, justified coefficient ranges, seed timing and location. Introduce external force-of-infection only with explicit catchment/prevalence assumptions. The default ventilation coefficient is not an empirically fitted value.
9. Deliver paired-effect plots, household-displacement plots, held-out hotspot rank stability, and a sensitivity surface showing policy-order reversals. Retain zero outbreaks and unfavorable policy effects.

## Potential contributions and evidence

| Contribution | Evidence needed | Status |
| --- | --- | --- |
| Website-free reproducible Delineo workflow | Versioned configs/inputs, provenance, repeatability | Initial wrapper implemented |
| Robust school-targeting conclusions | Held-out seeds, paired contrasts, validated IDs | Design ready; actual bundle needed |
| Household displacement changes rankings | Attribution checks and explicit movement assumptions | Engine capability exists; study not run |
| Ranking sensitivity to occupancy/ventilation | Justified ranges and factorial analysis | Engine switches exist; study not run |
| Interoperability benchmark | Matched populations/interventions/metrics in another model | Future work |

A wrapper alone is not a new disease model. A carefully evaluated use case, reproducibility contribution or robustness result is a more defensible near-term paper direction.

## Calibration and validation

For empirical claims, choose geography, historical period, observations and mobility window together. Link infections to observed cases/hospitalizations through explicit ascertainment and delay assumptions. Fit a small identifiable parameter set; several transmission/mobility knobs can fit the same aggregate curve. Hold out later weeks or another community, compare against a simple baseline, and report predictive intervals and residuals.

Audit natural-history units and demographic matching before calibrating transmission. The three-day DMP smoke test completed with zero fallback but no secondary infections; it does not validate duration distributions or sustained epidemic behavior. A synthetic methods study can instead focus on constructed scenarios, analytical/software checks and sensitivity, clearly stating its scope.

## Paper package and next milestone

Prepare: question/related work; mechanism and revision; input provenance; prespecified design; calibration/validation where relevant; results with uncertainty; sensitivity/limitations; reproducibility appendix containing commands and hashes.

Next: obtain a frozen local Barnsdall input export and audit DMP timing. Reproduce one baseline and one targeted closure before launching a large ensemble. No publication-quality result or guaranteed novelty is claimed yet.
