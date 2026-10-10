---
lab3_first_draft:
  source: ai
  tool: "OpenAI Codex, desktop workspace, 2026-10-10"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: TODO
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
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

Pending the first baseline measurement; no ladder has been designed from evidence yet.

## The draft alert rule

Pending SLO design and burn-rate arithmetic.

## Verdict on the instructor's flawed ladder

Pending the same baseline measurement.
