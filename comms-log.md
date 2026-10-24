---
lab4_comms:
  awareness: 2026-10-12T06:40:09Z
  detection: 2026-10-12T06:39:19Z
  classification: 2026-10-12T06:41:00Z
  nis2:
    early_warning_due: 2026-10-13T06:40:09Z
    notification_due: 2026-10-15T06:40:09Z
    notification_sent: 2026-10-12T10:00:00Z
    final_report_due: 2026-11-12T10:00:00Z
  ksc:
    early_warning_due: 2026-10-13T06:39:19Z
    notification_due: 2026-10-15T06:39:19Z
    notification_sent: 2026-10-12T10:00:00Z
    final_report_due: 2026-11-12T10:00:00Z
  dora:
    initial_due: 2026-10-12T10:41:00Z
    initial_sent: 2026-10-12T07:00:00Z
    intermediate_due: 2026-10-15T07:00:00Z
    intermediate_sent: 2026-10-14T12:00:00Z
    final_due: 2026-11-14T12:00:00Z
  log:
    - {at: 2026-10-12T07:00:00Z, to: financial supervisor, what: DORA initial notification}
    - {at: 2026-10-12T08:00:00Z, to: CSIRT, what: NIS2 and KSC early warning}
    - {at: 2026-10-12T10:00:00Z, to: CSIRT, what: NIS2 and KSC incident notification}
    - {at: 2026-10-14T12:00:00Z, to: financial supervisor, what: DORA intermediate report}
---
<!-- ai-generated: 100% - drafted with GitHub Copilot from the incident timeline and Lab 4 regulatory-clock rules -->

# Communications log: the regulators' clocks

## The three instants you defend

Awareness is 06:40:09Z, when the P1 ticket was acknowledged and the on-call had a confirmed user-impacting checkout incident. Detection is 06:39:19Z, when `ShopCheckoutErrors` first fired; the KSC clock starts at that earlier alert. Classification as major for this exercise is 06:41:00Z, after the on-call had the ticket and could assess the checkout and payment error evidence. This is a hypothetical exercise under the handout's assumption that the shop is in scope for NIS2, the Polish KSC act, and DORA; it is not a legal determination about a real organization.

## The log

At 07:00Z on 12 October, the financial supervisor would receive the DORA initial notification, well before its 10:41Z deadline. At 08:00Z, the CSIRT would receive the NIS2 and KSC early warning. At 10:00Z, the CSIRT would receive the NIS2 and KSC incident notification, ahead of both 72-hour deadlines. At 12:00Z on 14 October, the financial supervisor would receive the DORA intermediate report, before its 15 October 07:00Z deadline. The corresponding final-report deadlines are 12 November 10:00Z for NIS2 and KSC, and 14 November 12:00Z for DORA.
