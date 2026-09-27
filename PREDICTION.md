---
feature: "Single-ticket lifecycle event lookup"
predicted_minutes: 25
predicted_at: "2026-09-27T21:59:41Z"
feature_path: "src/svcdesk/ticket_event_lookup.py"
---

I predict that implementing and testing `GET /dora/tickets/{ticket_id}/events` will take 25 minutes. For a ticket held by the service, the endpoint will return its lifecycle events in the same shape and order as the existing all-ticket stream; an unknown ticket will return the service's standard not-found error. I will measure from the first implementation edit to a passing local verification of this endpoint.
