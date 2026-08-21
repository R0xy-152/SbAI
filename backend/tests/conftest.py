import pytest


@pytest.fixture(autouse=True)
def _disable_auth_for_legacy_tests(monkeypatch):
    """Old runtime/API tests predate docs/18; dedicated auth tests opt back in."""
    monkeypatch.setenv("GAL_AUTH_REQUIRED", "false")
    monkeypatch.setenv("GAL_AUTH_BACKEND", "memory")
