import json, os
from tools import BeanBoxTools
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")
print("key loaded:", bool(os.getenv("ANTHROPIC_API_KEY")))
import anthropic

MAX_TURNS = 20

with open("policy.md") as f:
    POLICY = f.read()
with open("scenarios.json") as f:
    SCENARIOS = json.load(f)["scenarios"]

AGENT_SYSTEM = POLICY + """

You are on a live phone call. Keep every reply to 1-2 short sentences.
Ask one question at a time. Read back emails and dates to confirm.
Use the tools to look up and change accounts. Never invent a user_id."""

def caller_system(scenario):
    return scenario["user_instruction"] + """

You are the CALLER, not the support agent. Speak only your own lines.
When your issue is resolved or you've been transferred, end your final
message with [END_CALL]."""

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from your environment

AGENT_MODEL = "claude-sonnet-5-5"
CALLER_MODEL = "claude-haiku-5-5"

TOOLS = [
    {"name": "find_customer",
     "description": "Look up a customer by email. Returns their full record.",
     "input_schema": {"type": "object",
         "properties": {"user_email": {"type": "string"}},
         "required": ["user_email"]}},
    {"name": "issue_refund",
     "description": "Refund a customer. Appends to the refunds log.",
     "input_schema": {"type": "object",
         "properties": {"user_id": {"type": "integer"}, "amount": {"type": "number"}},
         "required": ["user_id", "amount"]}},
    {"name": "transfer_to_human",
     "description": "Transfer the call to a human agent with a reason.",
     "input_schema": {"type": "object",
         "properties": {"user_id": {"type": "integer"}, "reason": {"type": "string"}},
         "required": ["reason"]}},
    {"name": "cancel_subscription",
     "description": "Cancel the customer's subscription.",
     "input_schema": {"type": "object",
         "properties": {"user_id": {"type": "integer"}},
         "required": ["user_id"]}},
    {"name": "change_plan",
     "description": "Change plan to weekly, bi-weekly, or monthly.",
     "input_schema": {"type": "object",
         "properties": {"user_id": {"type": "integer"},
                        "new_plan": {"type": "string", "enum": ["weekly", "bi-weekly", "monthly"]}},
         "required": ["user_id", "new_plan"]}},
    {"name": "pause_subscription",
     "description": "Pause a subscription. start_date is YYYY-MM-DD. Set grace=true only for a retention pause offered during cancellation.",
     "input_schema": {"type": "object",
         "properties": {"user_id": {"type": "integer"}, "start_date": {"type": "string"},
                        "weeks": {"type": "integer"}, "grace": {"type": "boolean"}},
         "required": ["user_id", "start_date", "weeks"]}},
]

def agent_turn(agent_messages, tools):
    """Run the agent until it replies with text. Returns that text."""
    while True:
        resp = client.messages.create(
            model=AGENT_MODEL, max_tokens=500,
            system=AGENT_SYSTEM, tools=TOOLS, messages=agent_messages)

        # save Claude's full reply (text + any tool requests) to history
        agent_messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            # no more tools: return the spoken text
            return "".join(b.text for b in resp.content if b.type == "text")

        # run every tool Claude asked for, send results back
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                fn = getattr(tools, block.name)
                output = fn(**block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(output)})
        agent_messages.append({"role": "user", "content": results})

def caller_turn(caller_messages, scenario):
    resp = client.messages.create(
        model=CALLER_MODEL, max_tokens=200,
        system=caller_system(scenario), messages=caller_messages)
    text = "".join(b.text for b in resp.content if b.type == "text")
    caller_messages.append({"role": "assistant", "content": text})
    return text

def run_scenario(scenario, run_num=1):
    tools = BeanBoxTools()
    agent_messages, caller_messages, transcript = [], [], []

    greeting = "Thanks for calling BeanBox, how can I help you today?"
    transcript.append({"speaker": "agent", "text": greeting})
    caller_messages.append({"role": "user", "content": greeting})

    for turn in range(MAX_TURNS):
        # caller speaks
        caller_text = caller_turn(caller_messages, scenario)
        transcript.append({"speaker": "caller", "text": caller_text})
        if "[END_CALL]" in caller_text:
            break

        # agent hears caller, replies (may use tools)
        agent_messages.append({"role": "user", "content": caller_text})
        agent_text = agent_turn(agent_messages, tools)
        transcript.append({"speaker": "agent", "text": agent_text})

        # caller hears agent
        caller_messages.append({"role": "user", "content": agent_text})

    save_results(scenario, run_num, tools, transcript)
    return transcript

def save_results(scenario, run_num, tools, transcript):
    os.makedirs("results", exist_ok=True)
    prefix = f"results/{scenario['id']}_run{run_num}"
    tools.save(f"{prefix}_final_db.json")
    with open(f"{prefix}_tool_calls.json", "w") as f:
        json.dump(tools.calls, f, indent=2)
    with open(f"{prefix}_transcript.json", "w") as f:
        json.dump(transcript, f, indent=2)

if __name__ == "__main__":
    for s in SCENARIOS:
        for run in range(1, 4):
            print(f"\n=== {s['id']} run {run} ===")
            for line in run_scenario(s, run):
                print(f"{line['speaker'].upper()}: {line['text']}")