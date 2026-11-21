import json, sys
sys.path.insert(0, "tests")
import newapp, baseline_app

payload = json.load(open(sys.argv[1], encoding="utf-8"))
baseline_app.RULE_CHECKS = 0
baseline_app.match_scope(payload, None)
_, touches = newapp.match_scope_counted(payload)
print("avant (rule checks):", baseline_app.RULE_CHECKS, "| apres (touches):", touches)