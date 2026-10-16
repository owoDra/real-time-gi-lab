# Prospective IDE visibility and same-device graphics-accounting diagnostic

Date: 2026-10-16 JST. Parent checkpoint: `4571e0f`.
Registered after post-hoc 173 and read-only window/version queries, before any
window movement or visibility-intervention data. Full GPU calibration 169 is
still running and its environment must remain unchanged until actual completion.

## Question and exact scope

Result 173 observes IDE graphics accounting on the same AMD device during
three live-calibration intervals. This does not prove the cause of timing
noise. Test whether moving that IDE window to an undisplayed special workspace,
without terminating or pausing any application, substantially suppresses that
same client's accounted graphics work. Restore the original workspace/focus.
This is an operational environment diagnostic, not Renderer calibration,
quality validation, causal proof for earlier failures or accepted GI timing.

Installed Hyprland is 0.55.2, source commit
`39d7e209c79d451efab1b21151d5938289da838d`. Official versioned sources confirm
legacy `movetoworkspacesilent` takes `workspace,window`, resolves the window
selector and passes a silent workspace move to the action implementation:

- https://raw.githubusercontent.com/hyprwm/Hyprland/v0.55.2/src/config/legacy/DispatcherTranslator.cpp
- https://wiki.hypr.land/0.54.0/Configuring/Dispatchers/

No DPMS, idle, clock, governor, power, driver or application-preference changes.
No signals are sent to the IDE/GPU process. No compositor or application exits.

## One fixed acquisition and guards

Use result `174-ide-visibility-accounting-diagnostic.json` and fresh work
`out/research/n010-comparison-readiness/ide-visibility-diagnostic-v1`.
Refuse existing paths. Require no research worker and actual complete 169
with all sixteen boundaries and all eight blocks each, preserving every FAIL.
No waiting/restart controller or automatic retry. The diagnostic may precede
plan-050 CPU feasibility 172; never overlap any scientific acquisition.

Pin 173's client identity: AMD PCI `0000:c5:00.0`, client 2946, GPU PID 516315
start ticks 8673949. Require its IDE parent PID 516230 with unchanged launch
identity throughout. Select exactly one mapped, unpinned, non-fullscreen,
non-floating, ungrouped class-`orca` window belonging to that parent, initially
on a displayed positive-numbered workspace. Refuse ambiguity or a preexisting
`special:n010-calibration-isolation` workspace. Record installed version,
PID/start identities, selected window metadata, original workspace/focus,
every IPC command and all return statuses. Do not retain window titles.

Fixed A/B/A phases: visible-before, hidden, visible-after. Before each phase,
settle two seconds. Capture four cumulative per-client DRM-engine snapshots
separated by exactly five requested seconds, retaining actual monotonic scan
times, all deltas and every interval. Read only one matching FD per snapshot;
never sum duplicates. Require the same client and PID/start throughout,
nonnegative counters, expected workspace/visibility at each snapshot and
unchanged displayed workspaces. Move only the selected window with
`movetoworkspacesilent special:n010-calibration-isolation,address:<window>`;
return it to its original numbered workspace before the last visible phase.
Restore original focus where it still identifies the original window.

Always attempt restoration on normal completion, exceptions and handled
SIGINT/SIGTERM; retain restoration commands and verify original workspace,
geometry/layout attributes and focus. A refusal, missing counter, changed
identity, intervention or restoration failure is a retained diagnostic failure,
not grounds for a retry or for modifying 169. Save partials as they are acquired.

Implementation detail registered before any intervention: restoration waits
two fixed seconds outside every accounting phase before comparing exact window
geometry, allowing the compositor's workspace animation to finish. This is
separate from each phase's fixed two-second settle; neither interval contributes
to accounting deltas. Record both GPU and IDE-parent PID/start identities.

## Fixed interpretation

For each phase, compute total accounted graphics-nanosecond delta divided by
total actual monotonic scan-start interval. This is an accounting rate, not
instantaneous utilization, physical GPU busy percentage or per-query overlap.
Report every interval and all three phase rates. Classify local suppression
only if BOTH visible rates are >=10,000,000 accounted ns/elapsed second,
hidden rate <=1,000,000 ns/second AND <=0.05 times the smaller visible rate,
all identities/phase checks pass and restoration is verified. Otherwise the
intervention has not demonstrated the registered suppression; do not tune the
cutoffs or retry. These cutoffs belong solely to this new operational diagnostic,
not to any original N010 calibration/quality/reference decision.

A positive result would justify considering a separate prospective acquisition
under this recorded visibility policy, with its own all-boundary measurements
and unchanged original timing gates. It does not pass those gates, guarantee
future desktop quiescence, accept earlier timing, or exclude failures.
A future full-calibration repair must be specified before its GPU data.

All 24 eligible references, full quality/memory pilots and final six-gate 047
remain required. Direct relative-error-1.0 pixels remain UNRESOLVED / 未解決
and included. No N011, CUDA, Actions, active Renderer promotion or historical
N001–N009 changes. Tests are not part of this observational diagnostic.
