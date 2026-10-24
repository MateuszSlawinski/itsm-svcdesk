---
lab4_postmortem:
  ticket: "50ceffde-fa49-40b3-b4ca-957734d74bf7"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T06:36:23Z
  detection: 2026-10-12T06:39:19Z
  acknowledgement: 2026-10-12T06:40:09Z
  recovery: 2026-10-12T06:44:19Z
  mttd_seconds: 176
  mtta_seconds: 50
  mttr_seconds: 476
  identified_flags: [paymentFailure, loadGeneratorFloodHomepage]
---
<!-- ai-generated: 100% - drafted with GitHub Copilot from the assigned recording and Lab 4 rules -->

# Postmortem: Checkout errors during a feature-flag incident

## Date

The incident occurred on 12 October 2026. This postmortem was prepared on 24 October 2026 from the assigned recording.

## Authors

Prepared by the on-call responder role for the service desk exercise; the recording was supplied by the course.

## Status

Complete for the recorded evidence; follow-up actions are proposed and have not been tracked outside this exercise.

## Summary

Checkout requests began failing after the recorded feature-flag onset. The detecting alert recovered 7 minutes and 56 seconds after onset.

## Impact

At 06:39:19Z, the recorded alert detected checkout failures. At 06:39:30Z, the five-minute checkout server error ratio was about 13.4%; at 06:43:00Z it was 25%. The five-minute 99th-percentile checkout server latency stayed near 50 ms, so the measured checkout symptom was errors rather than elevated checkout latency. The same observation showed frontend spans rising from about 3.74/s at 06:35Z to 37.02/s at 06:39:30Z, and frontend-proxy spans from about 1.95/s to 21.17/s.

## Root Causes

Payment `charge` errors and checkout `PlaceOrder` errors rose together, consistent with the `paymentFailure` flag. Frontend and frontend-proxy request volume rose by roughly an order of magnitude, consistent with `loadGeneratorFloodHomepage`. These two flags are supported by separate metric evidence; the available recorded telemetry does not justify naming a third flag.

## Trigger

The recorded fault became active at 06:36:23Z on 12 October 2026. The supplied snapshot records the onset but does not expose the feature-flag keys directly.

## Resolution

The recorded incident recovered at 06:44:19Z, when the detecting checkout error alert ended. The evidence supports mitigating the payment errors and the excessive homepage load by disabling the corresponding failing flags. The supplied recording does not include a per-flag rollback log, so an exact command order or per-flag timestamp cannot be claimed.

## Detection

`ShopCheckoutErrors` detected the incident at 06:39:19Z, 176 seconds after onset. The P1 ticket was acknowledged at 06:40:09Z, 50 seconds after detection. Without the page, the on-call would have had to discover failed orders through customer reports or the service dashboards.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Alert on checkout server error ratio and verify it remains quiet on the healthy baseline. | prevent | Service owner | ITSM-4101 |
| Add a dashboard panel for frontend request volume so homepage floods are visible during triage. | mitigate | On-call team | ITSM-4102 |

## Lessons Learned

### What went well

The checkout error alert identified the user-facing failure, and the acknowledgement followed detection within one minute.

### What went wrong

The recorded investigator produced several overlapping payment-related hypotheses, and the telemetry did not identify the full three-flag fault with certainty.

### Where we got lucky

The recorded checkout error run ended within eight minutes of onset, and the ticket remained traceable to the alert that prompted it.

## Timeline

- 06:36:23Z - the recorded fault onset.
- 06:39:19Z - `ShopCheckoutErrors` began firing and detected the incident.
- 06:40:09Z - the P1 ticket was acknowledged.
- 06:44:19Z - the detecting alert recovered.
- During post-incident review, transcript hypotheses H1-H4 were evaluated against payment `charge`, checkout `PlaceOrder`, and checkout-to-payment error metrics; they were not used as live mitigation instructions.

## Supporting information

The assigned `incident/tsdb-snapshot.tar.gz` and `incident/ticket.json` are the source artifacts. The `itsmlab incident 4` recomputation reports the four instants and durations above. The AI hypotheses and their filtering PromQL checks are recorded in `ai-rca-eval.json` and `ai-rca/transcript.md`.

## Problem record

- Incident record: 50ceffde-fa49-40b3-b4ca-957734d74bf7
- Root cause: Recorded payment charge failures accompanied by a substantial frontend request-volume increase.
- Known error: Checkout orders failed while the payment and checkout services emitted error spans.
- Workaround: Disable the failing payment and homepage-load feature flags, then confirm the checkout error alert resolves.
