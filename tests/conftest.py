# tests/conftest.py
import pytest
from unittest.mock import MagicMock
import sys

@pytest.fixture(autouse=True)
def mock_gspread(monkeypatch):
    """Mock Google Sheets-tilgang slik at tests kan kjøre uten credentials.json"""
    # Mock ServiceAccountCredentials
    import oauth2client.service_account as sac
    monkeypatch.setattr(
        sac.ServiceAccountCredentials,
        "from_json_keyfile_name",
        lambda *a, **kw: MagicMock()
    )

    # Mock gspread.authorize
    import gspread
    monkeypatch.setattr(
        gspread,
        "authorize",
        lambda *a, **kw: MagicMock()
    )

    # Optional: hvis du bruker gspread.open i sheets.py
    mock_client = MagicMock()
    monkeypatch.setattr(
        gspread,
        "open",
        lambda *a, **kw: mock_client
    )
