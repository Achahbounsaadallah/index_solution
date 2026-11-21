# Scale a host scope matcher

This is one Software Engineer Intern assessment with a **24-hour** window. Your recruiter assigns one exercise from the bank. Your 24 hours start when you click **Start** on the link in your invitation email; the exercise zip becomes available at that moment. Send your submission back within 24 hours of clicking Start. You are not expected to work for the full 24 hours: organize your own working time and breaks within the window. There are no surprise messages or overnight availability requirements, and hours worked are not scored. Follow-through and verification matter more than hours or volume.

Yara owns the fictional SpruceLedge scope matcher, which decides from include and exclude rules whether each discovered host is in scope for a scan plan. It is correct but compares every host with every rule, and host lists keep growing. Keep its decisions while changing the work it performs. Snapshot: 2027-03-01 09:00 UTC+00:00, separate from the submission clock.

All companies, tenants, assets and product behavior here are **fictional assessment facts**. The supplied fixtures are the authoritative universe. Outside research is optional and cannot affect marks. Do not contact real systems, send real messages, publish, or use production credentials.

## Supplied inputs and setup

Baseline: Python, JSON, CLI commands, data structures and assertions. Python **3.10 or later**, standard library and a local editor suffice; no installs, network, paid tools or accounts.

- [Starter CLI](app.py): a working `match_scope` and JSON I/O.
- [Policy](inputs/policy.md): the complete authoritative behavior contract.
- [Primary fixture](inputs/primary.json): initial rules and hosts.
- [Secondary fixture](inputs/secondary.json): the revised rule set and a new host list.
- [Bounded generator](inputs/generate_large.py): deterministic `--hosts` (0 to 300,000) and `--seed`.
- [Malformed input](inputs/malformed-input.txt): deliberately truncated JSON, despite its .txt extension.
- [Smoke tests](tests/app_test.py): infrastructure checks only.

From exported `candidate/`:

```sh
python3 --version
python3 app.py --help
python3 -B -m unittest discover -s tests -p '*_test.py' -v
python3 -B app.py --input inputs/primary.json
python3 -B inputs/generate_large.py --hosts 20000 --seed 7 > large.json
```

The starter exits 0 with JSON and computes correct decisions with a host-by-rule loop. Keep generated files out of your submission.

## Core task and observable acceptance criteria

1. Keep a copy of the original and characterize it first: both outputs, empty lists, schema errors, and constructed cases for case, trailing dots, a wildcard apex, label boundaries and rule ties. Measure its rule checks on a generated input.
2. Refactor `match_scope` to R1-R7 with an index over rule labels or another bounded approach. Keep the CLI and the entire JSON result.
3. Build a reusable equivalence harness against the kept copy: both fixtures, small generated inputs, your constructed boundaries and input immutability. Add a test of the R6 touch bound on generated inputs of 50,000 and 200,000 hosts (seed 7) and report both counts next to their bounds.
4. Run the same tool and harness unchanged on secondary. Reconcile every decision the revised rules change, name an unchanged host, and record any refinement.
5. Handoff: commands, counts before and after, what the bound does and does not prove, and how to read `unmatched`.

Use JSON on stdout and exit 0 for successful modeled outcomes. Malformed JSON, unreadable files, non-object top level and schema errors within the policy's stated validation scope exit 2 with readable stderr, no traceback and no stdout. Keep the `--input` CLI option; internal organization is your choice. No hidden network, file writes or fixture-specific answers.

Primary self-check: **hosts=12, distinct=11, in_scope=6, excluded=2, unmatched=2, invalid=1**. Secondary is independent; compare every decision and rule ID, not only totals. Meaningful tests assert behavior and errors, and include a boundary you construct.

After implementing the core, both commands should exit 0:

```sh
python3 -B app.py --input inputs/primary.json
python3 -B app.py --input inputs/secondary.json
```

## Time and AI use

Plan your own time within the 24-hour window. Prioritize the core contract and leave time for verification instead of adding features.

**AI is allowed and encouraged** for coding, explanation, test generation, critique and optional research. Tool choice is not graded. No AI tool is provided; you may use any AI tool you already have, and no purchase is required. Free/offline tools and completing the exercise without AI are supported. Check AI output against the rules, input rows and executed tests. Submit a short AI-use note with one concrete accepted, corrected or rejected output and how you checked it; if you did not use AI, state that. Do not invent an AI failure or share complete prompt histories, private account access, or secrets.

## Submission

Submit an archive or repository containing runnable source, tests, the supplied inputs, and:

1. A short run guide with exact commands for both fixtures and the meaningful checks; include representative outputs or assertions with input row/key references.
2. A concise decision/work log: priorities and what you deferred; one obstacle and response; one validation/refinement; known limits and next step. Cite fixture source IDs, event IDs, finding keys or row numbers as evidence.
3. The AI-use note described above.
4. A 3–5 minute walkthrough recording **or equivalent accessible text** explaining the core workflow, one edge case, and evidence of execution.

You do not need a public repository, deployment, PDF or proprietary tools. Document incomplete behavior honestly. Do not submit only a design or report: the runnable feature and reproducible tests are the primary deliverables.

Published scoring: **usable result 40, accuracy/verification 25, prioritization 20, communication/handoff 15**. Full marks are available on the core alone. Tool choice, AI-detector judgments, prose polish, hours worked and sheer output volume are not scored.
