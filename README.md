1st round done: After experiments, codes improved

Code 3 -> Code 3_1

Code 4 -> Code 4_1

Code 5 -> Code 5_1 (Code 5_2 + Code 5_3)

2nd round:

(yt) Experiment 5_2 excludes the double option (4,5) that made errors (Line 437). Debugging: p as multiprocessing -> p_mp Then, we can perform (4,5) separately (Line 438).

(MNL) Experiment 1_2

(Sensitivity) Experiment 2_2 performs the heuristic (doubleSolution-Local Search) on the small-scale instances with logSum parameter = 0.5 for sensitivity analysis

(Warm) Experiment 6_2 warm starts Enhanced on large-scale instances for 5 hours.

3rd Round:

1_3_IAP_MNL_experiments_revised.py warm starts MILP-MNL

2_3_IAP_DoubleLS_Parallel_experiments.py produces heuristic solutions to large-scale instances for 2_4

2_3_IAP_NLCC_warm_facebook_sensitivity_experiments.py warm starts small instances (logSum = 0.5) comparing (Enhanced) with default (MILP-NL)

4th Round:

2_4_IAP_NLCC_warm_facebook_sensitivity_experiments.py can warm start with the heuristic solutions to large-scale instances, which are given by (2_3_IAP_DoubleLS_Parallel_experiments.py) in Round 3  

4_4_IAP_DoubleLS_Parallel_Gowalla.py tackles Gowalla again with the updated code if the computing resource is still available

The End
