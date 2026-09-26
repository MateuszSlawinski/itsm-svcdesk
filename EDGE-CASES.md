---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 90% - counts checked against the service response for the published practice fixture -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three successful production commit pairs have a commit timestamp later than the deployment.
- What a default definition would have done: It might discard these pairs or include negative values in the median.
- Why the rule is defensible: The delivery event still occurred, while zero avoids claiming negative elapsed time.

## E2 - a revert of a revert

- What the log contains: Two revert commits point through earlier revert commits to the original changes.
- What a default definition would have done: It might count every revert as a new independent change.
- Why the rule is defensible: Reverts undo prior work; resolving the chain preserves the identity of the original change.

## E3 - a hotfix that never touched `main`

- What the log contains: Four distinct non-main commit SHAs were included in production deployments in the window.
- What a default definition would have done: It might ignore all hotfix branches and omit changes that reached users.
- Why the rule is defensible: Production exposure, not a branch naming convention, determines whether work was delivered.

## E4 - a deployment with zero linked commits

- What the log contains: Four production deployments have an empty commits array in the observation window.
- What a default definition would have done: It might drop these events or divide a metric by delivered changes only.
- Why the rule is defensible: A production release happened even when its source change metadata was missing.

## E5 - a deployment that failed and never recovered

- What the log contains: One in-window production failure has no covering resolved incident.
- What a default definition would have done: It might invent a recovery time at the window boundary or omit the failure.
- Why the rule is defensible: An unresolved outage has no observed recovery duration but remains an operational failure.

## E6 - overlapping incidents

- What the log contains: Eleven unordered pairs of incident intervals intersect in the practice log.
- What a default definition would have done: It might merge the incidents or sum their overlapping wall-clock time.
- Why the rule is defensible: Recovery belongs to each failed deployment and the same period must not be double-counted.

## Gaming demonstration

The gaming log improves `deployment_rework_rate` by exploiting R-15: reclassifying deployments as planned and removing
their incident links suppresses the numerator. A team rewarded only for a lower rework rate could make that change
to protect its dashboard. Meanwhile, the same base production deployments are delayed by five days, which increases
the true lead time of existing work or leaves late changes undelivered. The dashboard rewards the team for tidier
classification even though customers wait longer for fixes.
