"""Launch the static transform publisher from a YAML file and optional inline frames."""

import json
import math
from numbers import Real
from pathlib import Path
from typing import Any

from launch import LaunchContext
from launch import LaunchDescription
from launch import LaunchDescriptionEntity
from launch.actions import DeclareLaunchArgument
from launch.actions import OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution
from launch.utilities.type_utils import perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
from launch_ros.parameter_descriptions import ParameterValue
import ros2_launch_helpers as rlh

POSE_COMPONENTS = ('x', 'y', 'z', 'R', 'P', 'Y')
DEFAULT_NODE_ARGS = '{"output":"both","ros_arguments":["--log-level","info"]}'


def generate_launch_description() -> LaunchDescription:
    """Declare the inputs required to launch the static transform publisher."""
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'namespace',
                default_value='robot',
                description='Namespace where the node is launched.',
            ),
            DeclareLaunchArgument(
                'params_file',
                default_value='',
                description='Optional YAML file with static transform parameters.',
            ),
            DeclareLaunchArgument(
                'params_file_allow_substs',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Allow ROS launch substitutions in params_file.',
            ),
            DeclareLaunchArgument(
                'frames_inline',
                default_value='',
                description=(
                    'Optional JSON object keyed by child frame. '
                    'Inline definitions override frames from params_file.'
                ),
            ),
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Use ROS simulation time when true.',
            ),
            DeclareLaunchArgument(
                'node_args',
                default_value=DEFAULT_NODE_ARGS,
                description=rlh.LAUNCH_ACTION_ARGUMENTS_DESC,
            ),
            OpaqueFunction(function=_launch_node),
        ]
    )


def _launch_node(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    """Resolve launch inputs and create the static transform publisher node."""
    parameters: list[Any] = []
    params_file = LaunchConfiguration('params_file').perform(ctx).strip()
    allow_substs = perform_typed_substitution(
        ctx,
        normalize_typed_substitution(LaunchConfiguration('params_file_allow_substs'), bool),
        bool,
    )

    if params_file:
        if not Path(params_file).is_file():
            raise FileNotFoundError(f"Params file '{params_file}' does not exist.")

        parameters.append(ParameterFile(params_file, allow_substs=allow_substs))

    frames_inline = LaunchConfiguration('frames_inline').perform(ctx).strip()

    if frames_inline:
        parameters.append(_build_inline_frame_parameters(frames_inline))

    # The launch environment owns clock selection.
    # Appending this value makes it authoritative if a custom YAML file also defines it.
    parameters.append(
        {'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}
    )

    return [
        Node(
            package='static_tf_publisher',
            executable='static_tf_publisher_node',
            namespace=LaunchConfiguration('namespace'),
            parameters=parameters,
            **rlh.resolve_node_arguments(
                LaunchConfiguration('node_args').perform(ctx),
                default_arguments={'name': 'static_tf_publisher'},
                extra_rejected_arguments={'namespace'},
            ),
        )
    ]


def _build_inline_frame_parameters(frames_inline: str) -> dict[str, Any]:
    """
    Convert one JSON frame object into the flattened ROS parameters consumed by the node.

    Input:

    ```json
    {"camera_link":{"parent_frame":"map","pose":{"x":0,"y":0,"z":1,"R":0,"P":0,"Y":0}}}
    ```

    Output keys use the form `frames.<child>.parent_frame` and
    `frames.<child>.pose.<component>`.
    """
    try:
        parsed_json: Any = json.loads(frames_inline)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON in frames_inline: {exc.msg}.') from exc

    if not isinstance(parsed_json, dict):
        raise ValueError('frames_inline must decode to one JSON object keyed by child frame.')

    frames_parameters: dict[str, Any] = {}
    normalized_child_frames: set[str] = set()

    for child_frame_name, raw_entry in parsed_json.items():
        if not isinstance(child_frame_name, str) or not child_frame_name.strip():
            raise ValueError('Each frame name in frames_inline must be a non-empty string.')

        child_frame = child_frame_name.strip()

        if child_frame in normalized_child_frames:
            raise ValueError(f"Frame '{child_frame}' is defined more than once in frames_inline.")

        normalized_child_frames.add(child_frame)

        if not isinstance(raw_entry, dict):
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline must define one JSON object."
            )

        unexpected_entry_keys = sorted(set(raw_entry) - {'parent_frame', 'pose'})

        if unexpected_entry_keys:
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline has unknown "
                f'keys: {unexpected_entry_keys}.'
            )

        parent_frame_value: Any = raw_entry.get('parent_frame')

        if not isinstance(parent_frame_value, str) or not parent_frame_value.strip():
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline must define a non-empty "
                "'parent_frame' string."
            )

        parent_frame = parent_frame_value.strip()

        if child_frame == parent_frame:
            raise ValueError(f"Frame '{child_frame}' cannot use itself as parent_frame.")

        pose_mapping: Any = raw_entry.get('pose')

        if not isinstance(pose_mapping, dict):
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline must define one 'pose' object."
            )

        unexpected_pose_keys = sorted(set(pose_mapping) - set(POSE_COMPONENTS))

        if unexpected_pose_keys:
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline has unknown pose components: "
                f'{unexpected_pose_keys}.'
            )

        missing_components = [
            component_name
            for component_name in POSE_COMPONENTS
            if component_name not in pose_mapping
        ]

        if missing_components:
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline is missing pose components: "
                f'{missing_components}.'
            )

        frames_parameters[f'frames.{child_frame}.parent_frame'] = parent_frame

        for component_name in POSE_COMPONENTS:
            component_value = pose_mapping[component_name]

            if not isinstance(component_value, Real) or isinstance(component_value, bool):
                raise ValueError(
                    f"Pose component '{component_name}' for frame '{child_frame}' in "
                    'frames_inline must be numeric.'
                )

            numeric_value = float(component_value)

            if not math.isfinite(numeric_value):
                raise ValueError(
                    f"Pose component '{component_name}' for frame '{child_frame}' in "
                    'frames_inline must be finite.'
                )

            frames_parameters[f'frames.{child_frame}.pose.{component_name}'] = numeric_value

    return frames_parameters
