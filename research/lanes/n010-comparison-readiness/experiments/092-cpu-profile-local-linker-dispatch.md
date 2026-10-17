# N010 original CPU profile: local linker dispatch amendment

Date:2026-10-17 JST. Parent:aab5ca6. Before any profiling acquisition.
091 driver stopped at `perf --version`: inherited LD_LIBRARY_PATH selected
libcurl without CURL_OPENSSL_4, required by perf's libdebuginfod. Work directory
is empty, no native/profile ran. Preserve post-hoc bootstrap receipt239 and the
sealed091 driver. `env -u LD_LIBRARY_PATH perf --version` reports7.2.10.
Original224 native contains explicit Nix glibc/GCC RUNPATHs (readelf inspection).

New strict-inverse wrapper changes only work/output/plan identities, the
perf-version child environment, and the profile/analysis child environment:
remove LD_LIBRARY_PATH locally, retain DEBUGINFOD_URLS='' and PERF_PAGER=cat.
The Python controller retains the library environment needed by NumPy.
No system/app environment changes. All091 scenes/counts/seeds/bytes/resource/
profile/stop requirements remain exact. No actual profile was retried.

Work:out/research/n010-comparison-readiness/original-all-split-cpu-profile-local-linker-v1
Result:results/240-original-all-split-cpu-profile-local-linker.json
Driver:scripts/research/n010_reference_sampling/profile_original_cpu_local_linker.py
Permission or collection failure remains a stop, with no settings change.
Original gates11/17physical,16/24references,timing208FAIL,direct1.0UNRESOLVED
included,N010 NOT_READY. Tests NOT RUN.
