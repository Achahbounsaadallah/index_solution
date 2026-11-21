"""SpruceLedge scope matcher: label-trie index (R1-R7 of inputs/policy.md)."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import typing


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


class _Node:
    __slots__ = ("children", "exact", "wild")

    def __init__(self) -> None:
        self.children: dict[str, "_Node"] = {}
        self.exact = None  # (size, is_exclude, rule_id, action)
        self.wild = None


def _prefer(candidate, current) -> bool:
    """R4: more labels, then exclude, then lowest id."""
    if current is None:
        return True
    if candidate[0] != current[0]:
        return candidate[0] > current[0]
    if candidate[1] != current[1]:
        return candidate[1]  # True = exclude wins
    return candidate[2] < current[2]


def build_index(rules) -> tuple[_Node, int]:
    root, touches = _Node(), 0
    for rule_id, labels, wildcard, action in rules:
        node = root
        for label in reversed(labels):
            touches += 1  # one rule label stored
            child = node.children.get(label)
            if child is None:
                child = node.children[label] = _Node()
            node = child
        entry = (len(labels), action == "exclude", rule_id, action)
        if wildcard is True:
            if _prefer(entry, node.wild):
                node.wild = entry
        elif _prefer(entry, node.exact):
            node.exact = entry
    return root, touches


def classify(root: _Node, labels: list[str]):
    node, best, touches, total = root, None, 0, len(labels)
    for depth, label in enumerate(reversed(labels), start=1):
        touches += 1  # one host label examined
        node = node.children.get(label)
        if node is None:
            break
        if depth < total and node.wild is not None and _prefer(node.wild, best):
            best = node.wild  # wildcard needs at least one more label
        if depth == total and node.exact is not None and _prefer(node.exact, best):
            best = node.exact
    return best, touches


def match_scope_counted(payload: dict[str, typing.Any], arguments: argparse.Namespace | None = None):
    rules = validate_rules(payload)
    root, touches = build_index(rules)
    decisions = {}
    for raw in payload["hosts"]:
        host = normalize(raw)
        if host in decisions:
            continue
        labels = labels_of(host)
        if labels is None:
            decisions[host] = {"host": host, "status": "invalid", "rule": None}
            continue
        best, used = classify(root, labels)
        touches += used
        if best is None:
            decisions[host] = {"host": host, "status": "unmatched", "rule": None}
        else:
            status = "excluded" if best[3] == "exclude" else "in_scope"
            decisions[host] = {"host": host, "status": status, "rule": best[2]}
    rows = [decisions[host] for host in sorted(decisions)]
    summary = {"hosts": len(payload["hosts"]), "distinct": len(rows)}
    for status in ("in_scope", "excluded", "unmatched", "invalid"):
        summary[status] = sum(1 for row in rows if row["status"] == status)
    return {"decisions": rows, "summary": summary}, touches


def match_scope(payload: dict[str, typing.Any], arguments: argparse.Namespace | None = None) -> dict[str, typing.Any]:
    return match_scope_counted(payload, arguments)[0]


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