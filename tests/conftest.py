"""Globale test-fixtures for å mocke gspread/OAuth uten credentials."""

from unittest.mock import MagicMock
import pytest
import oauth2client.service_account as sac
import gspread


@pytest.fixture(autouse=True)
def mock_gspread(monkeypatch):
    """
    Mock Google Sheets-tilgang slik at tests kan kjøre uten credentials.json
    """

    monkeypatch.setattr(
        sac.ServiceAccountCredentials,
        "from_json_keyfile_name",
        lambda *a, **kw: MagicMock(),
    )

    mock_client = MagicMock()
    mock_sheet = MagicMock()
    mock_client.open = lambda *a, **kw: mock_sheet
    monkeypatch.setattr(gspread, "authorize", lambda *a, **kw: mock_client)

    # Mock sheet-funksjoner hvis de brukes direkte
    mock_sheet.sheet1 = MagicMock()
    mock_sheet.row_values.return_value = ["ID1", "ID2", "ID3"]
    mock_sheet.get_all_values.return_value = [["Kamp1", "", ""], ["Kamp2", "", ""]]
    mock_sheet.cell.return_value.value = "Test"
    mock_sheet.update_cell.return_value = None
    mock_sheet.range.return_value = []
    mock_sheet.update_cells.return_value = None
