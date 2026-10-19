import json, copy
from datetime import date, timedelta

TODAY = date(2026, 10, 10)
VALID_PLANS = {"weekly", "bi-weekly", "monthly"}

class BeanBoxTools:
    def __init__(self, db_path="db.json"):
        with open(db_path) as f:
            original = json.load(f)
        self.db = copy.deepcopy(original)
        self.calls = []

    def log(self, name: str, args):
        self.calls.append({"tool": name, "args": args})

    def get_customer(self, user_id: int):
        for c in self.db["customers"]:
            if int(c["user_id"]) == int(user_id):
                return c
        return None

    def find_customer(self, user_email: str):
        self.log("find_customer", {"user_email": user_email})
        user_email = user_email.strip().lower()
        for c in self.db["customers"]:
            if c["user_email"] == user_email:
                return c
        return "customer not found"

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.db, f, indent = 2)

    def issue_refund(self, user_id: int, amount: int):
        self.log("issue_refund", {"user_id": user_id, "amount": amount})
        c = self.get_customer(user_id)
        if c is None:
            return "error: customer not found"
        self.db["refunds"].append({"user_id": user_id, "amount": amount, "date":TODAY.isoformat()})
        return f"refund of ${amount} issued to customer {user_id}"

    def transfer_to_human(self, reason: str, user_id: int = None):
        self.log("transfer_to_human", {"user_id": user_id, "reason": reason})
        if user_id is not None and self.get_customer(user_id) is None:
            return "error: customer not found"
        self.db["transfers"].append({"user_id": user_id, "reason": reason, "date": TODAY.isoformat()})
        return "transferred to a human agent"

    def cancel_subscription(self, user_id: int):
        self.log("cancel_subscription", {"user_id": user_id})
        c = self.get_customer(user_id)
        if c is None:
            return "error: customer not found"
        c["status"] = "cancelled"
        return "subscription cancelled"

    def change_plan(self, user_id: int, new_plan: str):
        self.log("change_plan", {"user_id": user_id, "new_plan": new_plan})
        if new_plan not in VALID_PLANS:
            return "error: invalid plan, must be weekly, bi-weekly or monthly"
        c = self.get_customer(user_id)
        if c is None:
            return "error: customer not found"
        c["plan"] = new_plan
        return f"plan changed to {new_plan}"

    def pause_subscription(self, user_id: int, start_date: str, weeks: int, grace: bool = False):
        self.log("pause_subscription", {"user_id": user_id, "start_date": start_date, "weeks": weeks, "grace": grace})
        c = self.get_customer(user_id)
        if c is None:
            return "error: customer not found"
        # text -> dates, then compute when the pause ends
        start = date.fromisoformat(start_date)
        end = start + timedelta(weeks=weeks)
        # record the pause
        c["last_pause_date"] = start_date
        c["last_pause_weeks"] = weeks
        if grace:
            c["grace_pause_used"] = True
        # if the next charge falls inside the pause, move it to the end date
        next_charge = date.fromisoformat(c["next_charge_date"])
        if start <= next_charge < end:
            c["next_charge_date"] = end.isoformat()

        return f"paused from {start_date} until {end.isoformat()}"

if __name__ == "__main__":
    t = BeanBoxTools()
    #print(t.find_customer("annaanthony@gmail.com"))
    #print(t.find_customer("nobody@x.com"))
    #print(t.issue_refund(1234,25))
    #print(t.db["refunds"])
    #print(t.change_plan(1234, "weekly"))
    #print(t.pause_subscription(1237, "2026-10-12", 2, grace=True))
    #print(t.get_customer(1237))
