"""Globale test-fixtures for å mocke gspread/OAuth uten credentials."""

from unittest.mock import MagicMock
import pytest
import google.oauth2.service_account as google_auth
import gspread


@pytest.fixture(autouse=True)
def mock_gspread(monkeypatch):
    """
    Mock Google Sheets-tilgang slik at tester kan kjøre uten credentials.json.

    Den ekte get_sheet() gjør: gspread.authorize(creds) -> client.open(navn)
    -> spreadsheet.get_worksheet(indeks). Mocken speiler nøyaktig denne
    kjeden - ellers ender testene opp med å konfigurere et mock-objekt som
    aldri faktisk er det koden bruker.
    """
    monkeypatch.setattr(
        google_auth.Credentials,
        "from_service_account_file",
        lambda *a, **kw: MagicMock(),
    )

    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_sheet = MagicMock()

    # client.open(navn) -> spreadsheet
    mock_client.open = lambda *a, **kw: mock_spreadsheet
    # spreadsheet.get_worksheet(indeks) -> arbeidsarket get_sheet() faktisk returnerer
    mock_spreadsheet.get_worksheet.return_value = mock_sheet
    # spreadsheet.worksheet("State") / .add_worksheet(...) -> brukt av _get_state_sheet()
    mock_spreadsheet.worksheet.return_value = mock_sheet
    mock_spreadsheet.add_worksheet.return_value = mock_sheet
    # arbeidsark.spreadsheet -> tilbake til spreadsheet, brukt av _get_state_sheet()
    mock_sheet.spreadsheet = mock_spreadsheet

    monkeypatch.setattr(gspread, "authorize", lambda *a, **kw: mock_client)

    # Fornuftige standardverdier - overstyr på selve mock_sheet i den enkelte
    # testen ved behov (fixture returnerer mock_sheet).
    mock_sheet.row_values.return_value = ["ID1", "ID2", "ID3"]
    mock_sheet.get_all_values.return_value = [["Kamp1", "", ""], ["Kamp2", "", ""]]
    mock_sheet.cell.return_value.value = "Test"
    mock_sheet.update_cell.return_value = None
    mock_sheet.range.return_value = []
    mock_sheet.update_cells.return_value = None

    return mock_sheet
