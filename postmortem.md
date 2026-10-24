---
lab4_postmortem:
  ticket: "3ba75e92-1b55-483b-a69e-6097c02b182c"
  detecting_alert: ShopCheckoutSlow
  onset: 2026-10-12T05:01:00Z
  detection: 2026-10-12T05:06:19Z
  acknowledgement: 2026-10-12T05:06:56Z
  recovery: 2026-10-12T05:08:19Z
  mttd_seconds: 319
  mtta_seconds: 37
  mttr_seconds: 439
  identified_flags: [adFailure, intlShippingSlowdown, emailMemoryLeak]
---
<!-- ai-generated: 100% - Codex analysed the assigned recording, executed PromQL and wrote this retrospective; no live response is invented. -->

# Postmortem: slow checkout, failed advertisements and email memory pressure

## Date

The incident occurred on **12 October 2026**, not on the laboratory date. This retrospective was prepared on 24 October 2026. All incident times below are UTC; the recording is `lab4-rec-1`, assigned to `konradxxx777` by `./itsmlab.sh recording 4`.

## Authors

Konrad Sieradzki is the student responsible for the submission and prospective on-call process. Codex performed the recorded-path investigation and drafted the artifacts. The original operator's ticket, metrics and first AI transcript were supplied with the recording; we did not perform their historical actions ourselves. The second investigator was the unmodified course agent loop with a different local model, as documented in its ledger and comparison.

## Status

Retrospective analysis complete; preventive actions remain planned. The detecting checkout alert recovered according to the laboratory's clock definition. This is **not** proof that every dependency had recovered then: the ad error alert persisted longer. The supplied ticket remains `acknowledged`, with null `resolved_at` and `closed_at`; we preserve it rather than manufacture a closure or an API call absent from the snapshot. A real on-call would validate the remaining symptoms, resolve and then close the ticket through the Lab 1 workflow. The underlying problem remains open.

## Summary

During the assigned recorded incident, checkout SERVER p99 reached approximately **9050 ms**, while shipping reached **8100 ms**, versus healthy values of 49.6 ms and 5.28 ms. Ad requests also failed and email used substantially more of its memory limit. The first firing alert was `ShopCheckoutSlow` at 05:06:19Z. Its first firing run ended at 05:08:19Z: formal MTTR 439 seconds from onset, not an assertion of complete multi-service recovery.

## Impact

All point comparisons use **04:56:00Z** (healthy, onset minus five minutes) and **05:06:00Z** (fault) on 12 October. Queries, actual responses and the original archive SHA-256 are saved in `incident/evidence.json`, reproducible with `scripts/lab4_evidence.py`.

| Measured user-facing signal | Healthy | During fault | Query in evidence.json |
|---|---:|---:|---|
| Checkout SERVER p99 | 49.6 ms | 9050 ms | `server_p99_ms`, checkout series |
| Shipping SERVER p99 | 5.28 ms | 8100 ms | `server_p99_ms`, shipping series |
| Checkout shipping CLIENT POST p99 | low before fault | 7150 ms | `checkout_shipping_client_p99_ms` |
| Ad SERVER error ratio | no recorded error series | 6.195% | `server_error_ratio`, ad series |
| Email SERVER p99 | 7.94 ms | 181 ms | `server_p99_ms`, email series |
| Email container memory | about 59.6 MB | 93,761,536 bytes, 89.4% of 100 MiB limit | `memory_bytes`, `memory_limit_bytes` |

The latency query is `histogram_quantile(0.99, sum by(service_name,le)(rate(traces_span_metrics_duration_milliseconds_bucket{span_kind="SPAN_KIND_SERVER"}[5m])))`; duration units are **milliseconds**. The ad ratio divides SERVER `STATUS_CODE_ERROR` call rate by all SERVER call rate for the same service. The histogram estimates tail latency, not an exact slow-request count, and quantiles across services cannot be added or subtracted as a trace decomposition.

For the formal 439-second interval, `sum(increase(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER"}[439s]))` evaluated at 05:08:19Z estimates **47.04 checkout spans**. The corresponding ad estimate is **72.98 calls, 5.04 errors (about 6.90%)**; frontend is **1762.94 calls, 10.07 errors**. The complete queries and responses are under `impact`. These are extrapolated counter increases over minute-spaced observations, **not exact orders, unique customers, payment losses or requests all proven slow**. Checkout error series are absent despite positive traffic; the observed checkout incident is principally latency, not evidence of a payment outage. No business-revenue telemetry was available, so financial loss is unknown.

## Root Causes

We inferred the following fault keys from **ordinary service telemetry**, not by opening the sealed ground truth:

1. **`intlShippingSlowdown`**: shipping SERVER p99 moves from 5.28 ms to 8100 ms; checkout's shipping CLIENT POST reaches 7150 ms while checkout SERVER reaches 9050 ms. Payment SERVER remains 1.98 ms, catalog SERVER stays near 46 ms, and checkout's internal `prepareOrderItemsAndShippingQuoteFromCart` stays near 49.58 ms. This isolates a slow shipping path as the strongest explanation for slow checkout, rather than local preparation, catalog locking, a failed payment or a traffic flood. The pooled histogram cannot determine which individual shipment was international or an exact injected delay variant.
2. **`adFailure`**: ad SERVER error rate reaches 0.01183/s of 0.1910/s total (6.195%), while ad p99 stays near 5.8 ms instead of showing a large latency/GC spike. The recorded `ShopServiceErrors{service_name="ad"}` corroborates the symptom, but the error-rate calculation is independent of its name. This favors failures over `adManualGc`.
3. **`emailMemoryLeak`**, with more uncertainty: email grows from approximately 59.6 MB to 93.76 MB against its 104,857,600-byte limit; the five-minute peak is 96,960,512 bytes (92.47%). Email p99 rises to 181 ms. Recommendation memory stays around 53–55 MB against 500 MiB, so the resource anomaly is localized to email, not recommendation cache growth. Email uptime rises continuously: **no observed OOM kill or restart is claimed**. Memory recedes toward baseline after the incident. The flag is a diagnosis consistent with pressure and the available pool, not proof of a leak from heap profiling.

These are concurrent injected failures, not evidence that ad failures caused shipping delay or that memory pressure alone explains checkout's multi-second tail. No flags outside these three are asserted. The first agent's catalog/internal-span/load/payment explanations are explicitly tested and mostly refuted in `ai-rca-eval.json`.

## Trigger

The public binary activity marker begins at 05:01:00Z (raw sample 05:01:00.242Z), which is the onset reported by the checker. The recording contains one armed run. At that point the injected changes manifested as independent service errors, downstream latency and memory pressure. We did not use the sealed seed or hidden flag values to identify the causes. There is no evidence here of a student deployment causing the incident.

## Resolution

This is a **recorded-path retrospective**: the archive does not contain an authenticated per-flag switch-off audit, so the exact historical disable order is unknown. We did not send flag mutations, claim to have rolled back services, or edit the supplied ticket. The recorded checkout P1's last firing sample is 05:08:09.815Z; adding the 10-second evaluation interval gives the prescribed 05:08:19Z recovery (seconds displayed by the checker). The public activity marker first becomes zero at **05:10:05.242Z**. Ad's recorded error alert remains firing through **05:13:09.815Z**; a five-minute error-rate window is still above our 2% proposal at 05:14Z. Thus alert recovery, all-flags-off and all-symptoms-quiet are distinct events.

For an analogous live incident the proposed mitigation order is: remove the shipping delay first to reduce order latency; disable ad failures next while retaining checkout capacity; disable the email leak and watch memory/uptime before considering a controlled restart. Observe error/latency and memory windows after each action, retain evidence, and only resolve the incident after customer symptoms clear. This order is a **future runbook recommendation**, not an invented historical timeline. Removing injected triggers is a workaround; downstream timeouts, resilience and leak prevention are still action items.

## Detection

`./itsmlab.sh incident 4` chooses `ShopCheckoutSlow` at 05:06:19Z. Several alerts share that first timestamp; the P1 wins over P2. MTTD is **319 seconds**, MTTA from that page to recorded acknowledgement is **37 seconds**. Five-minute smoothing and a pending period trade detection delay for reduced noise. Without the page, users or support would likely report slow order submission; the snapshot contains no evidence that they actually did.

The submitted `prometheus/demo-alerts.yml` is our **proposed** alert set, not a claim that these exact rules ran in the historical recording. At 04:56Z all four expressions are empty. At 05:06Z checkout latency, ad errors and service latency cross their thresholds; checkout errors do not, which is appropriate for this latency-led incident. The historical `ShopServiceSlow` was P2; our proposal makes it P3 and waits five minutes, retaining the dedicated checkout P1. We route P1 to pager and P2/P3 to chat, inhibiting only same-`system` non-P1 shop notifications when a P1 is active. Nonempty-system guards prevent suppression of Lab 3 KB alerts with no such label. Inhibition affects notifications, not metric storage or whether an alert is firing.

## Action Items

The identifiers below are stable planned backlog IDs for Labs 6/8, **not claims that external GitHub issues were opened**. Owners designate responsibility for follow-up rather than blame for the injection.

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add bounded shipping-call timeouts and a tested fallback that clearly tells customers when a shipping quote is unavailable. | prevent | Checkout maintainer | ITSM-401 |
| Add an email memory regression test with a sustained workload and a warning below the container limit. | prevent | Email maintainer | ITSM-402 |
| Make advertisement failures non-blocking and verify that the storefront remains usable when ads fail. | mitigate | Frontend maintainer | ITSM-403 |
| Require an explicitly timed histogram/error query and a healthy-baseline comparison before acting on an AI causal claim. | process | On-call lead | ITSM-404 |
| Add a recorded recovery checklist covering residual ad errors, memory trend and the ticket resolve/close workflow. | process | Service desk owner | ITSM-405 |
| Replay slow-checkout scenarios to tune the 319-second detection delay without paging on healthy traffic fluctuations. | mitigate | Observability owner | ITSM-406 |

## Lessons Learned

### What went well

The independent latency alert caught an incident without checkout error spans. A timestamped ticket and acknowledgement are backed by svcdesk request counters in the same snapshot. Read-only Prometheus tools let both investigators inspect exactly the same evidence. Keeping the original archive and transcripts makes disputed claims reproducible.

### What went wrong

The first agent interpreted cumulative call counts as duration and even inferred missing payment data after not requesting it correctly. Several malformed queries yielded no evidence; a convincing final answer did not repair that. The second agent also needed a repeated, time-specific investigation after its initial run used `now` against historical data and returned too few concrete hypotheses. No autonomous mutation was allowed. The formal checkout recovery preceded complete clearing of the multi-service incident, so an unqualified “all fixed” would be misleading.

### Where we got lucky

Email memory peaked below its 100 MiB limit and uptime shows no restart; a larger leak could have compounded checkout degradation. Payment remained responsive, avoiding a payment-related incident on top of slow shipping. The assigned recording fits the 8 GB workstation without running the 6+ GiB live playground; no competing Kubernetes cluster was needed to achieve the full two-of-three Stretch bundle.

## Timeline

Times are UTC on 12 October 2026. Items labelled retrospective were performed on 24 October, against historical instants; they are not fabricated actions during the original incident.

| Time | Evidence / action |
|---|---|
| 04:56:00 | Healthy comparison: checkout p99 49.6 ms, shipping 5.28 ms, no firing shop P1. It is onset minus 300 s and is re-evaluated for each correct/partial ledger prediction. |
| 05:00:00 | Last quiet whole minute before onset; baseline recorded traffic precedes the armed run by at least ten minutes (checked from the snapshot by Tier A). |
| **05:01:00** | **Onset**, first active marker (raw .242 s); one armed run, no knowledge of sealed flag values used. |
| 05:06:00 | Retrospective diagnostic instant: checkout/shipping histogram p99 9050/8100 ms, ad errors 6.195%, email 93.76 MB. All testable primary-ledger claims are evaluated here, not at the analyst's current wall clock. |
| **05:06:19** | **Detection**, first `ShopCheckoutSlow` firing, tied P2 symptoms; pager evidence is present in the recording. |
| 05:06:36 | Original P1 ticket created, impact 1 / urgency 1, ID `3ba75e92-1b55-483b-a69e-6097c02b182c`; successful POST corroborated by telemetry. |
| **05:06:56** | **Acknowledgement** in the original ticket and successful `/tickets/{id}/ack` telemetry; MTTA 37 s. |
| **05:08:19** | **Recovery** under I-14: first detecting-alert run ends (last sample at 05:08:09.815Z plus 10 s); MTTR 439 s. Not full multi-service restoration. |
| 05:10:05.242 | First public active-marker zero; individual switch-off order is not available. |
| 05:13:09.815 | Last recorded firing ad-error sample; ad metrics can retain a five-minute tail after removal of the trigger. |
| 05:14:00 | Retrospective follow-up: checkout/shipping latency below proposed threshold; ad ratio 2.70% remains above 2%, email near baseline. |

**AI decision audit (retrospective, not a historical live intervention):** H1's proposed high load was rejected using `sum(rate(traces_span_metrics_calls_total{service_name="checkout",span_kind="SPAN_KIND_SERVER"}[5m])) > 0.225`. H2 and H6's payment premises were rejected using the payment duration-availability and error predicates in the ledger. H3's catalog cause was rejected with catalog SERVER histogram p99 `> 300`. H4's checkout symptom was retained, but its primary-local-cause attribution was not: checkout p99 `> 2000 unless on()` preparation-phase p99 `> 150`. H5 and repeated H7's internal-delay cause were rejected with that preparation-phase p99 `> 150`. All full executable predicates, results and healthy comparisons are in `ai-rca-eval.json` and `incident/evidence.json`. The second run and every additional causal claim are similarly audited in `ai-rca-eval-2.json`; see `ai-rca/COMPARISON.md`. **No AI hypothesis was used to mutate the recorded system.**

## Supporting information

- `incident/tsdb-snapshot.tar.gz` and `incident/ticket.json`: unchanged assigned recording artifacts, not newly generated evidence. Archive digest and sampled results are in `incident/evidence.json`.
- `./itsmlab.sh incident 4`: run `65125b2a3e80aecf`, onset 05:01:00Z, detecting alert `ShopCheckoutSlow`, detection 05:06:19Z, acknowledgement 05:06:56Z, recovery 05:08:19Z, MTTD/MTTA/MTTR 319/37/439 seconds.
- `scripts/lab4_evidence.py`: read-only reproduction of service comparisons, estimated impact, all testable ledger predicates and the public clock samples. It never opens hidden ground truth.
- `ai-rca/transcript.md`, `ai-rca/second/transcript.md`, both JSON ledgers and `ai-rca/COMPARISON.md`: verbatim model outputs and explicit scoring; unsuccessful queries are retained too.
- `alertmanager/routing-tests.yml`: route cases for every proposed shop alert plus existing KB alerts, same-system suppression, a system-only-different negative pair, and absent-system guards.
- `comms-log.md`: simulated notification clock calculations under the course's assumptions; no real regulator was contacted. `LAB4-RUNBOOK.md` describes local replay, checks and scope.

## Problem record

Incident record: P1 `3ba75e92-1b55-483b-a69e-6097c02b182c`, original recorded state acknowledged; recovery evidence does not rewrite its lifecycle history.
Root cause: Concurrent shipping latency, advertisement failures and probable email memory leakage expose missing dependency resilience and resource regression protection; this problem remains open pending preventive work.
Known error: The analyzed system can return slow checkout while error-only monitoring remains quiet, and AI can misread cumulative span counts as latency; validated workarounds exist but the underlying resilience gaps are not yet removed.
Workaround: Remove injected shipping/ad/email triggers in a controlled live response, monitor the independent latency/error/memory signals until clear, and require timed histogram evidence before following AI suggestions; do not mistake a recovered checkout alert for a closed problem.
