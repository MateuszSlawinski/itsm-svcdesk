---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 90% - drafted from the published requirements and aligned with the running implementation -->

# Decisions

<!--
How to fill this in (delete this comment when you are done):
- The three values in the front matter must be the ones your RUNNING service exhibits. The checker probes the
  service (checks 2.41, 2.35, 2.46) and compares them with this file (L1-CORE-4).
- Keep the three headings starting with "## C1", "## C2", "## C3" and the five bold labels in each section. Write
  at least 20 characters after every label; the lecturer reads this document, so write what you would say to
  the service owner, not the minimum.
- "Service owner": the role (never a person's name) who would sign this decision off, and why it is theirs.
- "Customer outcome": what the reporter or the organisation gets from this choice, in one or two sentences.
- Update the ai-generated line above to say how much of this text an AI wrote and how.
-->

## C1 - SLA clock for P1

**Decision:** P1 acknowledgement and resolution targets use the wall-clock, while P2-P4 targets use Warsaw business hours.

**Rejected alternative:** Applying business hours to P1 would delay an urgent outage raised after closing until the next working day.

**Reason:** R-13 requires pausing ordinary work outside office hours, but R-14 explicitly makes P1 urgent around the clock. Keeping one clock for both P1 targets avoids a surprising mixed policy.

**Service owner:** The service desk product owner signs this off because they own the operational SLA and escalation expectations.

**Customer outcome:** A critical outage is visible as late within minutes, regardless of the time of day, while lower priorities receive predictable working-time targets.

## C2 - Closed tickets and reopening

**Decision:** A resolved ticket may be reopened within seven days, but a closed ticket is immutable and requires a related new ticket.

**Rejected alternative:** Allowing closed tickets to reopen would make historical closure reports mutable and conflict with the requirements' explicit immutability rule.

**Reason:** R-09 makes closure a durable record, while R-10 and R-11 still require a bounded reopening window for a resolution that did not work. The implementation clears the resolution timestamp when reopening.

**Service owner:** The service desk product owner owns audit semantics and therefore decides when a case is considered final.

**Customer outcome:** Customers can report a failed fix promptly, and closed historical records remain trustworthy for reporting and compliance.

## C3 - VIP reporters and the priority matrix

**Decision:** VIP reporters raise matrix P3 and P4 tickets to P2; matrix P1 and P2 priorities remain unchanged.

**Rejected alternative:** Ignoring VIP status would leave executive-impacting reports at P4, while making every VIP ticket P1 would over-escalate routine requests.

**Reason:** This implements R-06's “never lower than P2” promise while preserving the impact/urgency matrix for serious incidents and keeping priority independent of a client-supplied field.

**Service owner:** The service desk product owner approves the escalation policy because it controls staffing and notification load.

**Customer outcome:** VIP requests are visible quickly without allowing reporter status to outrank a genuine P1 incident or distort the standard priority model.
