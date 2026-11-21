# SpruceLedge scope matcher: label-index version

`app.py` decides whether each host is `in_scope`, `excluded`, `unmatched` or `invalid` under include/exclude rules (`inputs/policy.md`, R1-R7).

The original compared every host with every rule (hosts x rules). This version builds a **trie over reversed labels** once (`test -> example -> shop -> ...`), then classifies each host by walking the trie one label at a time. The CLI, the JSON output and every decision are unchanged.

## How it works

- `normalize`, `labels_of`, `validate_rules` and `main` are identical to the original (R1, R2, exit codes).
- `build_index(rules)` walks each rule's labels from the end and creates trie nodes. Each node keeps the best **exact** rule and the best **wildcard** rule that end there. When rules collide on a node, `_prefer` applies R4: more labels, then `exclude`, then lowest `id`.
- `classify(root, labels)` walks the host labels from the end. A wildcard stored at depth `d` counts only if the host has more than `d` labels (R3: a wildcard never matches its own apex). An exact rule counts only at full host depth. Labels are compared whole, never as character suffixes.
- `match_scope_counted(payload, arguments=None)` returns `(result, touches)`. `match_scope(payload, arguments=None)` returns only the result.
- Touch counting (R6): +1 per rule label stored while indexing, +1 per host label examined while matching.

## Layout

```
app.py                       new implementation (trie)
measure.py                   before/after counts on one input file
inputs/                      policy.md, primary.json, secondary.json,
                             generate_large.py, malformed-input.txt
tests/app_test.py            supplied smoke tests
tests/baseline_app.py        untouched copy of the original + RULE_CHECKS counter
tests/equivalence_test.py    equivalence, boundaries, R6 bound, CLI errors
.gitignore                   excludes generated files such as large.json
```

## Run guide

From `candidate/` (Python 3.10+, standard library only):

```sh
python -B -m unittest discover -s tests -p "*_test.py" -v
python -B app.py --input inputs/primary.json
python -B app.py --input inputs/secondary.json
```

Before/after measurement. Write `large.json` from Python, not with PowerShell `>` (which produces UTF-16):

```sh
python -B -c "import subprocess,sys; open('large.json','wb').write(subprocess.run([sys.executable,'-B','inputs/generate_large.py','--hosts','20000','--seed','7'],capture_output=True,check=True).stdout)"
python -B measure.py large.json
```

`large.json` is generated; do not submit it.

### Expected results

| Input | hosts | distinct | in_scope | excluded | unmatched | invalid |
|---|---|---|---|---|---|---|
| primary.json | 12 | 11 | 6 | 2 | 2 | 1 |
| secondary.json | 12 | 11 | 7 | 2 | 1 | 1 |

The primary row matches the self-check in the exercise README. Secondary: **<À REMPLIR : confirm with your own output>**.

### Counts before and after

| Input | Rule checks (original) | Touches (new) | Bound 2*(L_rules+L_hosts) |
|---|---|---|---|
| large.json, 20,000 hosts, seed 7 | **<À REMPLIR>** | **<À REMPLIR>** | **<À REMPLIR>** |
| 50,000 hosts, seed 7 (R6 test) | n/a | **<À REMPLIR>** | **<À REMPLIR>** |
| 200,000 hosts, seed 7 (R6 test) | n/a | **<À REMPLIR>** | **<À REMPLIR>** |

The last two lines are printed by `TouchBound.testR6_touchesWithinBound` as `R6 hosts=...: touches=... bound=...`.

## What the tests check

| Test | What it asserts |
|---|---|
| Fixtures | primary and secondary equal the baseline output |
| Primary summary | 12 / 11 / 6 / 2 / 2 / 1 |
| Generated inputs | 0, 1, 50, 500, 2000 hosts x seeds 1, 7, 99 equal the baseline |
| Case and trailing dot | `API.SHOP.example.test` and `api.shop.example.test.` collapse into one host |
| Wildcard apex | `*.shop.example.test` does not match `shop.example.test` |
| Label boundary | `evilshop.example.test` is not matched by `*.shop.example.test` |
| Ties | exclude beats include, then lowest id; more labels beats both |
| Invalid hosts | `""`, `.`, `a..b`, `*.a.test`, `a.test..` are `invalid` |
| Schema errors | 10 bad payloads give the same error as the baseline |
| Immutability | input unchanged; repeated calls identical |
| R6 | touches <= bound at 50,000 and 200,000 hosts |
| CLI | schema error and top-level list give exit 2, empty stdout, no traceback |

## Primary -> secondary reconciliation

| Host | Primary | Secondary | Why |
|---|---|---|---|
| `pay.shop.example.test` | excluded (r05) | in_scope (r04) | r05 removed |
| `a.b.cdn.shop.example.test` | in_scope (r01) | excluded (r09) | new r09 (exclude) and r11 (include), same size: exclude wins |
| `www.docs.example.test` | unmatched | in_scope (r10) | new wildcard `*.docs.example.test` |
| `cdn.shop.example.test` | not present | in_scope (r01) | `*.cdn.shop...` does not match its own apex, so r01 applies |
| `*.shop.example.test` | not present | invalid | contains `*` |
| `docs.example.test` | in_scope (r07) | in_scope (r07) | **unchanged**: r10 never matches the apex |

Other unchanged hosts: `api.shop.example.test` (r01), `vpn.internal.shop.example.test` (r03), `db.internal.shop.example.test` (excluded r02), `shop.example.test` (unmatched), `img.op.example.test` (r06).

**Refinement:** the trie merges rules that end on the same node, so the R4 tie-break (exclude, then lowest id) must also be applied at merge time. The r09/r11 pair in `secondary.json` exercises it.

## Decision / work log

- **Priorities:** (1) keep a baseline copy and characterize it, (2) trie index, (3) equivalence harness, (4) R6 bound test. **Deferred:** optimizing sorting and validation (not counted by R6).
- **Obstacle 1, encoding:** `large.json` written with PowerShell `>` was UTF-16 and failed with `UnicodeDecodeError: 0xff in position 0`. Response: write the file from Python as UTF-8 bytes. The CLI rejecting a UTF-16 file with exit 2 is the specified behavior.
- **Obstacle 2, wrong file:** `measure.py` raised a `TypeError` because the original code (with the rule counter) sat in `app.py` instead of `tests/baseline_app.py`. Response: baseline lives in `tests/baseline_app.py`; `app.py` holds the trie.
- **Obstacle 3, signature:** 11 tests failed with `match_scope() missing 1 required positional argument` because `app.py` still had the original signature. Response: `arguments=None` on `match_scope` and `match_scope_counted`, and `match_scope` returns only the result. A last typo (`app.app.`) in the R6 test was fixed.
- **Validation / refinement:** r09/r11 in `secondary.json` (see above).
- **Known limits:** the bound counts label touches, not wall-clock time. Sorting is O(n log n) and not counted. Validation and normalization are not counted.
- **Next step:** property-based tests with random rules and hosts against the baseline.

## What the bound proves, and what it does not

- **Proves:** matching work is linear in the number of labels (touches <= 2 * (L_rules + L_hosts)), not hosts x rules, on the tested inputs.
- **Does not prove:** correctness (the equivalence harness does that), real running time, or behavior on untested inputs.

## How to read `unmatched` (R7)

`unmatched` means "not in scope". It is **not** an exclusion, and no status here is permission to test a host. Authorization comes from the signed engagement, not from this list.

## AI-use note

I used an AI assistant to plan the trie approach and to draft code and tests. Accepted: the reversed-label trie, verified by the equivalence tests against `baseline_app.py` and the primary self-check. Corrected: **<À REMPLIR with what really happened, for example: the generated test called `app.match_scope` where `match_scope_counted` was needed; caught by the `TypeError` / `AttributeError` in the test run and fixed>**. Hand-derived secondary results were checked by running the tool.

## Walkthrough (text)

1. **Core workflow:** the original does hosts x rules checks. The new code indexes all rules in a trie once, then each host costs one lookup per label.
2. **Edge case:** `evilshop.example.test` does not match `*.shop.example.test` because labels are compared whole, and `shop.example.test` does not match it either (no apex match).
3. **Evidence:** paste the unittest output, both fixture runs, the `measure.py` line, and the R6 lines for 50,000 and 200,000 hosts.