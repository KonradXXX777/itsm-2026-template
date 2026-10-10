---
lab3_first_draft:
  source: ai
  tool: "OpenAI Codex, desktop workspace, 2026-10-10"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: refuted
  evidence: {p99_seconds: 0.1248, bucket: [0.1, 0.25], relative_width: 1.202}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.1248, bucket: [0.04, 0.5], relative_width: 3.686}
---
<!-- ai-generated: 100% - Written by Codex; the first answer is preserved verbatim before measurement. -->

# First proposal before measurement

## Prompt

Propose initial histogram bucket boundaries in seconds and an alert rule for GET /kb/search, which calls a latency-varying upstream. No latency measurement is available yet. State what needs validation before production use.

## Answer

Wstępna propozycja: histogram w sekundach z granicami `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]`. Dla `/kb/search` można rozpocząć od alertu, gdy udział odpowiedzi 5xx z ostatnich 5 minut przekracza 1% przez 5 minut:
`sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code=~"5.."}[5m])) / sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m])) > 0.01`.
To propozycja bez znajomości rozkładu opóźnień; granice i alert trzeba zweryfikować pomiarem oraz budżetem błędów SLO.

## Verdict on the draft ladder

The first published load (2026-10-10, checker 0.8.1, login konradxxx777)
measured p99 = 0.1248 s. The unchanged draft contains it in (0.1, 0.25].
Width / p99 = (0.25 − 0.1) / 0.1248 = 1.201923, or 120.2%, not at most 20%.
The verdict is refuted. The histogram interpolates within a 150 ms interval
without knowing where the observations inside it occurred. In this run its
estimated p99 was 211.3 ms, 69.3% above the client's p99. Dense buckets near
the median do not rescue that tail estimate. Both 0.95q and 1.05q remain
inside the same coarse interval, so the verdict is not a boundary accident.

## The draft alert rule

The 1% threshold is burn 1 for a 99% availability objective. The observed
failure rate (7/2400 = 0.292%) does not trigger it, but a modest sustained
degradation could page after a single noisy five-minute window, without
confirming longer-term harm. We kept the route/job filters, 5xx definition
and rate-of-counters ratio. We replaced the single window and arbitrary
threshold with explicitly budget-derived burns 14.4 and 6 and long AND
short windows, for paging versus chat. We retained the five-minute pending
period and added equally budget-derived latency alerts. Reset and edge
tests make these changes falsifiable rather than trusting the AI answer.

## Verdict on the instructor's flawed ladder

The instructor's boundaries put the same 0.1248 s in (0.04, 0.5].
Width / p99 = (0.5 − 0.04) / 0.1248 = 3.685897, or 368.6%; verdict: refuted.
Most of its fourteen boundaries cover 1–40 ms, while its 460 ms tail bucket
collapses the slow population. Depending on cumulative counts, linear
interpolation can put a reported percentile anywhere in that interval;
it cannot locate the 125 ms tail from the bucket totals alone. The final
ladder resolves a broad band around q, detailed in slo.md; the original
assistant response above is not rewritten to resemble that final design.
