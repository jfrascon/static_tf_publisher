from __future__ import annotations

import math
from typing import Iterable

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

from static_tf_publisher.frame_config import FrameSpec, parse_frames

class FramePublisherNode(Node):
    """Publish all configured static transforms at startup and keep the node alive."""

    def __init__(self) -> None:
        super().__init__('static_tf_publisher', automatically_declare_parameters_from_overrides=True)
        self._should_exit: bool = False
        self._transforms: list[TransformStamped] = []
        self._broadcaster = StaticTransformBroadcaster(self)

        # Parse the full frame set once during startup. Invalid entries abort startup.
        frame_specs: list[FrameSpec] = parse_frames(self._get_frame_parameters())
        if not frame_specs:
            # An empty configuration is allowed. Warn and exit without spinning forever.
            self.get_logger().warning(
                "No frames were configured under 'frames'. The node will exit without publishing "
                'static transforms.'
            )
            self._should_exit = True
            return

        # Static transforms are published once and then kept available by the node.
        self._transforms = self._build_transforms(frame_specs)
        self._broadcaster.sendTransform(self._transforms)
        self.get_logger().info(f'Published {len(self._transforms)} static transforms.')

    def _build_transforms(self, frame_specs: Iterable[FrameSpec]) -> list[TransformStamped]:
        stamp: Time = self.get_clock().now().to_msg()
        return [self._build_transform_message(frame_spec, stamp) for frame_spec in frame_specs]

    def _get_frame_parameters(self) -> dict[str, object]:
        """
        Return the flattened ROS parameters that live under the 'frames' prefix.

        Nested YAML keys become dot-delimited ROS parameter names.
        """
        frame_parameters: dict[str, object] = {
            parameter_name: getattr(parameter, 'value', parameter)
            for parameter_name, parameter in self.get_parameters_by_prefix('frames').items()
        }
        return frame_parameters

    @property
    def should_exit(self) -> bool:
        """Return whether the node should terminate immediately after startup."""
        return self._should_exit

    def _build_transform_message(self, frame_spec: FrameSpec, stamp: Time) -> TransformStamped:
        """Create one TransformStamped message from one validated frame spec."""
        transform: TransformStamped = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = frame_spec.parent_frame
        transform.child_frame_id = frame_spec.child_frame

        transform.transform.translation.x = frame_spec.x
        transform.transform.translation.y = frame_spec.y
        transform.transform.translation.z = frame_spec.z

        # TF messages use quaternions, so convert the configured roll-pitch-yaw first.
        qx, qy, qz, qw = self._quaternion_from_rpy(frame_spec.roll, frame_spec.pitch, frame_spec.yaw)
        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw

        return transform

    @staticmethod
    def _quaternion_from_rpy(roll: float, pitch: float, yaw: float) -> tuple[float, float, float, float]:
        """Convert one roll-pitch-yaw triple in radians into one quaternion."""
        half_roll = roll * 0.5
        half_pitch = pitch * 0.5
        half_yaw = yaw * 0.5

        cr = math.cos(half_roll)
        sr = math.sin(half_roll)
        cp = math.cos(half_pitch)
        sp = math.sin(half_pitch)
        cy = math.cos(half_yaw)
        sy = math.sin(half_yaw)

        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        qw = cr * cp * cy + sr * sp * sy

        return qx, qy, qz, qw


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node: FramePublisherNode | None = None

    try:
        node = FramePublisherNode()
        # Exit immediately when startup determined there is nothing to publish.
        if node.should_exit:
            return
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
