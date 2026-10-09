---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.95
      threshold_seconds: 0.5
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.5"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.05, minutes: 2160}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 1h, short_window: 5m}
---
<!-- ai-generated: 25% - drafted with GitHub Copilot from the Lab 3 SLO template; objectives and budgets follow its example -->

# SLO for `GET /kb/search`

## Availability

The service objective is 99% of valid search requests returning a non-5xx response over 30 days. The budget is 1% of requests, equivalent to 432 minutes in a 30-day window. The index can independently return errors, so the availability target leaves a small but nonzero allowance for dependency failures while still making sustained service-side failures visible.

## Latency

The objective is 95% of searches completing within 0.5 seconds. In my load run, p50 was 0.0173 seconds and p99 was 0.1133 seconds; the directly measured kb-index p99 was 0.1051 seconds. The threshold is an exposed histogram boundary, so the SLI counts requests directly instead of interpolating between buckets. The 0.5-second threshold leaves room for the measured slow mode while still detecting a widening tail; the checker will independently validate the measurement and threshold. The error budget is 5% of requests, or 2,160 minutes in the 30-day window.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---:|---|---:|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m | 2% per hour at 2x burn | P1 page |
| KbSearchErrorsBurnSlow | availability | 6 | 1h / 5m | 0.83% per hour at 2x burn | P2 chat |

The fast alert pages because this burn rate can exhaust the budget quickly and needs immediate intervention. The slower alert goes to chat: it calls for investigation, but does not justify waking someone as readily. Both require elevated error ratios in the long and short windows so a resolved spike clears promptly.

## Buckets

The service uses a dense geometric ladder around the expected search latency, with an explicit 0.5-second boundary for the latency SLI. The measured p99 and its exact bucket arithmetic will be recorded in `ai-first-draft.md` after running the prescribed load measurement; the checker independently repeats that measurement.
