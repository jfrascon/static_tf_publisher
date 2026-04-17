import pytest

from static_tf_publisher.frame_config import parse_frames


def test_parse_frames_returns_empty_list_for_empty_configuration() -> None:
    specs = parse_frames({})
    assert specs == []


def test_parse_frames_valid() -> None:
    specs = parse_frames(
        {
            'camera_link.parent_frame': 'map',
            'camera_link.pose.x': 0.0,
            'camera_link.pose.y': 0.0,
            'camera_link.pose.z': 1.0,
            'camera_link.pose.R': 0.0,
            'camera_link.pose.P': 0.0,
            'camera_link.pose.Y': 0.0,
            'charger_pose.parent_frame': 'map',
            'charger_pose.pose.x': 2.0,
            'charger_pose.pose.y': 3.0,
            'charger_pose.pose.z': 0.0,
            'charger_pose.pose.R': 0.0,
            'charger_pose.pose.P': 0.0,
            'charger_pose.pose.Y': 1.57,
        }
    )

    assert [spec.child_frame for spec in specs] == ['camera_link', 'charger_pose']
    assert specs[0].parent_frame == 'map'
    assert specs[1].yaw == pytest.approx(1.57)


def test_parse_frames_rejects_missing_parent_frame() -> None:
    with pytest.raises(ValueError, match='Parent frame'):
        parse_frames(
            {
                'camera_link.pose.x': 0.0,
                'camera_link.pose.y': 0.0,
                'camera_link.pose.z': 1.0,
                'camera_link.pose.R': 0.0,
                'camera_link.pose.P': 0.0,
                'camera_link.pose.Y': 0.0,
            }
        )


def test_parse_frames_rejects_incomplete_pose() -> None:
    with pytest.raises(ValueError, match='missing pose components'):
        parse_frames(
            {
                'camera_link.parent_frame': 'map',
                'camera_link.pose.x': 0.0,
                'camera_link.pose.y': 0.0,
                'camera_link.pose.z': 1.0,
                'camera_link.pose.R': 0.0,
                'camera_link.pose.P': 0.0,
            }
        )


def test_parse_frames_rejects_non_numeric_pose() -> None:
    with pytest.raises(ValueError, match='must be numeric'):
        parse_frames(
            {
                'camera_link.parent_frame': 'map',
                'camera_link.pose.x': 'bad',
                'camera_link.pose.y': 0.0,
                'camera_link.pose.z': 1.0,
                'camera_link.pose.R': 0.0,
                'camera_link.pose.P': 0.0,
                'camera_link.pose.Y': 0.0,
            }
        )


def test_parse_frames_rejects_same_parent_and_child() -> None:
    with pytest.raises(ValueError, match='cannot use itself as parent_frame'):
        parse_frames(
            {
                'map.parent_frame': 'map',
                'map.pose.x': 0.0,
                'map.pose.y': 0.0,
                'map.pose.z': 0.0,
                'map.pose.R': 0.0,
                'map.pose.P': 0.0,
                'map.pose.Y': 0.0,
            }
        )
