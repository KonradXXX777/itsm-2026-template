# Agent tool-denial policy

- Bash(rm:*): File deletion is outside a reviewer's remit and could destroy specifications, implementation evidence, or receipt history.
- Bash(git push:*): Publishing commits or tags changes the externally graded repository and must remain an explicit owner-controlled release action.
- Bash(docker login:*): Registry authentication touches reusable credentials and is unnecessary for a read-only conformance review.
