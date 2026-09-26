---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: reopen         # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 100% - OpenAI Codex drafted the reasoning from the selected service-owner outcomes. -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 acknowledgement and resolution targets use continuous wall-clock time, including nights and weekends.

**Rejected alternative:** Counting only weekday business windows for P1 would pause the most critical incidents outside office hours.

**Reason:** A P1 represents the largest service impact and urgency, so a four-hour target that can pause for an entire weekend would not express the operational risk. Continuous measurement also gives on-call teams an unambiguous deadline while P2-P4 retain cost-conscious business-time targets.

**Service owner:** The IT service owner signs off because this role owns availability commitments, support coverage and the cost of the on-call model required to meet them.

**Customer outcome:** Customers receive a predictable response to critical outages at any time, rather than discovering that an urgent clock silently stopped after office hours.

## C2 - Closed tickets and reopening

**Decision:** A closed ticket may be reopened into `in_progress` within seven days of its most recent resolution timestamp.

**Rejected alternative:** Making closed tickets immutable would force reporters to create a duplicate even when the same symptom returns immediately.

**Reason:** A short reopening window preserves one audit trail and avoids duplicate triage while remaining bounded. The same seven-day rule already applies to resolved tickets, so extending it to closed tickets is simple to explain and operate.

**Service owner:** The service desk process owner approves this lifecycle rule because that role is accountable for ticket quality, duplicate demand and closure policy.

**Customer outcome:** Reporters can continue the original conversation when a fix proves incomplete, without losing context or waiting for a new ticket to be correlated.

## C3 - VIP reporters and the priority matrix

**Decision:** VIP tickets calculated as P3 or P4 are elevated to P2; tickets already calculated as P1 or P2 remain unchanged.

**Rejected alternative:** Applying only the ordinary impact-urgency matrix would give no controlled recognition to explicitly designated VIP reporters.

**Reason:** A bounded elevation to P2 provides faster handling for strategically important reporters without allowing VIP status to manufacture a P1 outage. Impact and urgency remain the primary controls, and client-supplied priority is ignored.

**Service owner:** The business relationship owner signs off because this role maintains the VIP definition and balances contractual attention against fair operational capacity.

**Customer outcome:** VIP reporters receive consistently faster handling for low-priority requests, while genuinely critical incidents retain the distinct P1 path.
