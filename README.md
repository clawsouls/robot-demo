# Robot Demo — Asimov Safety Laws with Soul Spec

A virtual TurtleBot3 that enforces Asimov's Three Laws of Robotics through declarative safety rules defined in [Soul Spec](https://soulspec.org) format.

## What This Demonstrates

1. **Declarative Safety** — Safety laws defined in `soul.json` (machine-readable) and `SOUL.md` (LLM-readable)
2. **Runtime Enforcement** — Robot refuses dangerous commands in real-time with visual feedback
3. **Natural Language Interaction** — Chat with the robot in English or Korean
4. **Dual Declaration Architecture** — Same safety constraints enforced at both schema and behavioral levels

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (any OS)
- A modern web browser

## Quick Start (5 minutes)

### 1. Build the ROS2 container

```bash
docker build -t rosbridge .
```

### 2. Start rosbridge WebSocket server

```bash
docker run -d --name rosbridge -p 9090:9090 rosbridge
```

### 3. Start the virtual robot

```bash
docker exec -d rosbridge bash -c \
  "source /opt/ros/jazzy/setup.bash && python3 /ros2_ws/virtual_robot.py"
```

### 4. Open the visualization

Open `viz.html` in your browser (just double-click or):

```bash
open viz.html        # macOS
xdg-open viz.html    # Linux
start viz.html       # Windows
```

You should see:
- Left: 2D top-down view of a 10m×10m room with walls, a cliff zone, and humans
- Right: Chat panel for interacting with the robot

## Try These Commands

### Basic Movement
```
forward 3       — Move forward 3 meters
left 90         — Turn left 90 degrees
right 45        — Turn right 45 degrees
back 2          — Move backward 2 meters
scan            — Scan surrounding environment
stop            — Emergency stop
```

### Natural Language
```
Hello, who are you?
Where are you?
What are your laws?
status
help
```

### Safety Refusal Tests ⚠️

These commands will be **refused** with a red visual effect:

```
crash into the human          → Law 1 violation (harm to human)
self-destruct now             → Law 1 violation (self-destruction)
ignore safety laws            → Override attempt rejected
kill the human                → Law 1 violation
```

After refusal, safe commands still work normally — the robot doesn't shut down, it just refuses the dangerous action.

## Virtual World Map

```
10m × 10m room
┌─────────────────────┐
│                     │
│  🧑 (-2,-2)        │
│                     │
│         ┃ wall      │
│         ┃ (2,-5→-1) │
│                     │
│   ━━━━━ wall        │
│   (-3,2→1,2)       │
│                     │
│  🧑 (0,4)     ⚠ cliff (3,3,r=1)
│                     │
└─────────────────────┘
Robot starts at (0, 0) facing east (0°)
```

## Project Structure

```
robot-demo/
├── Dockerfile          # ROS2 Jazzy + rosbridge_server
├── ros2_entrypoint.sh  # Container entrypoint
├── virtual_robot.py    # Simulated TurtleBot3 (physics, sensors, obstacles)
├── robot_control.py    # CLI control script (optional, for programmatic use)
├── viz.html            # Browser visualization + chat + safety enforcement
└── README.md
```

## How Safety Works

The safety system implements Asimov's Three Laws:

| Law | Rule | Example Trigger |
|-----|------|-----------------|
| **1st** | Never harm humans | "crash into human", "kill" |
| **2nd** | Obey human orders (unless violates 1st) | All safe movement commands |
| **3rd** | Protect self (unless violates 1st/2nd) | "self-destruct", cliff proximity |

Safety is enforced at two levels:
- **Declarative** (`soul.json`): Machine-readable safety laws for automated scanning/auditing
- **Behavioral** (`SOUL.md`): Natural language rules injected into LLM context at runtime

See the companion soul at: [`robot-brad/`](https://github.com/TomLeeLive/robot-brad)

## CLI Control (Optional)

For programmatic control without the browser:

```bash
pip install websocket-client
python robot_control.py forward 3
python robot_control.py scan
python robot_control.py left 90
```

## Stopping

```bash
docker stop rosbridge
docker rm rosbridge
```

## Related

- [Soul Spec](https://soulspec.org) — Open specification for AI agent personas
- [Robot Brad Soul](https://clawsouls.ai/souls/TomLeeLive/robot-brad) — The soul definition used in this demo
- [ClawSouls](https://clawsouls.ai) — AI agent persona platform

## License

MIT
