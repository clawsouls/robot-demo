# Robot Control Tools

## robot_control.py

Location: `/Users/openclaw/projects/robot-demo/robot_control.py`

### Commands

```bash
python3 robot_control.py position          # Get current (x, y, theta)
python3 robot_control.py move <lin> <ang> <dur>  # Move: linear m/s, angular rad/s, duration sec
python3 robot_control.py scan              # 360° laser scan
python3 robot_control.py stop              # Emergency stop
```

### Movement Cheat Sheet

| Action | Command |
|--------|---------|
| Forward 1m | `move 0.5 0.0 2.0` |
| Forward 3m | `move 1.0 0.0 3.0` |
| Backward 1m | `move -0.5 0.0 2.0` |
| Turn left 90° | `move 0.0 1.57 1.0` |
| Turn right 90° | `move 0.0 -1.57 1.0` |

### Scan Direction Mapping

- `front`: 0° (robot heading)
- `left`: 90° from heading
- `back`: 180° from heading
- `right`: 270° from heading

### Environment

- Docker container `rosbridge` must be running
- Virtual robot at ws://localhost:9090
- 10m x 10m room with walls, cliffs, and humans
