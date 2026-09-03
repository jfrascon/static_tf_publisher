"""Run ament_xmllint through the package test path."""

from pathlib import Path

from ament_xmllint.main import main
import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.linter
@pytest.mark.xmllint
def test_xmllint() -> None:
    """Require package.xml to remain valid without network access."""
    assert main(argv=[str(PACKAGE_ROOT / 'package.xml')]) == 0
