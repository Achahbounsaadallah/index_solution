"""Write a deterministic synthetic scope input to stdout.

Usage: python3 inputs/generate_large.py --hosts 50000 --seed 7 > large.json
The same --hosts and --seed always produce the same bytes. Python standard library only.
"""
from __future__ import annotations

import argparse
import json
import random
import sys

ZONES = ("shop", "docs", "api", "cdn", "pay", "ops")
WORDS = ("a", "b", "img", "db", "vpn", "edge", "stage", "eu", "us", "internal", "op")


def name(rng: random.Random, depth: int, zones: tuple[str, ...] = ZONES) -> str:
    parts = [rng.choice(WORDS) for _ in range(depth)]
    return ".".join(parts + [rng.choice(zones), "example", "test"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic scope input.")
    parser.add_argument("--hosts", type=int, required=True, help="host entries, 0 to 300000")
    parser.add_argument("--seed", type=int, default=7)
    arguments = parser.parse_args()
    if arguments.hosts < 0 or arguments.hosts > 300000:
        print("error: --hosts must be between 0 and 300000", file=sys.stderr)
        return 2
    rng = random.Random(arguments.seed)
    rules = []
    for index in range(400):
        pattern = name(rng, rng.randint(0, 3))
        if rng.random() < 0.6:
            pattern = "*." + pattern
        if rng.random() < 0.2:
            pattern = pattern.upper() + "."
        rules.append({"id": f"g{index:03d}", "pattern": pattern, "action": "exclude" if rng.random() < 0.3 else "include"})
    hosts = []
    for _ in range(arguments.hosts):
        host = name(rng, rng.randint(0, 6), ZONES + ("mail", "blog"))
        if rng.random() < 0.05:
            host = host.replace(".", "..", 1)
        if rng.random() < 0.1:
            host = host.capitalize() + "."
        hosts.append(host)
    json.dump({"rules": rules, "hosts": hosts}, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
