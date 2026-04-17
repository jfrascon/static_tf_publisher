from conftest import run_bash


def test_static_tf_publisher_launch_smoke() -> None:
    result = run_bash('timeout --signal=INT 8s ros2 launch static_tf_publisher static_tf_publisher.launch.py')

    output = result.stdout + result.stderr

    # timeout returns 124 when the launch keeps running as expected until interrupted.
    assert result.returncode in {0, 124}, output
    assert 'process started with pid' in output, output
    assert 'Published 2 static transforms.' in output, output
