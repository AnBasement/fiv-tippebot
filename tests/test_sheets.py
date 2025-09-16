import pytest
from unittest.mock import patch, MagicMock
from cogs import sheets

# Dummy Sheet for testing
class DummySheet:
    def __init__(self):
        self.formatted_cells = []

    def row_values(self, n):
        return ["Header", "123", "456"]

    def format_cell_range(self, cell_range, cell_format):
        self.formatted_cells.append((cell_range, cell_format))


def test_get_creds_none(monkeypatch):
    # Simuler at credentials.json ikke finnes
    monkeypatch.setattr("os.path.exists", lambda x: False)
    creds = sheets.get_creds()
    assert creds is None


def test_get_creds_returns_creds(monkeypatch):
    class DummyCreds:
        pass

    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr(
        "cogs.sheets.ServiceAccountCredentials.from_json_keyfile_name",
        lambda file, scope: DummyCreds(),
    )
    creds = sheets.get_creds()
    assert isinstance(creds, DummyCreds)


def test_get_client_none(monkeypatch):
    monkeypatch.setattr(sheets, "get_creds", lambda: None)
    client = sheets.get_client()
    assert client is None


def test_get_client_returns_client(monkeypatch):
    dummy_client = "client_instance"
    monkeypatch.setattr(sheets, "get_creds", lambda: "creds")
    monkeypatch.setattr(sheets.gspread, "authorize", lambda creds: dummy_client)
    client = sheets.get_client()
    assert client == dummy_client


def test_get_sheet(monkeypatch):
    dummy_sheet = MagicMock()
    dummy_client = MagicMock()
    dummy_client.open.return_value.get_worksheet.return_value = dummy_sheet

    monkeypatch.setattr(sheets, "get_client", lambda: dummy_client)
    sheet = sheets.get_sheet("MySheet")
    dummy_client.open.assert_called_once_with("MySheet")
    dummy_client.open.return_value.get_worksheet.assert_called_once_with(0)
    assert sheet == dummy_sheet


def test_format_cell_calls_format_cell_range():
    dummy_sheet = MagicMock()
    color_fmt = sheets.green_format()

    with patch("cogs.sheets.format_cell_range") as mock_format:
        sheets.format_cell(dummy_sheet, 2, 3, color_fmt)
        # Sjekk at format_cell_range ble kalt med riktig celle og format
        mock_format.assert_called_once_with(dummy_sheet, "C2", color_fmt)


def test_color_formats():
    assert sheets.green_format() is not None
    assert sheets.red_format() is not None
    assert sheets.yellow_format() is not None


def test_dummy_sheet_row_values():
    sheet = DummySheet()
    values = sheet.row_values(1)
    assert values == ["Header", "123", "456"]
