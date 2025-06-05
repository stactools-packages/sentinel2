import pytest


def pytest_addoption(parser):
    """Add custom options & settings to py.test."""
    help_str = "Update test expectation fixtures."
    parser.addoption(
        "--update-expectations", action="store_true", help=help_str, default=False
    )


@pytest.fixture
def update_expectations(pytestconfig):
    return pytestconfig.getoption("update_expectations")
