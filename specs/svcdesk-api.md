<!-- ai-generated: 100% - OpenAI Codex drafted this specification from the Lab 1 requirements; the student selected the service decisions. -->
# svcdesk API specification

This document defines the externally observable contract of the Lab 1 service desk. The service is a JSON HTTP API on port 8080. It persists tickets in SQLite at `/data/svcdesk.db`, which is backed by a Docker named volume. All responses use JSON. Failures caused by invalid input return HTTP 400 or 422; missing resources return 404; invalid state transitions return 409. Error responses contain a top-level `error` field.

## R-01 Health and routing

`GET /health` returns status 200 and `{"status":"ok"}`. Routes that are not defined return HTTP 404.

## R-02 Deterministic test clock

When `SVCDESK_TEST_CLOCK=1`, every request reads `X-Test-Clock` as an RFC 3339 timestamp. This timestamp is the request's current time and is used for creation, transition and SLA calculations. A malformed supplied clock is rejected with HTTP 400 or 422. Timestamps are returned as UTC instants using a trailing `Z`.

## R-03 Ticket creation

`POST /tickets` accepts `title`, optional `description`, `reporter`, `impact` and `urgency`. `title` is required, non-empty and at most 200 characters. `impact` and `urgency` are integers from 1 through 3. `reporter` has a required non-empty `name` and an optional boolean `vip` that defaults to false. A client-provided `priority` is ignored. A successful create returns HTTP 201 and a ticket with a unique non-empty string `id`, state `new`, computed priority, the submitted fields, `created_at`, and nested `sla.ack_due_at` and `sla.resolve_due_at` timestamps.

## R-04 Priority matrix

Priority is calculated from `(impact, urgency)` as follows: `(1,1)=P1`, `(1,2)=P2`, `(1,3)=P3`, `(2,1)=P2`, `(2,2)=P3`, `(2,3)=P4`, `(3,1)=P3`, `(3,2)=P4`, `(3,3)=P4`.

## R-05 VIP policy

Decision C3 is `vip`. After applying the matrix, a reporter with `vip: true` has P3 or P4 raised to P2. P1 and P2 remain unchanged. This rule is computed from trusted impact, urgency and reporter data, never from a client-provided priority.

## R-06 Read and list

`GET /tickets/{id}` returns the complete ticket or HTTP 404 with a top-level `error`. Ticket identifiers are opaque. `GET /tickets` returns a JSON array and supports independent `state` and `priority` query filters. A returned item follows the same ticket representation as the create and transition responses.

## R-07 State machine

The normal lifecycle is `new -> acknowledged -> in_progress -> resolved -> closed`. Actions use `POST /tickets/{id}/ack`, `/start`, `/resolve`, `/close` and `/reopen`. Acknowledging stores `acknowledged_at`; resolving stores `resolved_at`; closing stores `closed_at`. Any transition outside the allowed source state returns HTTP 409.

## R-08 Reopening policy

A resolved ticket may be reopened into `in_progress` until and including seven days after `resolved_at`; later requests return 409. Decision C2 is `reopen`, so a closed ticket may also be reopened into `in_progress` within seven days of its `resolved_at`. New, acknowledged and in-progress tickets cannot be reopened.

## R-09 SLA targets

Targets are: P1 acknowledge 15 minutes and resolve 4 hours; P2 acknowledge 1 business hour and resolve 8 business hours; P3 acknowledge 4 business hours and resolve 24 business hours; P4 acknowledge 8 business hours and resolve 72 business hours. Decision C1 is `wallclock`, so only P1 counts continuously. P2 through P4 count business time.

## R-10 Business-time calendar

Business windows are Monday through Friday, 08:00 inclusive to 16:00 exclusive in `Europe/Warsaw`, with daylight-saving changes respected and public holidays treated as ordinary business days. Work requested outside a window starts at the next opening. When a target lands exactly at closing, the due time is that day's 16:00 rather than the next opening.

## R-11 SLA status

`GET /tickets/{id}/sla` returns at least `ack_breached`, `resolve_breached` and `paused`. An acknowledgement breaches only if `acknowledged_at` is after `ack_due_at`, or, while still unacknowledged, the request clock is after the due time. Resolution is analogous. A completed event remains non-breached later if it occurred on time. `paused` is true when the ticket's active clock is business-time and the request clock is outside a business window; it is false for wall-clock P1 tickets.

## R-12 Persistence and concurrency

All tickets and transition timestamps survive service restarts through SQLite. Writes use transactions, generated identifiers do not collide, and database initialization is idempotent. The API must remain deterministic for sequential checker requests and must not depend on network access at runtime.

## R-13 Container contract

Docker Compose defines a service named `svcdesk` with `build: .`, exposes container port 8080, sets `SVCDESK_TEST_CLOCK=1`, uses only named volumes, and provides a health check. The image installs pinned dependencies at build time. Runtime startup performs no downloads.

## R-14 Validation and error envelope

Schema and application errors are normalized to a JSON object with a non-empty `error` value. Requests missing `title`, with title longer than 200 characters, with non-integer or out-of-range impact or urgency, with an invalid reporter, or with a malformed test clock never create a ticket.

## R-15 Verification

The repository includes containerized own tests that exercise health, validation, the complete state machine, filters, priority/VIP behavior, deterministic clocks and SLA calculations. Their final stdout line is `ITSMLAB-TESTS: passed=<n> failed=0`, with at least ten passing assertions.
