import os
from collections.abc import Sequence
from glob import glob

from setuptools import find_packages, setup

package_name = 'static_tf_publisher'


def _glob_files(pattern: str) -> list[str]:
    """Return only regular files that match one glob pattern."""
    return [path for path in glob(pattern) if os.path.isfile(path)]


def _walk_data_files(source_root: str, install_root: str) -> list[tuple[str, Sequence[str]]]:
    """Return data_files entries for every regular file under one directory tree."""
    data_files: list[tuple[str, Sequence[str]]] = []

    for current_root, _, filenames in os.walk(source_root):
        if not filenames:
            continue

        relative_dir = os.path.relpath(current_root, source_root)
        install_dir = install_root if relative_dir == '.' else os.path.join(install_root, relative_dir)
        files: Sequence[str] = [os.path.join(current_root, filename) for filename in sorted(filenames)]
        data_files.append((install_dir, files))

    return data_files


# Install launch and config assets so `ros2 launch` can find the shipped examples.
data_files: list[tuple[str, Sequence[str]]] = [
    ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
    (f'share/{package_name}', ['package.xml']),
    (f'share/{package_name}/launch', _glob_files('launch/*')),
]
data_files += _walk_data_files('config', f'share/{package_name}/config')


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test', 'tests']),
    data_files=data_files,
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='eutrob',
    maintainer_email='eurecat@eurecat.org',
    description='Publish static TF transforms from ROS 2 parameters',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={'console_scripts': ['static_tf_publisher_node = static_tf_publisher.static_tf_publisher_node:main']},
    python_requires='>=3.8',
)
