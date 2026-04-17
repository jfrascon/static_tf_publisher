import json
from pathlib import Path
from typing import Any, List

import ros2_launch_helpers as rlh
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity  # noqa

POSE_COMPONENTS = ('x', 'y', 'z', 'R', 'P', 'Y')


def generate_launch_description() -> LaunchDescription:
    # Mirror the launch structure used by the rest of the workspace packages.
    return LaunchDescription(
        [
            DeclareLaunchArgument('namespace', default_value='robot', description='Namepace'),
            DeclareLaunchArgument('params_file', default_value='', description='Base YAML with ros__parameters'),
            DeclareLaunchArgument(
                'frames_inline',
                default_value='',
                description='JSON object with inline frames. This takes precedence over any frames '
                'defined in the params_file. Example: \'{"frame1": {"parent_frame": "world", '
                '"pose": {"x": 1.0, "y": 2.0, "z": 3.0, "R": 0.1, "P": 0.2, "Y": 0.3}}}\'',
            ),
            DeclareLaunchArgument(
                'use_sim_time',
                default_value='False',
                choices=['True', 'true', 'False', 'false'],
                description='Use simulation clock if true',
            ),
            DeclareLaunchArgument('node_remappings', default_value='', description=rlh.REMAPPINGS_DESC),
            DeclareLaunchArgument(
                'node_logging_options',
                default_value=rlh.default_logging_options_str(),
                description=rlh.LOGGING_OPTIONS_DESC,
            ),
            DeclareLaunchArgument(
                'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
            ),
            OpaqueFunction(function=launch_static_tf_publisher_node),
        ]
    )


def launch_static_tf_publisher_node(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    # If the params_file exists, load it as a ParameterFile.
    # If any parameter is also provided to this launch file, it takes precedence over the
    # params_file.
    # This allows to override specific parameters in the params_file without having to create a new
    # params file.
    parameters: List[Any] = []

    params_file: str = LaunchConfiguration('params_file').perform(ctx).strip()

    if params_file:
        if not Path(params_file).is_file():
            raise FileNotFoundError(f"Params file '{params_file}' does not exist.")

        parameters.append(ParameterFile(params_file, allow_substs=True))

    frames_inline: str = LaunchConfiguration('frames_inline').perform(ctx).strip()

    if frames_inline:
        parameters.append(_build_inline_frame_parameters(frames_inline))

    parameters.append({'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)})

    # Reuse the common node option parsing so output, respawn and node name stay consistent.
    node_options: dict[str, Any] = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name: str = str(node_options['name']) or 'static_tf_publisher'

    if not rlh.is_valid_name(node_name):
        raise RuntimeError(f"The name of the node must be ASCII [A-Za-z0-9_] only: '{node_name}'")

    return [
        Node(
            package='static_tf_publisher',
            executable='static_tf_publisher_node',
            name=node_name,
            namespace=LaunchConfiguration('namespace'),
            parameters=parameters,
            remappings=rlh.process_remappings(LaunchConfiguration('node_remappings').perform(ctx)),
            ros_arguments=rlh.process_node_logging_options(LaunchConfiguration('node_logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    ]


def _build_inline_frame_parameters(frames_inline: str) -> dict[str, Any]:
    """
    Convert one JSON object of inline frames into the `frames.*` parameter model used by the node.

    Example input:
    {"camera_link":{"parent_frame":"map","pose":{"x":0.0,"y":0.0,"z":1.0,"R":0.0,"P":0.0,"Y":0.0}}}

    Example output:
    {
        "frames.camera_link.parent_frame": "map",
        "frames.camera_link.pose.x": 0.0,
        "frames.camera_link.pose.y": 0.0,
        "frames.camera_link.pose.z": 1.0,
        "frames.camera_link.pose.R": 0.0,
        "frames.camera_link.pose.P": 0.0,
        "frames.camera_link.pose.Y": 0.0,
    }
    """
    try:
        parsed_json: Any = json.loads(frames_inline)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON in frames_inline: {exc.msg}.') from exc

    if not isinstance(parsed_json, dict):
        raise ValueError('frames_inline must decode to one JSON object keyed by child frame.')

    frames_parameters: dict[str, Any] = {}

    # Flatten each child-frame object into the `frames.<child>.*` parameter namespace.
    for child_frame_name, raw_entry in parsed_json.items():
        if not isinstance(child_frame_name, str) or not child_frame_name.strip():
            raise ValueError('Each frame name in frames_inline must be a non-empty string.')

        child_frame: str = child_frame_name.strip()

        if not isinstance(raw_entry, dict):
            raise ValueError(f"Frame '{child_frame}' in frames_inline must define one JSON object.")

        if 'parent_frame' not in raw_entry:
            raise ValueError(f"Frame '{child_frame}' in frames_inline must define the 'parent_frame' key.")

        parent_frame_value: Any = raw_entry.get('parent_frame')

        # Fail early in the launch layer if one inline frame names an invalid parent.
        # The node keeps the full validation too, but this catches malformed JSON input
        # before ROS starts the process.
        if not isinstance(parent_frame_value, str) or not parent_frame_value.strip():
            raise ValueError(f"Frame '{child_frame}' in frames_inline must define a non-empty 'parent_frame' string.")

        frames_parameters[f'frames.{child_frame}.parent_frame'] = parent_frame_value.strip()

        pose_mapping: Any = raw_entry.get('pose')

        if pose_mapping is None:
            raise ValueError(f"Frame '{child_frame}' in frames_inline must define the 'pose' key.")

        if not isinstance(pose_mapping, dict):
            raise ValueError(f"Frame '{child_frame}' in frames_inline must define one 'pose' object.")

        # Copy every pose component into the flattened parameter dictionary.
        missing_components: list[str] = [
            component_name for component_name in POSE_COMPONENTS if component_name not in pose_mapping
        ]

        if missing_components:
            raise ValueError(
                f"Frame '{child_frame}' in frames_inline is missing pose components: {missing_components}."
            )

        for component_name in POSE_COMPONENTS:
            component_value: Any = pose_mapping[component_name]

            try:
                frames_parameters[f'frames.{child_frame}.pose.{component_name}'] = float(component_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Pose component '{component_name}' for frame '{child_frame}' in frames_inline must be numeric."
                ) from exc

    return frames_parameters
