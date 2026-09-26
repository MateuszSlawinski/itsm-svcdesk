# ai-generated: 95% - implemented from the published Lab 2 metric rules and checked against the practice fixture
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import re


class MetricInputError(ValueError):
    pass


_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def parse_instant(value):
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        raise MetricInputError("timestamps must be RFC 3339 instants with an offset")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise MetricInputError("invalid RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise MetricInputError("timestamps must include an offset")
    return parsed.astimezone(timezone.utc)


def _required_string(event, field):
    value = event.get(field)
    if not isinstance(value, str) or not value:
        raise MetricInputError(f"{field} must be a non-empty string")
    return value


def _string_list(event, field):
    value = event.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise MetricInputError(f"{field} must be an array of non-empty strings")
    return value


def deduplicate_events(events):
    if not isinstance(events, list):
        raise MetricInputError("events must be an array")
    seen = set()
    unique = []
    for event in events:
        if not isinstance(event, dict):
            raise MetricInputError("each event must be an object")
        event_id = _required_string(event, "event_id")
        if len(event_id) > 64:
            raise MetricInputError("event_id must contain 1 to 64 characters")
        if event_id in seen:
            continue
        seen.add(event_id)
        unique.append(event)
    return unique


def validate_events(events):
    unique = deduplicate_events(events)
    commits = {}
    deployments = {}
    incidents = {}
    parsed = []

    for event in unique:
        event_type = event.get("type")
        if event_type not in ("commit", "deployment", "incident"):
            raise MetricInputError("type must be commit, deployment or incident")
        at = parse_instant(event.get("at"))
        parsed.append((event, at))

        if event_type == "commit":
            sha = _required_string(event, "sha")
            _required_string(event, "branch")
            change_id = event.get("change_id")
            reverts = event.get("reverts")
            if change_id is not None and (not isinstance(change_id, str) or not change_id):
                raise MetricInputError("change_id must be a non-empty string or null")
            if reverts is not None and (not isinstance(reverts, str) or not reverts):
                raise MetricInputError("reverts must be a non-empty string or null")
            if (reverts is None) == (change_id is None):
                raise MetricInputError("commits need a change_id unless they are revert commits")
            if sha in commits:
                raise MetricInputError("commit sha values must be unique")
            commits[sha] = (event, at)

        elif event_type == "deployment":
            deployment_id = _required_string(event, "deployment_id")
            _required_string(event, "environment")
            if event.get("outcome") not in ("success", "failure"):
                raise MetricInputError("deployment outcome must be success or failure")
            _string_list(event, "commits")
            if not isinstance(event.get("unplanned"), bool):
                raise MetricInputError("unplanned must be a boolean")
            caused_by = event.get("caused_by")
            if caused_by is not None and (not isinstance(caused_by, str) or not caused_by):
                raise MetricInputError("caused_by must be a non-empty string or null")
            if deployment_id in deployments:
                raise MetricInputError("deployment_id values must be unique")
            deployments[deployment_id] = (event, at)

        else:
            incident_id = _required_string(event, "incident_id")
            if event.get("phase") not in ("opened", "resolved"):
                raise MetricInputError("incident phase must be opened or resolved")
            _string_list(event, "deployments")
            phases = incidents.setdefault(incident_id, {})
            phase = event["phase"]
            if phase in phases:
                raise MetricInputError("an incident can have at most one event per phase")
            phases[phase] = (event, at)

    for event, _ in parsed:
        if event["type"] == "commit":
            if event["reverts"] is not None and event["reverts"] not in commits:
                raise MetricInputError("reverts references a sha not present in the log")
        elif event["type"] == "deployment":
            if any(sha not in commits for sha in event["commits"]):
                raise MetricInputError("deployment commits reference a sha not present in the log")
            if event["caused_by"] is not None and event["caused_by"] not in incidents:
                raise MetricInputError("caused_by references an incident not present in the log")
        else:
            if any(deployment_id not in deployments for deployment_id in event["deployments"]):
                raise MetricInputError("incident deployments reference an id not present in the log")

    for phases in incidents.values():
        if "resolved" in phases and "opened" not in phases:
            raise MetricInputError("a resolved incident must also have an opened event")

    return parsed, commits, deployments, incidents


def _round(value, places=0):
    quantum = Decimal(1).scaleb(-places)
    return Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)


def _seconds(delta):
    return Decimal(str(delta.total_seconds()))


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        median = ordered[middle]
    else:
        median = (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    return int(_round(median))


def _ratio(numerator, denominator):
    if denominator == 0:
        return None
    return float(_round(Decimal(numerator) / Decimal(denominator), 6))


def _resolve_changes(commits):
    resolved = {}

    def resolve(sha, visiting):
        if sha in resolved:
            return resolved[sha]
        if sha in visiting:
            raise MetricInputError("revert references contain a cycle")
        event, _ = commits[sha]
        if event["reverts"] is None:
            change_id = event["change_id"]
        else:
            change_id = resolve(event["reverts"], visiting | {sha})
        resolved[sha] = change_id
        return change_id

    for sha in commits:
        resolve(sha, set())
    return resolved


def compute_metrics(body):
    if not isinstance(body, dict):
        raise MetricInputError("request body must be an object")
    window = body.get("window")
    if not isinstance(window, dict):
        raise MetricInputError("window is required")
    from_text = window.get("from")
    to_text = window.get("to")
    start = parse_instant(from_text)
    end = parse_instant(to_text)
    if end <= start:
        raise MetricInputError("window.to must be after window.from")

    parsed, commits, deployments, incidents = validate_events(body.get("events"))
    changes_by_sha = _resolve_changes(commits)
    window_deployments = [
        (event, at)
        for event, at in parsed
        if event["type"] == "deployment"
        and event["environment"] == "production"
        and start <= at < end
    ]
    window_deployments.sort(key=lambda pair: (pair[1], pair[0]["deployment_id"]))

    successful = [(event, at) for event, at in window_deployments if event["outcome"] == "success"]
    failed = [(event, at) for event, at in window_deployments if event["outcome"] == "failure"]
    deployment_count = len(window_deployments)

    first_deployment_for_sha = {}
    production_window_shas = set()
    changes_delivered_at = {}
    lead_pairs = []
    negative_lead_pairs = 0
    for deployment, deployed_at in successful:
        for sha in deployment["commits"]:
            production_window_shas.add(sha)
            first_deployment_for_sha.setdefault(sha, (deployment, deployed_at))
            change_id = changes_by_sha[sha]
            if change_id not in changes_delivered_at or deployed_at < changes_delivered_at[change_id]:
                changes_delivered_at[change_id] = deployed_at

    for sha, (_, deployed_at) in first_deployment_for_sha.items():
        _, committed_at = commits[sha]
        duration = _seconds(deployed_at - committed_at)
        if duration < 0:
            negative_lead_pairs += 1
            duration = Decimal(0)
        lead_pairs.append(duration)

    for deployment, _ in window_deployments:
        production_window_shas.update(deployment["commits"])

    change_first_commit = {}
    for sha, (commit, committed_at) in commits.items():
        change_id = changes_by_sha[sha]
        if change_id not in change_first_commit or committed_at < change_first_commit[change_id]:
            change_first_commit[change_id] = committed_at

    truth_lead_times = []
    for change_id, delivered_at in changes_delivered_at.items():
        duration = _seconds(delivered_at - change_first_commit[change_id])
        truth_lead_times.append(max(duration, Decimal(0)))

    recovered_durations = []
    open_failures = 0
    incident_by_deployment = {}
    for incident_id, phases in incidents.items():
        opened = phases.get("opened")
        if opened is None:
            continue
        event, opened_at = opened
        for deployment_id in event["deployments"]:
            candidate = (opened_at, incident_id, phases)
            current = incident_by_deployment.get(deployment_id)
            if current is None or (candidate[0], candidate[1].encode()) < (current[0], current[1].encode()):
                incident_by_deployment[deployment_id] = candidate

    for deployment, deployed_at in failed:
        covering = incident_by_deployment.get(deployment["deployment_id"])
        resolved = covering[2].get("resolved") if covering else None
        if resolved is None:
            open_failures += 1
        else:
            recovery = _seconds(resolved[1] - deployed_at)
            recovered_durations.append(max(recovery, Decimal(0)))

    overlaps = 0
    incident_intervals = []
    for incident_id, phases in incidents.items():
        opened = phases.get("opened")
        if opened is None:
            continue
        opened_at = opened[1]
        resolved = phases.get("resolved")
        interval_end = resolved[1] if resolved else end
        if interval_end > opened_at:
            incident_intervals.append((incident_id, opened_at, interval_end))
    for index, (_, a_start, a_end) in enumerate(incident_intervals):
        for _, b_start, b_end in incident_intervals[index + 1:]:
            if a_start < b_end and b_start < a_end:
                overlaps += 1

    changes = set(changes_by_sha.values())
    non_main = {
        sha for sha in production_window_shas
        if commits[sha][0]["branch"] != "main"
    }
    empty_deployments = sum(not event["commits"] for event, _ in window_deployments)
    collapsed_reverts = sum(event["reverts"] is not None for event, _ in parsed if event["type"] == "commit")
    rework = sum(event["unplanned"] and event["caused_by"] is not None for event, _ in window_deployments)
    days = _seconds(end - start) / Decimal(86400)

    return {
        "spec_version": "1.0.0",
        "window": {"from": from_text, "to": to_text},
        "deployment_frequency_per_day": float(_round(Decimal(deployment_count) / days, 6)),
        "change_lead_time_seconds_p50": _median(lead_pairs),
        "failed_deployment_recovery_time_seconds_p50": _median(recovered_durations),
        "change_fail_rate": _ratio(len(failed), deployment_count),
        "deployment_rework_rate": _ratio(rework, deployment_count),
        "counts": {
            "deployments": deployment_count,
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": len(recovered_durations),
            "open_failures": open_failures,
            "rework_deployments": rework,
            "lead_time_pairs": len(lead_pairs),
            "changes": len(changes),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_pairs,
            "deployments_without_commits": empty_deployments,
            "commits_never_on_main": len(non_main),
            "revert_chains_collapsed": collapsed_reverts,
            "overlapping_incident_pairs": overlaps,
        },
        "ground_truth": {
            "changes_delivered": len(changes_delivered_at),
            "true_change_lead_time_seconds_p50": _median(truth_lead_times),
        },
    }
