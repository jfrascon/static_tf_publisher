import json

from conftest import run_bash


def test_static_tf_publisher_launch_smoke() -> None:
    frames_inline = json.dumps(
        {
            'camera_link': {
                'parent_frame': 'map',
                'pose': {'x': 0.0, 'y': 0.0, 'z': 1.0, 'R': 0.0, 'P': 0.0, 'Y': 0.0},
            },
            'charger_pose': {
                'parent_frame': 'map',
                'pose': {'x': 2.0, 'y': 3.0, 'z': 0.0, 'R': 0.0, 'P': 0.0, 'Y': 1.57},
            },
        },
        separators=(',', ':'),
    )
    result = run_bash(
        'timeout --signal=INT 8s ros2 launch static_tf_publisher static_tf_publisher.launch.py '
        f"frames_inline:='{frames_inline}'"
    )

    output = result.stdout + result.stderr

    # timeout returns 124 when the launch keeps running as expected until interrupted.
    assert result.returncode in {0, 124}, output
    assert 'process started with pid' in output, output
    assert 'Published 2 static transforms.' in output, output
    assert 'Traceback' not in output, output
