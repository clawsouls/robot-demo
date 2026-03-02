FROM ros:jazzy-ros-base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rosbridge-suite \
    ros-jazzy-turtlebot3-simulations \
    ros-jazzy-turtlebot3-msgs \
    ros-jazzy-turtlebot3-navigation2 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ENV TURTLEBOT3_MODEL=burger
ENV ROS_DOMAIN_ID=0

EXPOSE 9090

WORKDIR /ros2_ws

COPY virtual_robot.py /ros2_ws/virtual_robot.py
COPY ros2_entrypoint.sh /ros2_entrypoint.sh
RUN chmod +x /ros2_entrypoint.sh

ENTRYPOINT ["/ros2_entrypoint.sh"]
CMD ["ros2", "launch", "rosbridge_server", "rosbridge_websocket_launch.xml"]
