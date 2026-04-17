from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from typing import Any

POSE_COMPONENTS = ('x', 'y', 'z', 'R', 'P', 'Y')


@dataclass(frozen=True)
class FrameSpec:
    child_frame: str
    parent_frame: str
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


def parse_frames(frames_parameters: Mapping[str, Any]) -> list[FrameSpec]:
    """
    Parse the flattened ROS parameters under `frames` into validated FrameSpec objects.

    The input mapping contains parameter names such as `camera_link.parent_frame`
    and `camera_link.pose.x`. This function groups those flattened parameter
    names by child frame, validates that each grouped entry defines one complete
    transform, and returns one FrameSpec per child frame.

    Example input:
    {
        'camera_link.parent_frame': 'map',
        'camera_link.pose.x': 0.0,
        'camera_link.pose.y': 0.0,
        'camera_link.pose.z': 1.0,
        'camera_link.pose.R': 0.0,
        'camera_link.pose.P': 0.0,
        'camera_link.pose.Y': 0.0,
    }

    Example output:
    [
        FrameSpec(
            child_frame='camera_link',
            parent_frame='map',
            x=0.0,
            y=0.0,
            z=1.0,
            roll=0.0,
            pitch=0.0,
            yaw=0.0,
        )
    ]
    """
    if not frames_parameters:
        return []

    # Rebuild one nested entry per child frame from the flattened ROS parameter names.
    raw_entries: dict[str, dict[str, Any]] = {}

    # Walk every flattened parameter and group it back into one logical entry per child frame.
    # Example: `camera_link.parent_frame` and `camera_link.pose.x` both end up under the
    # reconstructed `camera_link` entry inside `raw_entries`.
    # One reconstructed entry looks like:
    # `raw_entries['camera_link'] = {'parent_frame': 'map', 'pose': {'x': 0.0, ...}}`
    for parameter_name, value in sorted(frames_parameters.items()):
        parts: list[str] = parameter_name.split('.')

        if len(parts) < 2:
            raise ValueError(
                f"Invalid parameter under 'frames': '{parameter_name}'. "
                "Expected '<child>.parent_frame' or '<child>.pose.<component>'."
            )

        if parts[-1] == 'parent_frame':
            child_frame: str = '.'.join(parts[:-1]).strip()
            entry: dict[str, Any] = raw_entries.setdefault(child_frame, {})
            entry['parent_frame'] = value
            continue

        if len(parts) >= 3 and parts[-2] == 'pose' and parts[-1] in POSE_COMPONENTS:
            child_frame = '.'.join(parts[:-2]).strip()
            entry = raw_entries.setdefault(child_frame, {})
            pose_values: dict[str, Any] = entry.setdefault('pose', {})
            pose_values[parts[-1]] = value
            continue

        raise ValueError(
            f"Invalid parameter under 'frames': '{parameter_name}'. "
            "Expected '<child>.parent_frame' or '<child>.pose.<x|y|z|R|P|Y>'."
        )

    # Validate each reconstructed entry and convert it into the typed object used by the ROS node.
    # Example:
    # `raw_entries['camera_link'] = {'parent_frame': 'map', 'pose': {'x': 0.0, ...}}`
    # becomes:
    # `FrameSpec(child_frame='camera_link', parent_frame='map', x=0.0, ...)`
    frame_specs: list[FrameSpec] = []

    for child_frame_name in sorted(raw_entries):
        raw_entry: Mapping[str, Any] = raw_entries[child_frame_name]
        child_frame: str = _validate_non_empty_string(child_frame_name, 'Frame name')
        parent_frame: str = _validate_non_empty_string(
            raw_entry.get('parent_frame'), f"Parent frame for '{child_frame}'"
        )

        if child_frame == parent_frame:
            raise ValueError(f"Frame '{child_frame}' cannot use itself as parent_frame.")

        # Validate the full pose block before converting the values into one FrameSpec.
        pose_mapping: Any = raw_entry.get('pose')

        if not isinstance(pose_mapping, Mapping):
            raise ValueError(f"Frame '{child_frame}' must define one 'pose' mapping.")

        missing_components: list[str] = [
            component for component in POSE_COMPONENTS if component not in pose_mapping
        ]

        if missing_components:
            raise ValueError(f"Frame '{child_frame}' is missing pose components: {missing_components}.")

        frame_specs.append(
            FrameSpec(
                child_frame=child_frame,
                parent_frame=parent_frame,
                x=_as_float(child_frame, 'x', pose_mapping['x']),
                y=_as_float(child_frame, 'y', pose_mapping['y']),
                z=_as_float(child_frame, 'z', pose_mapping['z']),
                roll=_as_float(child_frame, 'R', pose_mapping['R']),
                pitch=_as_float(child_frame, 'P', pose_mapping['P']),
                yaw=_as_float(child_frame, 'Y', pose_mapping['Y']),
            )
        )

    return frame_specs


def _as_float(child_frame: str, component_name: str, value: Any) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise ValueError(f"Pose component '{component_name}' for frame '{child_frame}' must be numeric.")

    return float(value)


def _validate_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a non-empty string.')

    return value.strip()
