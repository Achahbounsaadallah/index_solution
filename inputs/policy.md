# SpruceLedge scope contract

Snapshot: 2027-03-01 09:00 UTC+00:00. Fictional rules and hosts; nothing is resolved or contacted.

- R1 Input has `rules` and `hosts` lists. A rule has a unique nonempty string `id`, a string `pattern` and `action` `include` or `exclude`. Hosts are strings and may repeat. Bad schema, including a pattern that is invalid under R2, exits 2. Extra fields are ignored; empty lists are legal.
- R2 Normalize hosts and patterns the same way: lowercase, then drop one trailing `.`. A valid name is `.`-separated labels, each nonempty and without `*`. A pattern is a valid name (exact) or `*.` followed by a valid name (wildcard). A host that is not a valid name gets status `invalid`.
- R3 An exact rule matches only its own name. A wildcard `*.S` matches a name that ends with all labels of S and has at least one more label, at any depth; it never matches S itself. Compare whole labels, never character suffixes.
- R4 Among matching rules the winner has the most labels in its name (S for a wildcard); then `exclude` beats `include`; then the lowest `id` in string order. Status is `in_scope` (winner includes), `excluded` (winner excludes) or `unmatched` (no rule matches).
- R5 Return `decisions`, one per distinct normalized host sorted by that host: `host`, `status`, `rule` (winner id, null for `unmatched` and `invalid`). `summary`: `hosts` (input entries), `distinct`, and the count of each status, zeros included. Inputs are not mutated; repeated calls are identical.
- R6 Preserve every output, then remove the host-by-rule comparison. Count label touches outside the JSON: one per name label stored while indexing rules, one per host label examined while matching. Total touches must be at most `2 * (L_rules + L_hosts)`, the name labels of all rules plus the labels of all valid input host entries. Validation, normalization, sorting and JSON I/O are not counted; hash lookups count as constant. No wall-clock threshold.
- R7 `unmatched` means not in scope. It is not an exclusion, and no status here is permission to test a host; authorization comes from the signed engagement, not this list.
