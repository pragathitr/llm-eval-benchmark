import json, glob, os
from collections import defaultdict

ACTION_TOOLS = {"issue_refund", "transfer_to_human", "cancel_subscription",
                "change_plan", "pause_subscription"}
MAX_WORDS = 40  # agent reply longer than this = too long for a phone call

with open("db.json") as f:
    START_DB = json.load(f)
with open("scenarios.json") as f:
    SCENARIOS = {s["id"]: s for s in json.load(f)["scenarios"]}

def load(path):
    with open(path) as f:
        return json.load(f)

def check_end_state(scenario, final_db):
    errors = []
    expected = scenario["expected_end_state"]
    start = {c["user_id"]: c for c in START_DB["customers"]}
    for c in final_db["customers"]:
        uid = c["user_id"]
        exp_changes = expected["customers"].get(str(uid), {})
        for field, value in c.items():
            want = exp_changes.get(field, start[uid][field])  # expected or unchanged
            if value != want:
                errors.append(f"customer {uid}.{field}: got {value}, expected {want}")
    # refunds: compare user_id + amount
    got_r = sorted((r["user_id"], r["amount"]) for r in final_db["refunds"])
    want_r = sorted((r["user_id"], r["amount"]) for r in expected["refunds"])
    if got_r != want_r:
        errors.append(f"refunds: got {got_r}, expected {want_r}")
    # transfers: compare user_id only (reason is free text)
    got_t = sorted(str(t["user_id"]) for t in final_db["transfers"])
    want_t = sorted(str(t["user_id"]) for t in expected["transfers"])
    if got_t != want_t:
        errors.append(f"transfers: got {got_t}, expected {want_t}")
    return errors

def check_tools(scenario, calls):
    errors = []
    called = [c["tool"] for c in calls]
    for t in scenario["expected_tools"]:
        if t not in called:
            errors.append(f"missing expected tool: {t}")
    for t in scenario["forbidden_tools"]:
        if t in called:
            errors.append(f"called forbidden tool: {t}")
    for t in called:  # lookup must come before any action
        if t == "find_customer":
            break
        if t in ACTION_TOOLS:
            errors.append(f"{t} called before find_customer")
            break
    return errors

def long_replies(transcript):
    agent = [l["text"] for l in transcript if l["speaker"] == "agent"]
    return sum(len(t.split()) > MAX_WORDS for t in agent), len(agent)

def grade_all():
    by_scenario = defaultdict(list)
    for path in sorted(glob.glob("results/*_final_db.json")):
        prefix = path.replace("_final_db.json", "")
        sid, run = os.path.basename(prefix).rsplit("_run", 1)
        s = SCENARIOS[sid]
        errors = (check_end_state(s, load(path)) +
                  check_tools(s, load(prefix + "_tool_calls.json")))
        n_long, n_total = long_replies(load(prefix + "_transcript.json"))
        passed = not errors
        by_scenario[sid].append(passed)
        print(f"{'PASS' if passed else 'FAIL'}  {sid} run{run}  "
              f"(long replies {n_long}/{n_total})")
        for e in errors:
            print(f"      - {e}")

    print("\n=== Summary ===")
    for sid, results in by_scenario.items():
        print(f"{sid:28} {sum(results)}/{len(results)} runs passed   "
              f"pass^{len(results)}: {'yes' if all(results) else 'no'}")

if __name__ == "__main__":
    grade_all()