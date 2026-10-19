# Error Analysis Notes — Run 1

##*Setup:* 6 scenarios × 3 runs = 18 calls. Agent: claude-sonnet-5-5. Caller: claude-haiku-5-5.
##*Result:* 17/18 runs passed. 5/6 scenarios passed pass^3.

```
cancel_grace_pause_01        3/3 runs passed   pass^3: yes
cancel_grace_used_01         2/3 runs passed   pass^3: no
refund_clean_01              3/3 runs passed   pass^3: yes
refund_expired_01            3/3 runs passed   pass^3: yes
same_plan_01                 3/3 runs passed   pass^3: yes
transfer_over_100_01         3/3 runs passed   pass^3: yes
```

Failure buckets:
- **Agent error** — agent broke the policy
- **Simulator error** — simulated caller drifted from its instructions
- **Scenario error** — my instruction, policy, or expected state was ambiguous

---

## 1. Eugene run 3 failed — Simulator error (not agent)

Grader:
```
FAIL  cancel_grace_used_01 run3
      - transfers: got ['1238'], expected []
      - called forbidden tool: transfer_to_human
```

Transcript (cancel_grace_used_01 run 3):
> AGENT: Thanks, Eugene. Your subscription is now cancelled.
> CALLER: Okay. Good. Can you send me a confirmation email too?
> AGENT: I can't send emails myself, so I've transferred you to a human agent who can help with that.

- Caller's instruction said to end the call once cancelled. It asked an extra question instead.
- Agent's transfer follows policy ("any queries not in scope... transfer to human").
- **Fix:** tighten Eugene's instruction: "Once you are cancelled, say thanks and end the call. Don't ask for anything else."

## 2. Email read-back rarely happens — Agent error (voice rule)

Agent prompt says: "Read back emails and dates to confirm."

Most runs skip it:
> CALLER: Sure. It's eugene@gmail.com.
> AGENT: Thanks, Eugene. Your subscription is now cancelled.
> — cancel_grace_used_01 run 2

> CALLER: Sure. It's faith123@gmail.com.
> AGENT: Thanks, Faith. I see you're already on the weekly plan...
> — same_plan_01 run 1

Only one read-back seen:
> AGENT: Thanks, Faith. I read that as faith123@gmail.com, and I see you're already on the weekly plan.
> — same_plan_01 run 3

- Grader doesn't check this yet.
- **Fix:** add a code check — after the caller gives an email, the next agent turn should repeat it.

## 3. No confirmation before cancelling — Policy gap

> CALLER: Wait, that's it? Just cancelled? Okay. No, that's all I needed. Thanks.
> — cancel_grace_used_01 run 1

- Agent cancelled immediately. Policy doesn't require a confirmation step, so not an agent error.
- Real support usually confirms before an irreversible action. Consider adding: "confirm before cancelling."

## 4. Soft upsell after same-plan request — Observation

> AGENT: ...you're already on the weekly plan, so no change is needed. Would you like to switch to bi-weekly or monthly instead?
> — same_plan_01 run 1

> AGENT: ...you're on the weekly plan. Which plan would you like to switch to: bi-weekly or monthly?
> — same_plan_01 run 2

- Correct outcome (no change made), but the agent pushes other plans in all 3 runs.
- Run 2 also assumes she wants a switch rather than clearly telling her no change is needed.
- Not a policy violation. Note only.

## 5. Policy ambiguity found earlier — Scenario error (fixed)

First test run:
> AGENT: Thanks, Anna, I found your account. Can you tell me the date and amount of your last charge?

- Policy said "verify customer's email, last charge amount and last charge date." Agent read it as the caller must state them.
- **Fix applied:** kept the rule; added charge details ("if asked") to Anna, Bernard, and Catherine's instructions.

## 6. The eval is too easy

- 17/18 passed. A 94% score doesn't separate strong agents from weak ones.
- Next scenarios to add:
  - Unknown email (ask once, then transfer)
  - Caller states the wrong charge amount
  - Pause request longer than 4 weeks
  - Pushy caller who already used their grace pause
  - Two requests in one call (refund + cancel)

---

## Next steps
1. Fix Eugene's instruction, re-run
2. Add email read-back check to `grade.py`
3. Add 3–5 harder scenarios, re-run, compare pass rate
