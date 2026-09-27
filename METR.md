---
actual_minutes: 1.13
---

# METR n=1 replication

The prediction was 25 minutes for a single-ticket lifecycle event lookup. I measured from the first implementation edit at 2026-09-27 22:01:44 UTC to the completed local verification at 2026-09-27 22:02:52 UTC: 68 seconds, or 1.13 minutes. The work added a module that reads and serializes the stored ticket's occurred lifecycle events, exposed it through `GET /dora/tickets/{ticket_id}/events`, and added own-test coverage for an existing ticket and an unknown ticket. The existing all-ticket stream and Lab 2 metric calculations remained covered by the same checker run.

The endpoint returned the expected lifecycle phases and the unknown-ticket case returned the service's standard 404 error. `./itsmlab.sh verify 2` completed successfully for Core and the two other Stretch checks, and its own-tests service exercised the new route. The result is much faster than I predicted; I include the complete implementation and verification interval rather than estimating a hypothetical human coding time. The measure includes the Docker build and checker run after the first edit, so the elapsed time is reproducible from the recorded UTC timestamps.

Ratio actual/predicted: **0.05** (`1.13 / 25`, rounded to two decimal places).
