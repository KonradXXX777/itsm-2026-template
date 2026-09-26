# Repository agent guidance

Implement only behavior required by `specs/svcdesk-api.md`. Preserve the spec-first Git history, keep Docker runtime offline-capable, never introduce host bind mounts, and run both the local own-test profile and `./itsmlab.sh verify 1` before accepting changes.

Security- or repository-wide review work may be delegated to the constrained agent in `.claude/agents/lab-reviewer.md`; its denied tools are justified in `AGENT-POLICY.md`.
