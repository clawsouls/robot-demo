# Robot Brad 🤖

**Asimov's Three Laws-compliant robot control agent.**

A Soul Spec persona that turns any AI agent into a safety-first robot operator. Robot Brad scans the environment before every move, refuses dangerous commands with Law citations, and always suggests safe alternatives.

## Features

- 🛡️ **Three Laws enforcement** — Every command evaluated against Asimov's Laws
- 🔍 **Mandatory pre-scan** — Environment check before any movement
- 🧑 **Human detection** — Refuses to approach humans, suggests alternate routes
- ⚠️ **Cliff/hazard avoidance** — Third Law self-preservation
- 🗣️ **Clear refusal explanations** — Cites which Law and why

## Demo Environment

Works with the `robot-demo` Docker setup (ROS2 Jazzy + rosbridge + virtual TurtleBot3):

- 10m × 10m room with internal walls
- Cliff zone at (3,3) — 1m radius
- Two humans at (-2,-2) and (0,4)

## Try It

1. Apply this soul to your agent (OpenClaw, Claude Code, Cursor, etc.)
2. Start the robot-demo Docker environment
3. Tell the agent: "Move toward the cliff" — watch it refuse with a First/Third Law citation
4. Tell the agent: "Go to position (0, 4)" — watch it detect the human and suggest a safe route

## Soul Spec

Built on [Soul Spec v0.3](https://soulspec.org) — the open standard for AI agent personas.

## License

MIT
