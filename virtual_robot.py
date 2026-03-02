#!/usr/bin/env python3
"""Virtual TurtleBot3 robot node — simulates movement without Gazebo.
Subscribes to /cmd_vel, publishes /odom and /scan with ray-cast obstacles."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster
import math


# ── World Map ────────────────────────────────────────────────
# Walls: list of line segments [(x1,y1,x2,y2)]
WALLS = [
    # Outer boundary (10m x 10m room)
    (-5, -5, 5, -5),   # bottom
    (5, -5, 5, 5),     # right
    (5, 5, -5, 5),     # top
    (-5, 5, -5, -5),   # left
    # Internal walls
    (2, -5, 2, -1),    # vertical wall
    (-3, 2, 1, 2),     # horizontal wall
]

# Cliff zones: circles (cx, cy, radius) — falling hazard
CLIFFS = [
    (3.0, 3.0, 1.0),   # cliff zone at (3,3), radius 1m
]

# Human positions: circles (cx, cy, radius)
HUMANS = [
    (-2.0, -2.0, 0.3),  # person standing at (-2,-2)
    (0.0, 4.0, 0.3),    # person at (0,4)
]

# All obstacles for scan: walls + humans (cliffs are floor hazards, not scan-visible)
# We'll publish cliff info on a separate topic or encode in scan


def ray_segment_intersect(ox, oy, angle, x1, y1, x2, y2):
    """Ray from (ox,oy) at angle vs line segment (x1,y1)-(x2,y2). Returns distance or None."""
    dx = math.cos(angle)
    dy = math.sin(angle)
    sx = x2 - x1
    sy = y2 - y1
    denom = dx * sy - dy * sx
    if abs(denom) < 1e-10:
        return None
    t = ((x1 - ox) * sy - (y1 - oy) * sx) / denom
    u = ((x1 - ox) * dy - (y1 - oy) * dx) / denom
    if t > 0.01 and 0 <= u <= 1:
        return t
    return None


def ray_circle_intersect(ox, oy, angle, cx, cy, cr):
    """Ray from (ox,oy) at angle vs circle (cx,cy,cr). Returns distance or None."""
    dx = math.cos(angle)
    dy = math.sin(angle)
    fx = ox - cx
    fy = oy - cy
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - cr * cr
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    disc = math.sqrt(disc)
    t1 = (-b - disc) / (2 * a)
    t2 = (-b + disc) / (2 * a)
    if t1 > 0.01:
        return t1
    if t2 > 0.01:
        return t2
    return None


def point_in_circle(px, py, cx, cy, cr):
    return (px - cx)**2 + (py - cy)**2 < cr * cr


class VirtualRobot(Node):
    def __init__(self):
        super().__init__('virtual_robot')

        # State
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.linear_vel = 0.0
        self.angular_vel = 0.0
        self.last_time = self.get_clock().now()
        self.fallen = False  # fell off cliff

        # Subscribers
        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.scan_pub = self.create_publisher(LaserScan, '/scan', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Timer: 20Hz update
        self.timer = self.create_timer(0.05, self.update)

        self.get_logger().info(f'Virtual robot started at ({self.x:.1f}, {self.y:.1f})')
        self.get_logger().info(f'World: {len(WALLS)} walls, {len(CLIFFS)} cliffs, {len(HUMANS)} humans')

    def cmd_vel_callback(self, msg: Twist):
        if self.fallen:
            self.get_logger().warn('Robot has fallen off cliff! Ignoring cmd_vel.')
            return
        self.linear_vel = msg.linear.x
        self.angular_vel = msg.angular.z
        self.get_logger().info(f'cmd_vel: linear={msg.linear.x:.2f} angular={msg.angular.z:.2f}')

    def update(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        if not self.fallen:
            # Proposed new position
            new_theta = self.theta + self.angular_vel * dt
            new_x = self.x + self.linear_vel * math.cos(new_theta) * dt
            new_y = self.y + self.linear_vel * math.sin(new_theta) * dt

            # Collision check: don't move into walls (within 0.15m = robot radius)
            blocked = False
            for (x1, y1, x2, y2) in WALLS:
                dist = self._point_to_segment_dist(new_x, new_y, x1, y1, x2, y2)
                if dist < 0.15:
                    blocked = True
                    break
            # Don't move into humans
            if not blocked:
                for (cx, cy, cr) in HUMANS:
                    if math.sqrt((new_x - cx)**2 + (new_y - cy)**2) < cr + 0.15:
                        blocked = True
                        break

            if not blocked:
                self.theta = new_theta
                self.x = new_x
                self.y = new_y

            # Check cliff fall
            for (cx, cy, cr) in CLIFFS:
                if point_in_circle(self.x, self.y, cx, cy, cr):
                    self.fallen = True
                    self.linear_vel = 0.0
                    self.angular_vel = 0.0
                    self.get_logger().error(f'ROBOT FELL OFF CLIFF at ({self.x:.2f}, {self.y:.2f})!')
                    break

        # Publish odometry
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = math.sin(self.theta / 2)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2)
        odom.twist.twist.linear.x = self.linear_vel
        odom.twist.twist.angular.z = self.angular_vel
        self.odom_pub.publish(odom)

        # Publish TF
        t = TransformStamped()
        t.header.stamp = now.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.rotation.z = math.sin(self.theta / 2)
        t.transform.rotation.w = math.cos(self.theta / 2)
        self.tf_broadcaster.sendTransform(t)

        # Publish laser scan with ray casting
        scan = LaserScan()
        scan.header.stamp = now.to_msg()
        scan.header.frame_id = 'base_scan'
        scan.angle_min = 0.0
        scan.angle_max = 2 * math.pi
        n_rays = 360
        scan.angle_increment = 2 * math.pi / n_rays
        scan.range_min = 0.12
        scan.range_max = 3.5
        ranges = []

        for i in range(n_rays):
            angle = self.theta + i * scan.angle_increment
            min_dist = scan.range_max

            # Check walls
            for (x1, y1, x2, y2) in WALLS:
                d = ray_segment_intersect(self.x, self.y, angle, x1, y1, x2, y2)
                if d is not None and d < min_dist:
                    min_dist = d

            # Check humans (as cylindrical obstacles)
            for (cx, cy, cr) in HUMANS:
                d = ray_circle_intersect(self.x, self.y, angle, cx, cy, cr)
                if d is not None and d < min_dist:
                    min_dist = d

            ranges.append(max(scan.range_min, min(min_dist, scan.range_max)))

        scan.ranges = ranges
        self.scan_pub.publish(scan)

    def _point_to_segment_dist(self, px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.sqrt((px - proj_x)**2 + (py - proj_y)**2)


def main():
    rclpy.init()
    node = VirtualRobot()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
