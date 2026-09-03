# static_tf_publisher

`static_tf_publisher` publishes a configured set of static transforms on ROS 2 TF.
Each transform defines the pose of one child frame with respect to one parent frame.
The node publishes the complete set once through `StaticTransformBroadcaster` and remains alive so late TF subscribers can receive the transient-local data.

## Frame model

Each child frame requires:

- `parent_frame`: parent frame ID.
- `pose.x`, `pose.y` and `pose.z`: translation in meters.
- `pose.R`, `pose.P` and `pose.Y`: roll, pitch and yaw in radians.

Every pose component must be numeric and finite.
A child frame cannot be its own parent.
The configured child-to-parent relationships cannot form a cycle.
A parent may refer to a frame published by another component.

An empty frame set is valid.
The node logs a warning and exits without publishing when no frames are configured.

## Launch contract

The launch file exposes:

| Argument | Default | Responsibility |
| --- | --- | --- |
| `namespace` | `robot` | Namespace where the node is launched. |
| `params_file` | empty | Optional YAML file containing frame parameters. |
| `params_file_allow_substs` | `False` | Allow ROS launch substitutions inside the YAML file. |
| `frames_inline` | empty | Optional JSON frame definitions applied after the YAML file. |
| `use_sim_time` | `False` | Select the ROS simulation clock. |
| `node_args` | standard JSON | Configure supported `launch_ros.actions.Node` arguments. |

The standard `node_args` value is:

```json
{"output":"both","ros_arguments":["--log-level","info"]}
```

The YAML file owns the base frame set.
`frames_inline` is applied afterward and therefore replaces individual frames with the same child name.
`use_sim_time` is appended last because clock selection belongs to the launch environment.

The obsolete `node_remappings`, `node_logging_options` and `node_options` arguments are no longer supported.
Use `node_args` for node name, output, remappings, respawn behavior and ROS arguments.

## YAML configuration

The installed example is `config/example_params.yaml`:

```yaml
/**/static_tf_publisher:
  ros__parameters:
    frames:
      camera_link:
        parent_frame: map
        pose:
          x: 0.0
          y: 0.0
          z: 1.0
          R: 0.0
          P: 0.0
          Y: 0.0

      charger_pose:
        parent_frame: map
        pose:
          x: 2.0
          y: 3.0
          z: 0.0
          R: 0.0
          P: 0.0
          Y: 1.57
```

Parameter files should not define `use_sim_time` because the launch argument is authoritative.

Launch the installed example with:

```bash
ros2 launch static_tf_publisher static_tf_publisher.launch.py \
  params_file:="$(ros2 pkg prefix static_tf_publisher)/share/static_tf_publisher/config/example_params.yaml"
```

This publishes:

- `map -> camera_link`
- `map -> charger_pose`

## Inline configuration

`frames_inline` accepts one JSON object keyed by child frame:

```bash
ros2 launch static_tf_publisher static_tf_publisher.launch.py \
  frames_inline:='{"camera_link":{"parent_frame":"map","pose":{"x":0,"y":0,"z":1,"R":0,"P":0,"Y":0}}}'
```

Every entry must contain exactly `parent_frame` and `pose`.
The pose must contain exactly `x`, `y`, `z`, `R`, `P` and `Y`.
Unknown keys are rejected so configuration typos do not disappear silently.

Both input forms may be combined:

```bash
ros2 launch static_tf_publisher static_tf_publisher.launch.py \
  params_file:=/absolute/path/to/frames.yaml \
  frames_inline:='{"camera_link":{"parent_frame":"map","pose":{"x":1,"y":0,"z":1,"R":0,"P":0,"Y":0}}}'
```

In this example, the inline `camera_link` replaces the complete frame definition loaded from the YAML file.

## TF result

These captures show representative results:

- [Two configured transforms](docs/frames.png)
- [YAML and inline transforms combined](docs/frames_params_cli.png)

## Build and test

From the workspace root:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --merge-install --symlink-install --packages-select static_tf_publisher
source install/setup.bash
colcon test --merge-install --packages-select static_tf_publisher
colcon test-result --test-result-base build/static_tf_publisher --verbose
```

## License

This package is distributed under the Apache License 2.0.
See [LICENSE](LICENSE).
