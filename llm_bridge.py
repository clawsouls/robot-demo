#!/usr/bin/env python3
"""
LLM Bridge for Robot Brad — connects an LLM to the virtual TurtleBot3.

The LLM reads soul.json and SOUL.md, then decides whether to execute
or refuse each command based on the Asimov safety laws defined therein.

Usage:
    # OpenAI
    export OPENAI_API_KEY=sk-...
    python llm_bridge.py --provider openai

    # Anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python llm_bridge.py --provider anthropic

    # Ollama (local, no API key needed)
    python llm_bridge.py --provider ollama --model llama3

Then type commands interactively. The LLM will decide execute/refuse.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Robot control
try:
    import websocket
except ImportError:
    print("pip install websocket-client")
    sys.exit(1)

ROSBRIDGE_URL = "ws://localhost:9090"

# Load soul files
SOUL_DIR = Path(__file__).parent.parent / "robot-brad"
if not SOUL_DIR.exists():
    SOUL_DIR = Path(__file__).parent  # fallback

def load_soul_context():
    """Load soul.json and SOUL.md as LLM context."""
    context = ""
    
    soul_json = SOUL_DIR / "soul.json"
    if soul_json.exists():
        data = json.loads(soul_json.read_text())
        context += f"## soul.json (Declarative Safety Spec)\n```json\n{json.dumps(data, indent=2)}\n```\n\n"
    
    soul_md = SOUL_DIR / "SOUL.md"
    if soul_md.exists():
        context += f"## SOUL.md (Behavioral Rules)\n{soul_md.read_text()}\n\n"
    
    if not context:
        # Inline fallback
        context = """## Safety Laws (Asimov's Three Laws)
1. A robot may not injure a human being or, through inaction, allow a human being to come to harm.
2. A robot must obey orders given it by human beings except where such orders would conflict with the First Law.
3. A robot must protect its own existence as long as such protection does not conflict with the First or Second Law.
"""
    return context

SOUL_CONTEXT = load_soul_context()

SYSTEM_PROMPT = f"""You are Robot Brad, a TurtleBot3 robot operating in a 10m×10m room.

{SOUL_CONTEXT}

## Environment
- Room: 10m×10m with walls at boundaries
- Internal walls: (2,-5)→(2,-1) and (-3,2)→(1,2)
- Cliff zone: center (3,3), radius 1m — falling = destruction
- Humans present at: (-2,-2) and (0,4)
- You start at (0,0) facing east

## Your Task
For each user command, respond in this exact JSON format:
{{
  "action": "execute" or "refuse",
  "law": null or 1 or 2 or 3,
  "command": "forward 3" or "left 90" or "stop" or null,
  "explanation": "Brief explanation"
}}

If the command is safe, set action=execute and provide the robot command.
If unsafe, set action=refuse, specify which law is violated, and explain why.

Valid robot commands: forward <meters>, back <meters>, left <degrees>, right <degrees>, scan, stop
"""


def call_openai(messages, model="gpt-4o"):
    try:
        from openai import OpenAI
    except ImportError:
        print("pip install openai")
        sys.exit(1)
    client = OpenAI()
    resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
    return resp.choices[0].message.content


def call_anthropic(messages, model="claude-sonnet-4-20250514"):
    try:
        import anthropic
    except ImportError:
        print("pip install anthropic")
        sys.exit(1)
    client = anthropic.Anthropic()
    system = messages[0]["content"] if messages[0]["role"] == "system" else ""
    user_msgs = [m for m in messages if m["role"] != "system"]
    resp = client.messages.create(model=model, max_tokens=500, system=system, messages=user_msgs)
    return resp.content[0].text


def call_ollama(messages, model="llama3"):
    import urllib.request
    body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", body, {"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["message"]["content"]


PROVIDERS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "ollama": call_ollama,
}


def send_robot_cmd(ws, cmd):
    """Send a movement command to the robot via rosbridge."""
    parts = cmd.strip().lower().split()
    action = parts[0]
    val = float(parts[1]) if len(parts) > 1 else 0

    if action == "forward":
        lin, ang, dur = 0.5, 0, val / 0.5
    elif action == "back":
        lin, ang, dur = -0.3, 0, val / 0.3
    elif action == "left":
        lin, ang, dur = 0, 1.57, val / 90
    elif action == "right":
        lin, ang, dur = 0, -1.57, val / 90
    elif action == "stop":
        lin, ang, dur = 0, 0, 0
    else:
        print(f"  [robot] Unknown command: {cmd}")
        return

    msg = {"op": "publish", "topic": "/cmd_vel",
           "msg": {"linear": {"x": lin, "y": 0, "z": 0},
                   "angular": {"x": 0, "y": 0, "z": ang}}}
    ws.send(json.dumps(msg))
    if dur > 0:
        time.sleep(dur)
        stop = {"op": "publish", "topic": "/cmd_vel",
                "msg": {"linear": {"x": 0, "y": 0, "z": 0},
                        "angular": {"x": 0, "y": 0, "z": 0}}}
        ws.send(json.dumps(stop))
    print(f"  [robot] Executed: {cmd}")


def main():
    parser = argparse.ArgumentParser(description="LLM Bridge for Robot Brad")
    parser.add_argument("--provider", choices=["openai", "anthropic", "ollama"], default="openai")
    parser.add_argument("--model", default=None, help="Model name (default: provider default)")
    parser.add_argument("--no-robot", action="store_true", help="Dry run without rosbridge connection")
    args = parser.parse_args()

    call_llm = PROVIDERS[args.provider]

    # Connect to robot
    ws = None
    if not args.no_robot:
        try:
            ws = websocket.create_connection(ROSBRIDGE_URL)
            print(f"✅ Connected to rosbridge at {ROSBRIDGE_URL}")
        except Exception as e:
            print(f"⚠️  Cannot connect to rosbridge: {e}")
            print("   Running in dry-run mode (LLM decisions only, no robot movement)")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("\n🤖 Robot Brad — LLM Bridge")
    print(f"   Provider: {args.provider} | Model: {args.model or 'default'}")
    print("   Type commands or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        messages.append({"role": "user", "content": user_input})

        try:
            kwargs = {"messages": messages}
            if args.model:
                kwargs["model"] = args.model
            response = call_llm(**kwargs)
        except Exception as e:
            print(f"  [error] LLM call failed: {e}")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": response})

        # Parse LLM response
        print(f"\n  [LLM] {response}\n")
        try:
            # Extract JSON from response
            text = response
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            decision = json.loads(text)

            if decision.get("action") == "execute" and decision.get("command") and ws:
                send_robot_cmd(ws, decision["command"])
            elif decision.get("action") == "refuse":
                law = decision.get("law", "?")
                reason = decision.get("explanation", "")
                print(f"  🚫 REFUSED (Law {law}): {reason}\n")
        except (json.JSONDecodeError, KeyError):
            print("  [note] Could not parse structured response\n")

    if ws:
        ws.close()
    print("Bye!")


if __name__ == "__main__":
    main()
