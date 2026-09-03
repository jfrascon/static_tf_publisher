import importlib.util
import json
from pathlib import Path

import pytest

LAUNCH_MODULE_PATH = (
    Path(__file__).resolve().parent.parent / 'launch' / 'static_tf_publisher.launch.py'
)
SPEC = importlib.util.spec_from_file_location('static_tf_publisher_launch', LAUNCH_MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
LAUNCH_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAUNCH_MODULE)
_build_inline_frame_parameters = LAUNCH_MODULE._build_inline_frame_parameters


def test_build_inline_frame_parameters_valid() -> None:
    parameters = _build_inline_frame_parameters(
        json.dumps(
            {
                'camera_link': {
                    'parent_frame': 'map',
                    'pose': {'x': 0.0, 'y': 0.0, 'z': 1.0, 'R': 0.0, 'P': 0.0, 'Y': 0.0},
                }
            }
        )
    )

    assert parameters == {
        'frames.camera_link.parent_frame': 'map',
        'frames.camera_link.pose.x': 0.0,
        'frames.camera_link.pose.y': 0.0,
        'frames.camera_link.pose.z': 1.0,
        'frames.camera_link.pose.R': 0.0,
        'frames.camera_link.pose.P': 0.0,
        'frames.camera_link.pose.Y': 0.0,
    }


def test_build_inline_frame_parameters_rejects_non_object() -> None:
    with pytest.raises(ValueError, match='must decode to one JSON object'):
        _build_inline_frame_parameters('[]')


def test_build_inline_frame_parameters_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match='Invalid JSON in frames_inline'):
        _build_inline_frame_parameters('{')


@pytest.mark.parametrize('value', ['1.0', True, float('inf')])
def test_build_inline_frame_parameters_rejects_invalid_pose_values(value: object) -> None:
    frames_inline = json.dumps(
        {
            'camera_link': {
                'parent_frame': 'map',
                'pose': {'x': value, 'y': 0, 'z': 1, 'R': 0, 'P': 0, 'Y': 0},
            }
        }
    )

    with pytest.raises(ValueError, match="Pose component 'x'"):
        _build_inline_frame_parameters(frames_inline)


def test_build_inline_frame_parameters_rejects_unknown_keys() -> None:
    frames_inline = (
        '{"camera_link":{"parent_frame":"map","unexpected":true,'
        '"pose":{"x":0,"y":0,"z":1,"R":0,"P":0,"Y":0}}}'
    )

    with pytest.raises(ValueError, match='unknown keys'):
        _build_inline_frame_parameters(frames_inline)


def test_build_inline_frame_parameters_rejects_duplicate_normalized_names() -> None:
    frames_inline = (
        '{"camera_link":{"parent_frame":"map","pose":'
        '{"x":0,"y":0,"z":1,"R":0,"P":0,"Y":0}},'
        '" camera_link ":{"parent_frame":"map","pose":'
        '{"x":0,"y":0,"z":1,"R":0,"P":0,"Y":0}}}'
    )

    with pytest.raises(ValueError, match='defined more than once'):
        _build_inline_frame_parameters(frames_inline)
