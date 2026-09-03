"""Test resources installed by static_tf_publisher."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory


def test_documentation_and_runtime_resources_are_installed() -> None:
    """Keep package-index resources aligned with the documented runtime contract."""
    share_directory = Path(get_package_share_directory('static_tf_publisher'))

    assert (share_directory / 'README.md').is_file()
    assert (share_directory / 'LICENSE').is_file()
    assert (share_directory / 'launch' / 'static_tf_publisher.launch.py').is_file()
    assert (share_directory / 'config' / 'example_params.yaml').is_file()
    assert (share_directory / 'docs' / 'frames.png').is_file()
