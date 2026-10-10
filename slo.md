---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.99
      threshold_seconds: 0.2
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk",http_route="/kb/search",le="0.2"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
    - {alert: KbSearchLatencyBurnFast, sli: latency, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchLatencyBurnSlow, sli: latency, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 100% - Codex measured the login profile and derived the objectives, budgets and boundaries. -->

# SLO for knowledge-base search

## Evidence and scope

The baseline `./itsmlab.sh load 3` on 2026-10-10, checker 0.8.1,
login `konradxxx777`, scheduled 2,400 requests at 40/s on 64 connections.
p50 was 24.8 ms, p95 47.4 ms, p99 124.8 ms, p99.9 154.5 ms and maximum
188.8 ms. Direct upstream p99 was 118.3 ms. There were 2,393 HTTP 200
and 7 HTTP 502 responses (0.292% failures).
These are a finite sample, not a promise that the next sample is identical.

Only matched `/kb/search` traffic counts. Availability means non-5xx responses,
including client errors: a rejected invalid query is functioning validation,
not an unavailable service. Latency includes all statuses, so fast failures
cannot be hidden by excluding them. The two SLIs must be interpreted together;
being fast does not excuse failing.

## Availability

99% over a rolling 30 days allows 1% bad requests. The time-equivalent budget
is 0.01 × 30 × 24 × 60 = 432 minutes, not a claim that exactly 432 contiguous
minutes of outage are acceptable at every traffic rate. The observed upstream
failure rate was 0.292%, leaving headroom while still detecting a sustained
regression. 99.9% would already be violated by this dependency profile.
No retry is used: it would violate the contract, multiply dependency load and
hide the original failure distribution.

## Latency

99% of requests should finish within 0.2 seconds over 30 days, with the same
1% / 432-minute budget. The 200 ms threshold is an actual histogram boundary,
about 60% above the measured p99 and above the observed slow mode around
100–150 ms. It is below the 1 s cap used by the later canary lab.
The objective accommodates occasional tail outliers without accepting a
large slow population. This baseline met it, but a 60-second sample is not a
30-day SLO assessment. We must continue monitoring both SLIs.

## Paging and economic tradeoff

| Alerts (Errors / Latency) | Burn | Windows | Budget consumed over the long window | Action |
|---|---:|---|---:|---|
| BurnFast | 14.4 | 1h AND 5m | 14.4 × 1 / 720 = 2% | P1: page |
| BurnSlow | 6 | 6h AND 30m | 6 × 6 / 720 = 5% | P2: chat / working-hours investigation |

Both ratios must exceed B × (1 − 0.99): 14.4% or 6% bad requests.
At constant burn 14.4 the whole budget lasts only 50 hours; leaving it until
morning spends a meaningful share and exposes users to severe failures or
slowness, justifying an interruption. A burn of 6 exhausts it in 120 hours,
leaving time for a lower-cost, non-paging investigation. Five minutes pending
avoids waking someone for a momentary spike. The short window clears an alert
soon after recovery rather than retaining an hour or six hours of old harm.
The rates describe sustained burn; the actual fire instant depends on history
and on the pending period, not just the long-window budget percentage.
For an incident, inspect dependency health and 502s, saturation and latency,
then mitigate the dependency or roll back a regression. Do not add retries
or relax the objective merely to silence an alert.

## Histogram design

The 28 finite boundaries, in seconds, are:
`[0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.06, 0.08, 0.09, 0.1,
0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.2, 0.22, 0.24,
0.3, 0.4, 0.5, 0.75, 1, 2, 5]`.

The measured p99 is in (0.12, 0.13]; width / q = 0.01 / 0.1248 = 8.01%.
Every interval covering 0.08–0.24 s has width at most 20% of its lower end.
That band is wider than the required ±10% [0.11232, 0.13728] and accommodates
another machine and new random draws. Low boundaries show the common
20–40 ms mode; high boundaries and +Inf reveal severe stalls and timeouts.
All routes and statuses use the same ladder. Only bounded HTTP methods,
matched route templates (or `unmatched`) and status codes become labels:
no ticket IDs, query text or raw paths. /metrics is deliberately excluded.
The cost is 28 finite buckets plus +Inf, sum, count and created per labelset;
we spend resolution where it changes the p99 decision, not on arbitrary
millisecond detail across the entire range.
