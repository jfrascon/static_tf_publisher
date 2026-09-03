"""Run ament_pep257 through the package test path."""

from pathlib import Path

from ament_pep257.main import main
import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.linter
@pytest.mark.pep257
def test_pep257() -> None:
    """Require Python docstrings to pass the ROS 2 PEP 257 policy."""
    assert main(argv=[str(PACKAGE_ROOT)]) == 0
