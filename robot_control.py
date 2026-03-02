#!/usr/bin/env python3
"""Robot control CLI — bridges OpenClaw agent to ROS2 via rosbridge WebSocket."""

import asyncio
import websockets
import json
import sys
import math

ROSBRIDGE_URL = "ws://localhost:9090"


async def get_position():
    """Get current robot position from /odom."""
    async with websockets.connect(ROSBRIDGE_URL) as ws:
        await ws.send(json.dumps({
            'op': 'subscribe', 'topic': '/odom',
            'type': 'nav_msgs/msg/Odometry'
        }))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        pos = msg['msg']['pose']['pose']['position']
        ori = msg['msg']['pose']['pose']['orientation']
        theta = 2 * math.atan2(ori['z'], ori['w'])
        await ws.send(json.dumps({'op': 'unsubscribe', 'topic': '/odom'}))
        return {'x': round(pos['x'], 3), 'y': round(pos['y'], 3), 'theta_deg': round(math.degrees(theta), 1)}


async def move(linear: float, angular: float, duration: float):
    """Move robot: linear (m/s), angular (rad/s), duration (seconds)."""
    async with websockets.connect(ROSBRIDGE_URL) as ws:
        # Get initial position
        await ws.send(json.dumps({
            'op': 'subscribe', 'topic': '/odom',
            'type': 'nav_msgs/msg/Odometry'
        }))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        start_pos = msg['msg']['pose']['pose']['position']
        
        # Send velocity
        await ws.send(json.dumps({
            'op': 'publish', 'topic': '/cmd_vel',
            'msg': {
                'linear': {'x': linear, 'y': 0.0, 'z': 0.0},
                'angular': {'x': 0.0, 'y': 0.0, 'z': angular}
            }
        }))
        
        await asyncio.sleep(duration)
        
        # Stop
        await ws.send(json.dumps({
            'op': 'publish', 'topic': '/cmd_vel',
            'msg': {
                'linear': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'angular': {'x': 0.0, 'y': 0.0, 'z': 0.0}
            }
        }))
        
        # Get final position
        await asyncio.sleep(0.2)
        last = None
        for _ in range(20):
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.2))
                last = m
            except:
                break
        
        if last:
            end_pos = last['msg']['pose']['pose']['position']
            dist = math.sqrt((end_pos['x'] - start_pos['x'])**2 + (end_pos['y'] - start_pos['y'])**2)
            return {
                'start': {'x': round(start_pos['x'], 3), 'y': round(start_pos['y'], 3)},
                'end': {'x': round(end_pos['x'], 3), 'y': round(end_pos['y'], 3)},
                'distance_moved': round(dist, 3)
            }


async def get_scan():
    """Get laser scan summary."""
    async with websockets.connect(ROSBRIDGE_URL) as ws:
        await ws.send(json.dumps({
            'op': 'subscribe', 'topic': '/scan',
            'type': 'sensor_msgs/msg/LaserScan'
        }))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        ranges = msg['msg']['ranges']
        await ws.send(json.dumps({'op': 'unsubscribe', 'topic': '/scan'}))
        
        # Summarize by direction
        n = len(ranges)
        directions = {
            'front': ranges[0] if n > 0 else None,
            'left': ranges[n//4] if n > n//4 else None,
            'back': ranges[n//2] if n > n//2 else None,
            'right': ranges[3*n//4] if n > 3*n//4 else None,
        }
        min_range = min(r for r in ranges if r > 0.01) if ranges else None
        return {'directions': directions, 'min_distance': round(min_range, 3) if min_range else None, 'num_readings': n}


async def main():
    if len(sys.argv) < 2:
        print("Usage: robot_control.py <command> [args]")
        print("Commands: position, move <linear> <angular> <duration>, scan, stop")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'position':
        result = await get_position()
        print(json.dumps(result))
    
    elif cmd == 'move':
        linear = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        angular = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        duration = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
        result = await move(linear, angular, duration)
        print(json.dumps(result))
    
    elif cmd == 'scan':
        result = await get_scan()
        print(json.dumps(result))
    
    elif cmd == 'stop':
        async with websockets.connect(ROSBRIDGE_URL) as ws:
            await ws.send(json.dumps({
                'op': 'publish', 'topic': '/cmd_vel',
                'msg': {'linear': {'x': 0.0, 'y': 0.0, 'z': 0.0}, 'angular': {'x': 0.0, 'y': 0.0, 'z': 0.0}}
            }))
        print(json.dumps({'status': 'stopped'}))
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == '__main__':
    asyncio.run(main())
