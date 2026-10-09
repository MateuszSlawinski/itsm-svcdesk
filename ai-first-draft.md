---
lab3_first_draft:
  source: ai
  tool: "GitHub Copilot in VS Code, model not exposed, 10 October 2026"
  ladder: [0.001, 0.005, 0.01, 0.012, 0.0144, 0.01728, 0.020736, 0.024883, 0.02986, 0.035832, 0.042998, 0.051598, 0.061917, 0.074301, 0.089161, 0.106993, 0.128392, 0.15407, 0.184884, 0.221861, 0.266233, 0.31948, 0.383376, 0.460051, 0.5, 0.552061, 0.662474, 0.794968, 0.953962, 1.144755]
  verdict: confirmed
  evidence: {p99_seconds: 0.1133, bucket: [0.106993, 0.128392], relative_width: 0.189}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.1133, bucket: [0.04, 0.5], relative_width: 4.059}
---
<!-- ai-generated: 100% - written with GitHub Copilot; the prompt, answer and verdict arithmetic are recorded below -->

# The assistant's first draft, and two verdicts

## Prompt
Before measuring or designing the monitoring, recommend no more than 30 finite histogram boundaries in seconds for GET /kb/search and a multiwindow alert rule for its availability SLO. Give the exact ladder and the PromQL, burn rates, windows, for durations and severities; briefly explain the choices.

## Answer
Use this 30-boundary ladder in seconds: [0.001, 0.005, 0.01, 0.012, 0.0144, 0.01728, 0.020736, 0.024883, 0.02986, 0.035832, 0.042998, 0.051598, 0.061917, 0.074301, 0.089161, 0.106993, 0.128392, 0.15407, 0.184884, 0.221861, 0.266233, 0.31948, 0.383376, 0.460051, 0.5, 0.552061, 0.662474, 0.794968, 0.953962, 1.144755]. It is geometric around the expected p99 band, with an explicit 0.5-second threshold for the latency SLI. For a 99% availability objective, alert on the 5xx request ratio for route /kb/search, filtering both long and short windows. Use KbSearchErrorsBurnFast at burn rate 14.4 with 1h and 5m windows, for 1m, severity P1; its long and short ratios must both exceed 14.4 * (1 - 0.99). Use KbSearchErrorsBurnSlow at burn rate 6 with the same windows, for 2m, severity P2; both ratios must exceed 6 * (1 - 0.99). The fast alert pages on rapid budget consumption; the slower alert goes to chat. The short window makes the alerts clear promptly after the burn stops.

## Verdict on the draft ladder

The measured p99 was 0.1133 seconds. It falls in the bucket (0.106993, 0.128392], whose width is 0.021399 seconds and whose relative width is (0.128392 - 0.106993) / 0.1133 = 0.189. Since 0.021399 is below 20% of the measured p99 (0.022660 seconds), the ladder resolves the p99; verdict: confirmed. The checker will repeat the measurement independently.

## The draft alert rule

The assistant proposed two availability alerts that require both a long-window and short-window error ratio to exceed a constant burn threshold. I kept the two rates, windows, route filter and severities in `prometheus/alerts.yml`, and added promtool edge tests so timing and threshold changes are detected.

## Verdict on the instructor's flawed ladder

The same measured p99, 0.1133 seconds, lies in the instructor ladder's bucket (0.04, 0.5]. Its width is 0.46 seconds and relative width is 0.46 / 0.1133 = 4.059. The bucket is more than four times the p99, far above the 20% resolution limit; verdict: refuted.
