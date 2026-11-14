# ai-generated: 100% - implemented the published SARIF-to-confusion-matrix rules in CI-SPEC.md P-14 to P-28
"""Compute per-tool confusion matrices from SARIF and labelled defects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote


_CLASS_CWES = {
    "secret": {259, 260, 321, 798},
    "injection": {74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336},
    "deserialization": {502},
    "weak-crypto": {261, 326, 327, 328, 330, 331, 338, 759, 760, 916},
    "insecure-transport": {295, 297, 319, 322, 757},
    "path-traversal": {22, 23, 35, 36, 73},
    "ssrf": {918},
    "vulnerable-dependency": {937, 1035, 1104, 1395},
    "misconfiguration": {16, 215, 250, 489, 668, 732, 1188},
    "access-control": {284, 285, 639, 862, 863},
}
_SEMGREP_NAMES = {
    "semgrep",
    "semgrep oss",
    "semgrep ce",
    "semgrep community edition",
    "semgrep pro",
}
_DEPENDENCY_TOKEN = re.compile(r"[A-Za-z0-9._-]+")
_CWE_TAG = re.compile(r"(?i)(?<![A-Za-z0-9])CWE-(\d+)")


def _items(value: object) -> list:
    return value if isinstance(value, list) else []


def _tool_id(run: dict) -> str:
    tool = run.get("tool")
    driver = tool.get("driver") if isinstance(tool, dict) else None
    name = driver.get("name") if isinstance(driver, dict) else None
    if not isinstance(name, str) or not name.strip():
        return "unknown"

    normalized = name.strip().lower()
    if normalized in {"trivy", "grype", "osv-scanner", "gitleaks"}:
        return normalized
    if normalized in _SEMGREP_NAMES:
        return "semgrep"
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "unknown"


def _path_in_set(uri: str, set_root: str) -> str | None:
    path = unquote(uri, encoding="utf-8", errors="replace")
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]

    components = path.split("/")
    root_positions = [index for index, component in enumerate(components) if component == set_root]
    if not root_positions:
        return None
    return "/".join(components[root_positions[-1] :])


def _result_location(result: dict, set_root: str) -> tuple[str, int | None, int | None] | None:
    locations = _items(result.get("locations"))
    if not locations or not isinstance(locations[0], dict):
        return None
    physical = locations[0].get("physicalLocation")
    if not isinstance(physical, dict):
        return None
    artifact = physical.get("artifactLocation")
    uri = artifact.get("uri") if isinstance(artifact, dict) else None
    if not isinstance(uri, str) or not uri:
        return None

    path = _path_in_set(uri, set_root)
    if path is None:
        return None

    region = physical.get("region")
    region = region if isinstance(region, dict) else {}
    start = region.get("startLine")
    if type(start) is not int or start < 1:
        return path, None, None
    end = region.get("endLine")
    if type(end) is not int or end < start:
        end = start
    return path, start, end


def _properties_tags(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    properties = value.get("properties")
    if not isinstance(properties, dict):
        return []
    return [tag for tag in _items(properties.get("tags")) if isinstance(tag, str)]


def _matched_classes(tool_id: str, result: dict, rule: dict | None) -> set[str]:
    properties = result.get("properties")
    own_class = properties.get("class") if isinstance(properties, dict) else None
    if isinstance(own_class, str) and own_class in _CLASS_CWES:
        return {own_class}

    if tool_id == "gitleaks":
        return {"secret"}
    if tool_id in {"grype", "osv-scanner"}:
        return {"vulnerable-dependency"}
    if tool_id == "trivy":
        trivy_classes = {
            "vulnerability": "vulnerable-dependency",
            "secret": "secret",
            "misconfiguration": "misconfiguration",
        }
        found = {
            trivy_classes[tag.lower()]
            for tag in _properties_tags(rule)
            if tag.lower() in trivy_classes
        }
        if found:
            return found

    cwe_numbers = {
        int(match.group(1))
        for tag in _properties_tags(result) + _properties_tags(rule)
        for match in _CWE_TAG.finditer(tag)
    }
    return {
        class_name
        for class_name, numbers in _CLASS_CWES.items()
        if cwe_numbers.intersection(numbers)
    } or {"other"}


def _rule_for_result(run: dict, result: dict) -> dict | None:
    result_rule_id = result.get("ruleId")
    if result_rule_id is None:
        return None
    tool = run.get("tool")
    driver = tool.get("driver") if isinstance(tool, dict) else None
    rules = _items(driver.get("rules")) if isinstance(driver, dict) else []
    for candidate in rules:
        if isinstance(candidate, dict) and candidate.get("id") == result_rule_id:
            return candidate
    return None


def _has_empty_suppressions(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, (str, list, dict)):
        return len(value) == 0
    return False


def _canonical_package(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def _dependency_names(result: dict) -> set[str]:
    message = result.get("message")
    text = message.get("text") if isinstance(message, dict) else None
    if not isinstance(text, str):
        return set()
    return {
        _canonical_package(token.strip("._-"))
        for token in _DEPENDENCY_TOKEN.findall(text)
        if token.strip("._-")
    }


def _matches_defect(
    defect: dict,
    file_path: str,
    start_line: int | None,
    end_line: int | None,
    classes: set[str],
    dependency_names: set[str],
) -> bool:
    defect_class = defect.get("class")
    if defect.get("file") != file_path or defect_class not in classes:
        return False
    if defect_class == "vulnerable-dependency":
        package = defect.get("package")
        return (
            isinstance(package, str)
            and _canonical_package(package) in dependency_names
        )
    if start_line is None or end_line is None:
        return False
    return start_line <= defect["end_line"] and defect["start_line"] <= end_line


def _accepted_result(result: dict) -> bool:
    kind = result.get("kind")
    return (kind is None or kind == "fail") and _has_empty_suppressions(
        result.get("suppressions")
    )


def confusion_matrix(labels: dict, sarif_documents: list[dict]) -> dict:
    """Return the P-21 confusion counts and P-22 scores for each SARIF tool."""
    defects = labels["defects"]
    set_root = labels["set"]
    tools: dict[str, dict] = {}

    for document in sarif_documents:
        for run in _items(document.get("runs")):
            if not isinstance(run, dict):
                continue
            tool_id = _tool_id(run)
            tool = tools.setdefault(
                tool_id,
                {"matched": set(), "false_positives": set()},
            )
            for result in _items(run.get("results")):
                if not isinstance(result, dict) or not _accepted_result(result):
                    continue
                location = _result_location(result, set_root)
                if location is None:
                    continue
                file_path, start_line, end_line = location
                rule = _rule_for_result(run, result)
                classes = _matched_classes(tool_id, result, rule)
                dependency_names = _dependency_names(result)
                matches = {
                    index
                    for index, defect in enumerate(defects)
                    if _matches_defect(
                        defect,
                        file_path,
                        start_line,
                        end_line,
                        classes,
                        dependency_names,
                    )
                }
                if matches:
                    tool["matched"].update(matches)
                else:
                    rule_id = result.get("ruleId")
                    fp_key = (
                        rule_id if isinstance(rule_id, str) else None,
                        file_path,
                        start_line,
                        end_line,
                    )
                    tool["false_positives"].add(fp_key)

    output_tools = {}
    for tool_id, counts in tools.items():
        true_positives = len(counts["matched"])
        false_positives = len(counts["false_positives"])
        false_negatives = len(defects) - true_positives
        precision_denominator = true_positives + false_positives
        recall_denominator = true_positives + false_negatives
        f1_denominator = 2 * true_positives + false_positives + false_negatives
        output_tools[tool_id] = {
            "tp": true_positives,
            "fp": false_positives,
            "fn": false_negatives,
            "precision": (
                round(true_positives / precision_denominator, 4)
                if precision_denominator
                else None
            ),
            "recall": (
                round(true_positives / recall_denominator, 4)
                if recall_denominator
                else None
            ),
            "f1": (
                round(2 * true_positives / f1_denominator, 4)
                if f1_denominator
                else None
            ),
        }

    return {"set": set_root, "defects": len(defects), "tools": output_tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)"
    )
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8") as file:
        labels = json.load(file)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8") as file:
            documents.append(json.load(file))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
