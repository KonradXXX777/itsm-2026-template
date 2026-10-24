---
lab4_comms:
  awareness: 2026-10-12T05:06:56Z
  detection: 2026-10-12T05:06:19Z
  classification: 2026-10-12T05:12:00Z
  nis2:
    early_warning_due: 2026-10-13T05:06:56Z
    notification_due: 2026-10-15T05:06:56Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  ksc:
    early_warning_due: 2026-10-13T05:06:19Z
    notification_due: 2026-10-15T05:06:19Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  dora:
    initial_due: 2026-10-12T09:12:00Z
    initial_sent: 2026-10-12T06:00:00Z
    intermediate_due: 2026-10-15T06:00:00Z
    intermediate_sent: 2026-10-14T09:00:00Z
    final_due: 2026-11-14T09:00:00Z
  log:
    - {at: 2026-10-12T05:06:56Z, to: "On-call and incident commander", what: "SIMULATION: acknowledge the P1 and recognize significant customer impact; keep regulatory assessment separate from the technical alert."}
    - {at: 2026-10-12T05:12:00Z, to: "Incident commander and compliance lead", what: "SIMULATION: classify as major ICT incident under the exercise assumptions; activate all three notification tracks."}
    - {at: 2026-10-12T05:20:00Z, to: "Designated NIS2 authority and KSC CSIRT channels", what: "SIMULATION: early warnings: slow checkout, concurrent dependency symptoms, limited impact estimates and ongoing investigation; do not assert an attack or data breach without evidence."}
    - {at: 2026-10-12T06:00:00Z, to: "DORA competent authority channel", what: "SIMULATION: initial notification of the classified major ICT incident, detection/awareness times and preliminary mitigation; commit to follow-up."}
    - {at: 2026-10-13T09:00:00Z, to: "Designated NIS2 authority and KSC CSIRT channels", what: "SIMULATION: incident notifications with measured error/latency scope, provisional causes and recovery caveats; starts both one-calendar-month final-report clocks."}
    - {at: 2026-10-14T09:00:00Z, to: "DORA competent authority channel", what: "SIMULATION: intermediate report with updates and recovery evidence; starts the DORA final-report month."}
    - {at: 2026-11-13T08:00:00Z, to: "Designated NIS2 authority and KSC CSIRT channels", what: "SIMULATION: final reports with validated root causes, impact limits and ITSM-401 through ITSM-406 follow-up status."}
    - {at: 2026-11-14T08:00:00Z, to: "DORA competent authority channel", what: "SIMULATION: final report after the intermediate report, including known errors and preventive actions; no weekend extension assumed."}
---
<!-- ai-generated: 100% - Codex calculated the exercise's UTC deadlines from the recorded incident and wrote a hypothetical communications plan. -->

# Communications log: three clocks, one recorded incident

This is the **I-30 classroom simulation**, not a legal applicability assessment or evidence of actual filings. We assume the shop qualifies under all three regimes and the incident is significant/major as instructed. None of the messages below was sent to a regulator. The actual recording is from 12 October; later simulated reports are a plan, including dates after this retrospective was written.

## The three instants you defend

- **Detection — 2026-10-12T05:06:19Z:** the checker's first firing `ShopCheckoutSlow` sample, backed by `ALERTS` and the pager counter. This is the KSC start in the exercise; ticket creation at 05:06:36Z is not substituted for detection.
- **Awareness — 2026-10-12T05:06:56Z:** the ticket acknowledgement is our operational proxy for a human accepting significant customer impact, not merely a machine firing. It is 37 seconds after detection. Acknowledgement alone does not prove a real statutory significance assessment; we explicitly make that assumption for this simulated entity and record it in the first log entry.
- **Classification — 2026-10-12T05:12:00Z:** a hypothetical incident commander classifies the event after triage of the slow order flow, dependency errors and memory pressure. This is **not an event claimed to exist in the TSDB**. Service recovery can precede formal classification: the classification concerns the incident that happened, including its impact, not only whether the checkout alert is currently firing.

The arithmetic follows INCIDENT-SPEC.md I-30 and the supplied template. All hour periods are elapsed UTC hours. The final-report month is a **calendar month**, not 30 days; month-end would clamp to the last valid day. No weekend relief is applied, including the simulated DORA final deadline on Saturday 14 November. These course rules are not advice about a real entity's legal obligations.

| Track | Calculation | Deadline (UTC) |
|---|---|---|
| NIS2 early warning | awareness + 24 h | 2026-10-13 05:06:56 |
| NIS2 notification | awareness + 72 h | 2026-10-15 05:06:56 |
| NIS2 final | notification sent 2026-10-13 09:00 + one calendar month | 2026-11-13 09:00:00 |
| KSC early warning | detection + 24 h | 2026-10-13 05:06:19 |
| KSC notification | detection + 72 h | 2026-10-15 05:06:19 |
| KSC final | notification sent 2026-10-13 09:00 + one calendar month | 2026-11-13 09:00:00 |
| DORA initial | min(classification + 4 h, awareness + 24 h), classification within 24 h | 2026-10-12 09:12:00 |
| DORA intermediate | actual simulated initial sent 2026-10-12 06:00 + 72 h | 2026-10-15 06:00:00 |
| DORA final | actual simulated intermediate sent 2026-10-14 09:00 + one calendar month | 2026-11-14 09:00:00 |

For DORA the alternative awareness cap is 13 October 05:06:56Z, later than classification + four hours; therefore 12 October 09:12Z wins. All planned notifications precede their deadlines. The intermediate deadline follows the **send time**, not the initial deadline, and each final report follows the appropriate **send time**, not detection or the previous due date. UTC also avoids silently changing elapsed hours across Warsaw's October clock change.

## The log

The front matter is the machine-readable log. At 05:06:56Z the response team accepts the incident; at 05:12Z the commander records the major classification. At 05:20Z early warnings would describe observed customer latency, preliminary scope and uncertainty. At 06:00Z the DORA initial notification would report the known timestamps, current mitigation and a contact for updates.

On 13 October at 09:00Z both significant-incident notifications would include the measured span-based impact, distinguishing estimates from unique customers or lost orders. On 14 October at 09:00Z the DORA intermediate report would distinguish recovered checkout from residual ad errors and document that the recorded ticket is not shown closed. Final reports are planned an hour before their respective November deadlines, addressing preventive actions and the still-open problem rather than declaring that removing a trigger permanently fixed the design. The communication log never invents a breach, an actual regulator receipt or a measured revenue loss.
