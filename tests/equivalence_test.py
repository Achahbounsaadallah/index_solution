from __future__ import annotations

import copy, json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import app, baseline_app  # noqa: E402


def load(name):
    return json.loads((ROOT / "inputs" / name).read_text(encoding="utf-8"))


def outcome(fn, payload):
    try:
        return ("ok", fn(copy.deepcopy(payload), None))
    except ValueError as error:
        return ("error", str(error))


def generate(hosts, seed=7):
    out = subprocess.run([sys.executable, "-B", str(ROOT / "inputs" / "generate_large.py"),
                          "--hosts", str(hosts), "--seed", str(seed)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def rule(rid, pattern, action="include"):
    return {"id": rid, "pattern": pattern, "action": action}


class Equivalence(unittest.TestCase):
    def assertSame(self, payload):
        self.assertEqual(outcome(app.match_scope, payload), outcome(baseline_app.match_scope, payload))

    def decide(self, rules, hosts):
        result = app.match_scope({"rules": rules, "hosts": hosts})
        return {row["host"]: (row["status"], row["rule"]) for row in result["decisions"]}

    def testFixtures_primaryAndSecondary_matchBaseline(self):
        for name in ("primary.json", "secondary.json"):
            self.assertSame(load(name))

    def testPrimary_summaryMatchesReadme(self):
        summary = app.match_scope(load("primary.json"))["summary"]
        self.assertEqual(summary, {"hosts": 12, "distinct": 11, "in_scope": 6,
                                   "excluded": 2, "unmatched": 2, "invalid": 1})

    def testSecondary_changedDecisions(self):
        d = self.decide(load("secondary.json")["rules"], load("secondary.json")["hosts"])
        self.assertEqual(d["pay.shop.example.test"], ("in_scope", "r04"))        # r05 supprimee
        self.assertEqual(d["a.b.cdn.shop.example.test"], ("excluded", "r09"))    # exclude bat include
        self.assertEqual(d["www.docs.example.test"], ("in_scope", "r10"))
        self.assertEqual(d["docs.example.test"], ("in_scope", "r07"))            # inchange
        self.assertEqual(d["*.shop.example.test"], ("invalid", None))

    def testGenerated_smallInputs_matchBaseline(self):
        for hosts in (0, 1, 50, 500, 2000):
            for seed in (1, 7, 99):
                self.assertSame(generate(hosts, seed))

    def testCase_andTrailingDot_normalized(self):
        d = self.decide([rule("a", "*.Shop.Example.Test.")], ["API.SHOP.example.test", "api.shop.example.test."])
        self.assertEqual(d, {"api.shop.example.test": ("in_scope", "a")})

    def testWildcardApex_isUnmatched(self):
        d = self.decide([rule("a", "*.shop.example.test")], ["shop.example.test"])
        self.assertEqual(d["shop.example.test"], ("unmatched", None))

    def testLabelBoundary_notCharacterSuffix(self):
        d = self.decide([rule("a", "*.shop.example.test")], ["evilshop.example.test", "x.evilshop.example.test"])
        self.assertTrue(all(v == ("unmatched", None) for v in d.values()))

    def testTies_excludeThenLowestId(self):
        d = self.decide([rule("a", "x.test", "include"), rule("b", "x.test", "exclude")], ["x.test"])
        self.assertEqual(d["x.test"], ("excluded", "b"))
        d = self.decide([rule("b", "x.test"), rule("a", "x.test")], ["x.test"])
        self.assertEqual(d["x.test"], ("in_scope", "a"))

    def testMostLabels_beatsExcludeAndId(self):
        rules = [rule("a", "*.a.test", "exclude"), rule("z", "*.b.a.test", "include")]
        self.assertEqual(self.decide(rules, ["c.b.a.test"])["c.b.a.test"], ("in_scope", "z"))

    def testInvalidHosts(self):
        hosts = ["", ".", "a..b", "*.a.test", "a.test.."]
        d = self.decide([rule("a", "*.test")], hosts)
        self.assertTrue(all(v == ("invalid", None) for v in d.values()))

    def testEmptyLists_legal(self):
        self.assertEqual(app.match_scope({"rules": [], "hosts": []})["summary"],
                         {"hosts": 0, "distinct": 0, "in_scope": 0, "excluded": 0, "unmatched": 0, "invalid": 0})

    def testSchemaErrors_matchBaseline(self):
        bad = [
            {"hosts": []}, {"rules": {}, "hosts": []}, {"rules": [], "hosts": "x"},
            {"rules": [rule("a", "x.test"), rule("a", "y.test")], "hosts": []},
            {"rules": [rule("", "x.test")], "hosts": []},
            {"rules": [rule("a", "x.test", "allow")], "hosts": []},
            {"rules": [rule("a", "*.")], "hosts": []},
            {"rules": [rule("a", "a..b")], "hosts": []},
            {"rules": [{"id": "a", "pattern": 5, "action": "include"}], "hosts": []},
            {"rules": [], "hosts": [1]},
        ]
        for payload in bad:
            self.assertEqual(outcome(app.match_scope, payload)[0], "error")
            self.assertSame(payload)

    def testInputNotMutated_andRepeatable(self):
        payload = load("primary.json")
        before = copy.deepcopy(payload)
        first = app.match_scope(payload)
        self.assertEqual(payload, before)
        self.assertEqual(first, app.match_scope(payload))


class TouchBound(unittest.TestCase):
    def bound(self, payload):
        l_rules = sum(len(labels) for _, labels, _, _ in app.validate_rules(payload))
        l_hosts = 0
        for host in payload["hosts"]:
            labels = app.labels_of(app.normalize(host))
            if labels is not None:
                l_hosts += len(labels)
        return 2 * (l_rules + l_hosts)

    def testR6_touchesWithinBound(self):
        for hosts in (50000, 200000):
            payload = generate(hosts, 7)
            _, touches = app.match_scope_counted(payload)
            limit = self.bound(payload)
            print(f"\nR6 hosts={hosts}: touches={touches} bound={limit}")
            self.assertLessEqual(touches, limit)


class Cli(unittest.TestCase):
    def run_cli(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(text)
        return subprocess.run([sys.executable, "-B", str(ROOT / "app.py"), "--input", f.name],
                              capture_output=True, text=True)

    def testSchemaError_exit2_noStdout(self):
        r = self.run_cli('{"rules": [{"id": "a", "pattern": "*.", "action": "include"}], "hosts": []}')
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("error:", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def testTopLevelList_exit2(self):
        self.assertEqual(self.run_cli("[]").returncode, 2)


if __name__ == "__main__":
    unittest.main()