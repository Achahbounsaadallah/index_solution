"""Exercise starter; see README for the existing behavior or absent feature."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import typing

RULE_CHECKS = 0

def normalize(name: str) -> str:
    name = name.lower()
    return name[:-1] if name.endswith(".") else name


def labels_of(name: str) -> list[str] | None:
    parts = name.split(".")
    if any(part == "" or "*" in part for part in parts):
        return None
    return parts


def validate_rules(payload: dict[str, typing.Any]) -> list[tuple[str, list[str], bool, str]]:
    rules = payload.get("rules")
    if isinstance(rules, list) is False or isinstance(payload.get("hosts"), list) is False:
        raise ValueError("rules and hosts must be lists")
    parsed = []
    seen: set[str] = set()
    for rule in rules:
        if isinstance(rule, dict) is False or isinstance(rule.get("id"), str) is False or rule["id"] == "":
            raise ValueError("each rule needs a nonempty string id")
        if rule["id"] in seen:
            raise ValueError(f"duplicate rule id {rule['id']}")
        seen.add(rule["id"])
        if rule.get("action") not in ("include", "exclude") or isinstance(rule.get("pattern"), str) is False:
            raise ValueError(f"rule {rule['id']} needs a string pattern and include/exclude action")
        pattern = normalize(rule["pattern"])
        wildcard = pattern.startswith("*.")
        labels = labels_of(pattern[2:] if wildcard is True else pattern)
        if labels is None:
            raise ValueError(f"rule {rule['id']} has an invalid pattern")
        parsed.append((rule["id"], labels, wildcard, rule["action"]))
    if any(isinstance(host, str) is False for host in payload["hosts"]):
        raise ValueError("hosts must be strings")
    return parsed


def match_scope(payload: dict[str, typing.Any], arguments: argparse.Namespace) -> dict[str, typing.Any]:
    rules = validate_rules(payload)
    decisions = {}
    for raw in payload["hosts"]:
        host = normalize(raw)
        if host in decisions:
            continue
        labels = labels_of(host)
        if labels is None:
            decisions[host] = {"host": host, "status": "invalid", "rule": None}
            continue
        best = None
        for rule_id, rule_labels, wildcard, action in rules:
            global RULE_CHECKS
            RULE_CHECKS += 1
            size = len(rule_labels)
            if wildcard is True:
                matched = len(labels) > size and labels[-size:] == rule_labels
            else:
                matched = labels == rule_labels
            if matched is True:
                rank = (size, action == "exclude")
                if best is None or rank > best[0] or (rank == best[0] and rule_id < best[1]):
                    best = (rank, rule_id, action)
        if best is None:
            decisions[host] = {"host": host, "status": "unmatched", "rule": None}
        else:
            status = "excluded" if best[2] == "exclude" else "in_scope"
            decisions[host] = {"host": host, "status": status, "rule": best[1]}
    rows = [decisions[host] for host in sorted(decisions)]
    summary = {"hosts": len(payload["hosts"]), "distinct": len(rows)}
    for status in ("in_scope", "excluded", "unmatched", "invalid"):
        summary[status] = sum(1 for row in rows if row["status"] == status)
    return {"decisions": rows, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide whether each host is in scope under include and exclude rules.")
    parser.add_argument("--input", default="inputs/primary.json", help="UTF-8 fixture JSON")
    arguments = parser.parse_args()
    try:
        payload = json.loads(pathlib.Path(arguments.input).read_text(encoding="utf-8"))
        if isinstance(payload, dict) is False:
            raise ValueError("input must be a JSON object")
        result = match_scope(payload, arguments)
        print(json.dumps(result, indent=2, sort_keys=True))
    except NotImplementedError as error:
        print(str(error), file=sys.stderr)
        return 3
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
