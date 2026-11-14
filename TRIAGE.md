---
lab5_triage:
  image: ghcr.io/mateuszslawinski/itsm-svcdesk@sha256:73f95987c6068705effe8eeffe5ea73458861ea62957c974d61838c912410550
  sarif_receipt: 401
---

# Triage

The `.trivyignore` and `.gitleaksignore` files have no active entries. These rows cover every finding outside the
canary in the SARIF attached to receipt 401.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| grype | GHSA-6w46-j5rx-g56g-pytest | fix | The receipted scan found pytest 8.4.1 in requirements.txt. Commit ae1069c upgraded it to the fixed pytest 9.0.3, and the subsequent dependency gate passed. |
| osv-scanner | CVE-2025-71176 | fix | The first of two duplicate OSV results identifies pytest 8.4.1 in requirements.txt. The dependency was upgraded to pytest 9.0.3 in ae1069c; later CI scans pass. |
| osv-scanner | CVE-2025-71176 | fix | The second result is the same pytest advisory and affected version as the first, not another package. It is resolved by the same pinned upgrade to pytest 9.0.3 in ae1069c. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | This is a genuine hardening issue: the service process runs as root. The SQLite database is stored in the persistent named volume at /data; changing runtime identity without migrating ownership of existing volume data can break persistence. Keep this risk explicit and address it with a tested volume-ownership migration. |
| semgrep | python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query | accept | This finding is in semgrep/rules.py, the intentional unsafe positive fixture for the repository's custom SQL rule. It is scanner test data and is not imported or used by the running service. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | At src/main.py:178, the request controls only q, which is URL-encoded. The destination host comes from the deployment's KB_INDEX_URL setting, not from request input, so a client cannot redirect this request to an arbitrary URL. |
| semgrep | python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query | false-positive | At src/main.py:341, the SQL structure is assembled from internal state and fixed field names; ticket values are passed separately as SQLite parameters. The rule flags the dynamic statement construction but request data is not interpolated into SQL. |
| trivy | CVE-2025-71176 | fix | The receipted filesystem scan found pytest 8.4.1 in requirements.txt. The pin was upgraded to pytest 9.0.3 in ae1069c, the fixed version reported by Trivy; the later dependency and image gates passed. |

## Bake-off

The receipted canary has nine labelled defects. Gitleaks found all three labelled secrets and no false positives
(precision 1.0000, recall 0.3333, F1 0.5000). Grype and OSV-Scanner each found both vulnerable dependency pins
without a false positive (precision 1.0000, recall 0.2222, F1 0.3636). Trivy found four defects with no false
positives (precision 1.0000, recall 0.4444, F1 0.6154), the strongest F1 in this set. Semgrep found four defects
but also reported three false positives (precision 0.5714, recall 0.4444, F1 0.5000). None of the tools found all
nine defects, so a clean scan cannot establish that the canary is safe.

For CI gates, keep Gitleaks on secrets and Trivy on dependencies: their measured precision is perfect on this
small seeded set, and both are already configured as gates. Keep Semgrep as a review signal rather than a
blocking gate because its false positives would create avoidable alert fatigue. Grype and OSV-Scanner provide
useful second opinions on dependencies but have lower recall here. These numbers describe only this labelled
canary, not production coverage; seeded examples are easier for scanners to detect than unknown defects, and the
results should guide tool selection rather than be treated as a security guarantee.
