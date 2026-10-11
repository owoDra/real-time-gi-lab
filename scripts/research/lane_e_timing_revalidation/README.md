# Lane E timing revalidation scripts

`run_e001.py` owns the prospective Issue #22 campaign.

- Validation is completed before timing.
- Each timed child process owns two independent Vulkan contexts/runtimes.
- Each timed sample contains 16 complete base/target transitions.
- 8 fresh-process blocks use frozen AB/BA and control/candidate position counterbalance.
- All raw rows are retained; no sample exclusion or favorable rerun is implemented.
- Interrupted campaigns may resume only inside the same incomplete artifact root.
