# N010 Amendment 4 — measure known-work cost for dose sizing

Prospective after diagnostic sizing result 027, before any accepted timing
blocks. Result 027 and its failures remain unchanged. Under concurrent CPU
reference work, many full Renderer increments from 256/1024 integer rounds
were negative or below background variation, so that sizing plan is not
eligible for accepted acquisition.

Add inner GPU timestamps immediately around the neutral-work stage already
inside the full Renderer interval. Dose sizing keeps the exact nine-sample
schedule [0,256,1024] repeated three times. Use the median inner-stage cost at
each dose for incremental slope, and full Renderer median at zero for the
20% target numerator. Positive slopes at both doses are still required. Freeze
ceil(0.20 * full_zero_median / median(inner_increment/dose)) and binary/source
identities before accepted blocks. Do not subtract inner time from complete
Renderer measurements. It is a dose-sizing diagnostic only.

All full Renderer control/effect acceptance gates, eight process blocks,
warmup/measured pairs, counterbalancing and no-exclusion/no-retry rules remain
unchanged. Calibration acceptance still runs after CPU/GPU acquisition is quiet.
No power/clock setting is changed.
