from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity  # noqa
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue
from ament_index_python.packages import get_package_share_directory

import ros2_launch_helpers as rlh

import os
from pathlib import Path
from typing import Any, List


def generate_launch_description() -> LaunchDescription:
    # Mirror the launch structure used by the rest of the workspace packages.
    return LaunchDescription(
        [
            DeclareLaunchArgument('namespace', default_value='robot', description='Namepace'),
            DeclareLaunchArgument(
                'params_file',
                default_value=os.path.join(
                    get_package_share_directory('static_tf_publisher'),
                    'config',
                    'example_params.yaml',
                ),
                description='Base YAML with ros__parameters',
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
                'node_options',
                default_value=rlh.default_node_options_str(),
                description=rlh.NODE_OPTIONS_DESC,
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
