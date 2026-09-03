"""Run ament_flake8 through the package test path."""

from pathlib import Path

from ament_flake8.main import main_with_errors
import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.flake8
@pytest.mark.linter
def test_flake8() -> None:
    """Require Python code to pass the package Flake8 configuration."""
    return_code, errors = main_with_errors(
        argv=['--config', str(PACKAGE_ROOT / 'ament_flake8.ini'), str(PACKAGE_ROOT)]
    )

    assert return_code == 0, '\n'.join(errors)
