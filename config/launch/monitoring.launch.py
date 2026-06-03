"""
Launch all custom monitoring nodes in one command.

Usage:
  ros2 launch /autoware_config/launch/monitoring.launch.py \
    speed_limit_kmh:=50.0 \
    log_dir:=/results
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    speed_limit = LaunchConfiguration("speed_limit_kmh")
    log_dir = LaunchConfiguration("log_dir")

    return LaunchDescription([
        DeclareLaunchArgument("speed_limit_kmh", default_value="50.0"),
        DeclareLaunchArgument("log_dir",         default_value="/tmp"),

        Node(
            package="speed_monitor",
            executable="speed_monitor",
            name="speed_monitor",
            output="screen",
            parameters=[{
                "speed_limit_kmh": speed_limit,
                "log_path": PathJoinSubstitution([log_dir, "speed_log.csv"]),
            }],
        ),

        Node(
            package="violation_logger",
            executable="violation_logger",
            name="violation_logger",
            output="screen",
            parameters=[{
                "speed_limit_kmh":      speed_limit,
                "brake_threshold_ms2":  -4.0,
                "steer_rate_threshold":  0.5,
                "log_path": PathJoinSubstitution([log_dir, "violations.json"]),
            }],
        ),
    ])
