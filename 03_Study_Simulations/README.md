# Objective 2 tutorial: exploratory monkey PK study simulations

This folder contains the tutorial workflow for using the a priori monkey PBPK
models from `02_APriori_PBPK_Workflow` to explore smaller PK study designs.

Run `Scripts/Step1_APriori_Monkey_Study_Design_Simulations.qmd`. This combined
Step 1 script loads the completed a priori Golimumab PBPK configuration,
generates the 50-animal monkey population defined in `Populations.xlsx`, and
draws 100 sets of six molecule-specific PBPK inputs at 30% and 50% CV. Each
parameter set is crossed with every physiological monkey, producing 5,000
profiles per variability level and dose and 50,000 profiles across 0.1, 1, 3,
10, and 30 mg/kg. It then resamples candidate studies with 2, 3, or 5 dose
groups and 2, 3, or 6 animals per group and plots the median and 5th-95th
percentiles of replicate study-mean concentration profiles at one fixed sparse
sampling schedule.

Step 1 writes a compact R data object containing the simulated profiles,
parameter-draw record, physiological population, and cross-index, plus figures
and plotting tables under `SimsOutputs`.
The rendered HTML embeds the explanatory text, settings, checks, and displayed
results. Code is folded by default and can be expanded by readers.

Step 1 intentionally stops before calculating PK endpoints or comparing a
candidate study with a true reference. Those calculations are introduced in
`Scripts/Step2_Golimumab_Rich_Reference_Fold_Error.qmd`.

Step 2 treats the nominal a priori Golimumab model as the true model and
simulates a rich typical-subject reference at 0.1, 1, 3, 10, and 30 mg/kg. It
calculates AUC0-28d, Cmax, and terminal clearance from the rich profiles and
from Step 1's sparse profiles, resamples the 2-, 3-, and 5-dose reduced-study
designs, and plots the resulting standard fold-error distributions for 2, 3,
and 6 animals per dose under 30% and 50% input variability.
