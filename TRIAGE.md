---
lab5_triage:
  image: ghcr.io/konradxxx777/itsm-2026-template@sha256:e6989da5692ba056e639f8913c52be482548b548357baef8d5b8987099a45391
  sarif_receipt: 424
---
<!-- ai-generated: 100% - Codex triaged measured image findings, audited the SARIF, and interpreted the reproduced matrix. -->

# Lab 5 — supply-chain triage

The measured comparison uses the old Lab 4 Dockerfile, with the base digest observed in its previous build, and the
new Lab 5 image. We scanned both local ARM64 images with the same Trivy 0.74.0 vulnerability database, limiting both
scans to fixable HIGH/CRITICAL findings. The old image gave **15 package findings (11 distinct advisory IDs)**; the
new one gave **0**. The remote Linux build independently passed the same gate on the
[green main run](https://github.com/KonradXXX777/itsm-2026-template/actions/runs/43652183021). These measurements are
not a claim of zero vulnerabilities across all severities, architectures or databases. No exceptions were added to
`.trivyignore` or `.gitleaksignore`: prefer removing the vulnerable component to muting its signal.

The base is pinned by manifest digest. Debian packages and transitive Python requirements still resolve at build
time; the final image digest and its signed SPDX 2.3 inventory are the evidence of **what was built**, not a claim
that arbitrary future rebuilds will be byte-identical. The named image is from main commit `6b07edd`. Its provenance
and SBOM both passed `gh attestation verify` against `ci.yml` on `refs/heads/main`.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2026-109518 | fix | The old Debian runtime ships apt and libapt-pkg7.0 3.0.3. The refreshed pinned base ships both at 3.0.4, the fixed version reported by Trivy. |
| trivy | CVE-2026-103111 | fix | The base refresh replaced libpcre2-8-0 10.46-1~deb13u2 with 10.46-1~deb13u3. Verified the exact package version in the rebuilt image. |
| trivy | CVE-2026-84782 | fix | The pinned base replaces the old OpenSSL set: openssl, libssl3t64 and openssl-provider-legacy moved from 3.5.7-1~deb13u2 to the fixed ~deb13u3 builds. |
| trivy | CVE-2026-76844 | fix | Dockerfile runs apt-get update and upgrade before installing the app. This updates zlib1g from 1:1.3.dfsg+really1.3.1-1+b1 to the fixed 1:1.3.dfsg+really1.3.1-1+deb13u1. |
| trivy | CVE-2026-85091 | fix | This is a separate advisory on the same zlib1g package. The Debian security upgrade above removes both findings in the same Trivy image rescan. |
| trivy | GHSA-6q48-6c7w-9gw2 | fix | Trivy saw two certifi copies in the baseline: the transitive Python install (2026.7.22) and a vendored copy (2026.6.17). The rebuild resolved certifi to 2026.10.23, above the fixed 2026.10.18; uninstalling pip removed its older vendored copy. |
| trivy | CVE-2026-114613 | fix | Baseline pip vendors msgpack 1.1.2; a separate application dependency upgrade would not replace that copy. Dockerfile uninstalls pip in the dependency-install layer; the new runtime has neither pip nor the finding. |
| trivy | GHSA-6v7p-g79w-8964 | fix | Another finding on pip's vendored msgpack 1.1.2. The package installer is build-time only, so removing pip removes the vulnerable library without an ignore. |
| trivy | CVE-2025-47273 | fix | The baseline's vendored setuptools 70.3.0 is not needed to serve requests. Remove pip and its vendored files after installation; Trivy no longer reports this item. |
| trivy | CVE-2026-97687 | fix | Baseline pip contains urllib3 2.7.0. The HTTP client used by svcdesk is httpx, not pip's copy of urllib3; with pip absent in the runtime, the finding disappears. |
| trivy | CVE-2026-97689 | fix | A second issue in the same vendored urllib3 2.7.0; removing the build installer removes it as verified by the new image scan. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | Dockerfile:19 actually runs as root inside the container. For this backwards-compatible coursework image, do not break existing named SQLite volumes with an uncontrolled UID change: no privileged mode, host bind on svcdesk or Docker socket. Accept only for the lab; before a real deployment migrate volume ownership, run as a dedicated UID and test startup and writes under that UID. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | The hits are local operator utilities, not remotely reachable SSRF sinks: gap/setup.py:14 uses the fixed localhost Toxiproxy origin with caller-owned paths; scripts/lab4_evidence.py:48 reads Prometheus at the operator's CLI address (loopback by default) and only issues read-only queries. Neither URL is derived from an HTTP request to svcdesk. |
| semgrep | python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query | false-positive | src/svcdesk/main.py:233 builds a WHERE clause only from constant fragments and bound query values. At :253 the optional timestamp column is a constant passed by internal transition call sites; the ticket ID, state and timestamp are bound parameters, not SQL text from the client. The connection is stdlib SQLite, not SQLAlchemy. |

The three Semgrep rule IDs above cover every result outside `lab5-canary/` in the receipted scanner SARIF. The
reporting scanners are deliberately not suppressed: the two false positives are explained, and root containment is
treated as a real, time-limited deployment risk. The course's evidence exclusions are not general scanner ignores;
the planted pins and credentials still fail their respective gates on
[canary](https://github.com/KonradXXX777/itsm-2026-template/actions/runs/43652470581).

## Bake-off

The [SARIF receipt and reveal](https://github.com/swasik/itsm-2026-submissions/issues/424) label **11 defects**. The
matrix below counts defects, not advisories: the same dependency can generate many CVE results. All five scanner
files are untouched and verified against attestations on the same canary commit. The sixth detector, local
Ollama `qwen3:1.7b`, ran before the reveal on the same numbered canary files, without seeing scanner results.

| Detector | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Trivy | 4 | 0 | 7 | 1.0000 | 0.3636 | 0.5333 |
| Grype | 2 | 0 | 9 | 1.0000 | 0.1818 | 0.3077 |
| OSV-Scanner | 2 | 0 | 9 | 1.0000 | 0.1818 | 0.3077 |
| gitleaks | 3 | 0 | 8 | 1.0000 | 0.2727 | 0.4286 |
| Semgrep | 6 | 0 | 5 | 1.0000 | 0.5455 | 0.7059 |
| AI reviewer | 0 | 4 | 11 | 0.0000 | 0.0000 | 0.0000 |

**Keep Trivy's dependency and image gates and gitleaks' secret gate.** Trivy caught both labelled vulnerable pins
(D04 python-multipart and D08 urllib3) and two of the three planted credentials in its combined report. Its dependency
gate intentionally uses vulnerabilities only. Gitleaks found all three credentials, including C06 that Trivy
missed, and separately failed the secrets gate. Its apparent 27.27% recall is over **all 11** defects; that is not a
27.27% secret-detection rate. Grype and OSV-Scanner also found both pins but contributed no additional matched
defects on this sample. Keep them reporting during triage: different advisory coverage may matter on a real
dependency update; gating on duplicate results would make the same remediation block several times.

**Use Semgrep for code review and promote only narrowly validated rules to gates.** Its 6/11 was the best measured
recall, including the weak password hash, command/code injection and unsafe deserialization. Two of its six TPs
are credential findings already covered by gitleaks. The zero canary FPs do not prove the registry rules should all
block builds: outside the canary this run flagged safe parameterized SQLite text and deliberately operator-directed
URLs. Keep the broad rules advisory; tune a targeted rule set on real code and negative fixtures first. The
union of all six detectors found nine of eleven labels; **none** found A12's missing access control or A16's SSRF.
For business logic, require explicit ownership checks in review and functional tests; for SSRF, test destination
allowlists and redirects at the actual outbound boundary. A green pipeline alone cannot certify either property.

**Do not gate on the small AI reviewer.** All four of its results were false positives under the frozen protocol:
it called attachment export SSRF rather than injection, rules loading a vulnerable dependency rather than
deserialization, ticket access traversal rather than access control, and webhook relay injection rather than SSRF.
These are useful examples of class errors: naming a suspicious file or overlapping line alone does not identify
its labelled defect. We kept the raw answer, including mistakes. A reviewer can propose hypotheses for humans,
but on these measurements it would add four review interruptions and no extra confirmed detection.

The sample is small, seeded and not representative: perfect measured precision for five detectors does not
establish a production false-positive rate, and synthetic bugs are often easier than real ones. There is no
true-negative cell. Re-evaluate by class on actual changes and monitor false positives as well as misses before
adjusting gates. The predicted mechanism matters more than whether one aggregate F1 happens to be larger.
