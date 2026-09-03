"""Test the public static_tf_publisher launch contract."""

import importlib.util
from pathlib import Path
from types import ModuleType

from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODE_ARGS = '{"output":"both","ros_arguments":["--log-level","info"]}'


def _load_launch_module() -> ModuleType:
    """Load the package launch file from the source tree."""
    path = PACKAGE_ROOT / 'launch' / 'static_tf_publisher.launch.py'
    spec = importlib.util.spec_from_file_location('static_tf_publisher_launch', path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launch_exposes_the_current_argument_contract() -> None:
    """Protect the parameter-file, inline-frame, clock, and node argument inputs."""
    module = _load_launch_module()
    declarations = {
        action.name: action
        for action in module.generate_launch_description().entities
        if isinstance(action, DeclareLaunchArgument)
    }

    assert set(declarations) == {
        'namespace',
        'params_file',
        'params_file_allow_substs',
        'frames_inline',
        'use_sim_time',
        'node_args',
    }

    context = LaunchContext()
    declarations['node_args'].visit(context)
    assert context.launch_configurations['node_args'] == DEFAULT_NODE_ARGS


@pytest.mark.parametrize('allow_substs', ['True', 'False'])
def test_launch_passes_shared_parameters_and_clock_to_the_node(
    allow_substs: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass the YAML, inline overrides, and launch-owned clock through separate parameter layers."""
    module = _load_launch_module()
    params_file = tmp_path / 'params.yaml'
    params_file.write_text('/**:\n  ros__parameters:\n    frames: {}\n', encoding='utf-8')
    captured: dict[str, object] = {}

    class FakeNode:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(module, 'Node', FakeNode)
    context = LaunchContext()
    context.launch_configurations.update(
        {
            'namespace': 'robot',
            'params_file': str(params_file),
            'params_file_allow_substs': allow_substs,
            'frames_inline': (
                '{"camera_link":{"parent_frame":"map","pose":'
                '{"x":0,"y":0,"z":1,"R":0,"P":0,"Y":0}}}'
            ),
            'use_sim_time': 'False',
            'node_args': DEFAULT_NODE_ARGS,
        }
    )

    actions = module._launch_node(context)

    assert len(actions) == 1
    assert captured['namespace'].perform(context) == 'robot'
    assert captured['name'] == 'static_tf_publisher'
    assert captured['output'] == 'both'
    assert captured['ros_arguments'] == ['--log-level', 'info']
    parameters = captured['parameters']
    assert len(parameters) == 3
    assert parameters[0].allow_substs is (allow_substs == 'True')
    assert parameters[1]['frames.camera_link.parent_frame'] == 'map'
    assert set(parameters[2]) == {'use_sim_time'}


def test_launch_rejects_a_missing_parameter_file(tmp_path: Path) -> None:
    """Reject an explicit missing YAML file before starting the node."""
    module = _load_launch_module()
    context = LaunchContext()
    context.launch_configurations.update(
        {
            'namespace': 'robot',
            'params_file': str(tmp_path / 'missing.yaml'),
            'params_file_allow_substs': 'False',
            'frames_inline': '',
            'use_sim_time': 'False',
            'node_args': DEFAULT_NODE_ARGS,
        }
    )

    with pytest.raises(FileNotFoundError, match='missing.yaml'):
        module._launch_node(context)
