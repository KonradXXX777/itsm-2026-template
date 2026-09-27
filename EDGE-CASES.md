---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 100% - OpenAI Codex drafted the analysis from METRIC-SPEC.md and the service's practice-fixture output -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three commit timestamps fall after the successful production deployments that carried them.
- What a default definition would have done: It might discard those pairs or report negative delivery times, both hiding clock skew in the dashboard.
- Why the rule is defensible: Keeping each shipped commit and clamping its duration to zero preserves the delivery evidence without claiming negative elapsed time.

## E2 - a revert of a revert

- What the log contains: Two commits revert earlier commits, including a commit that is itself a revert; both chains resolve to their original change.
- What a default definition would have done: Counting every commit as a new change would inflate the change count and distort lead-time and delivery totals.
- Why the rule is defensible: A revert changes code history but does not create a new unit of work, so following the chain preserves the original change identity.

## E3 - a hotfix that never touched `main`

- What the log contains: Four distinct non-main commit shas are carried by production deployments inside the observation window.
- What a default definition would have done: Filtering to the main branch would erase the hotfixes and make production delivery look slower or smaller than it was.
- Why the rule is defensible: Production receipt is the evidence of delivery; a branch name does not change whether users received the commit.

## E4 - a deployment with zero linked commits

- What the log contains: Four in-window production deployment events have empty commit lists, while retaining their outcomes and other deployment fields.
- What a default definition would have done: Dropping empty deployments would reduce the frequency denominator and alter failure and rework rates without evidence.
- Why the rule is defensible: The deployment still happened, so it belongs in deployment-based counts; only commit-pair calculations have no work to measure.

## E5 - a deployment that failed and never recovered

- What the log contains: One in-window production failure has no covering incident with a resolution event.
- What a default definition would have done: It could omit the failure entirely or invent a recovery at the window boundary, understating instability.
- Why the rule is defensible: An unobserved recovery duration is unknown, but the failure is known; it remains in the fail-rate numerator and is counted as open.

## E6 - overlapping incidents

- What the log contains: Distinct incident intervals overlap in eleven unordered pairs; some incidents cover multiple failed deployments.
- What a default definition would have done: Merging intervals or summing incident durations would lose incident-level attribution and could overstate recovery time.
- Why the rule is defensible: Recovery belongs to each failed deployment and its earliest covering incident; overlap is reported as a separate anomaly rather than merged away.

## Gaming demonstration

The gaming log raises `deployment_frequency_per_day` from 2.000000 to 2.523810 (53 events over 21 days), clearing R-20's 25% relative margin under R-11. It adds eleven empty production deployments and clears the commit links from the original deployment events while preserving every original commit, incident, deployment identity, outcome, environment and timestamp. This makes the metric look better while the original work delivered falls from 65 changes to zero under the ground-truth calculation. A team rewarded for raw deployment count, or a manager whose bonus depends on that dashboard, could create pressure to count empty releases and hide scope; the release-count owner would be rewarded while users and teams waiting for the real changes would bear the cost.
