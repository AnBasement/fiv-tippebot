"""Tester for sheets.py"""

from unittest.mock import patch, MagicMock
import pytest
from cogs import sheets
from core.errors import MissingCredentialsError


class DummySheet:
    """Dummy-ark for å teste grunnleggende funksjoner."""

    def __init__(self):
        self.formatted_cells = []

    def row_values(self, n):  # pylint: disable=unused-argument
        """Returnerer en dummy-rad med tre verdier."""
        return ["Header", "123", "456"]

    def format_cell_range(self, cell_range, cell_format):
        """Lagrer formateringen som ble bedt om."""
        self.formatted_cells.append((cell_range, cell_format))


def test_get_creds_none(monkeypatch):
    """Simulerer manglende credentials.json og forventer MissingCredentialsError."""
    monkeypatch.setattr("os.path.exists", lambda x: False)
    with pytest.raises(MissingCredentialsError) as exc_info:
        sheets.get_creds()

    assert "Fant ikke Google API credentials-filen" in str(exc_info.value)


def test_get_creds_returns_creds(monkeypatch):
    """Sjekker at get_creds() returnerer creds når filen finnes."""

    class DummyCreds:
        """Dummy credentials-objekt for testing."""

    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr(
        "cogs.sheets.ServiceAccountCredentials.from_json_keyfile_name",
        lambda file, scope: DummyCreds(),
    )
    creds = sheets.get_creds()
    assert isinstance(creds, DummyCreds)


def test_get_client_none(monkeypatch):
    """Sjekker at get_client() kan returnere None uten creds."""
    monkeypatch.setattr(sheets, "get_creds", lambda: None)
    monkeypatch.setattr("gspread.authorize", lambda creds: None)

    client = sheets.get_client()
    assert client is None


def test_get_client_returns_client(monkeypatch):
    """Sjekker at get_client() returnerer autorisert klient."""
    dummy_client = "client_instance"
    monkeypatch.setattr(sheets, "get_creds", lambda: "creds")
    monkeypatch.setattr(sheets.gspread, "authorize", lambda creds: dummy_client)
    client = sheets.get_client()
    assert client == dummy_client


def test_get_sheet(monkeypatch):
    """Sjekker at get_sheet() åpner riktig dokument/worksheet."""
    dummy_sheet = MagicMock()
    dummy_client = MagicMock()
    dummy_client.open.return_value.get_worksheet.return_value = dummy_sheet

    monkeypatch.setattr(sheets, "get_client", lambda: dummy_client)
    sheet = sheets.get_sheet("MySheet")
    dummy_client.open.assert_called_once_with("MySheet")
    dummy_client.open.return_value.get_worksheet.assert_called_once_with(0)
    assert sheet == dummy_sheet


def test_format_cell_calls_format_cell_range():
    """Sjekker at format_cell() kaller format_cell_range med riktig celle."""
    dummy_sheet = MagicMock()
    color_fmt = sheets.green_format()

    with patch("cogs.sheets.format_cell_range") as mock_format:
        sheets.format_cell(dummy_sheet, 2, 3, color_fmt)
        # Sjekk at format_cell_range ble kalt med riktig celle og format
        mock_format.assert_called_once_with(dummy_sheet, "C2", color_fmt)


def test_color_formats():
    """Sjekker at farge-funksjonene returnerer gyldige dicts."""
    assert sheets.green_format() is not None
    assert sheets.red_format() is not None
    assert sheets.yellow_format() is not None


def test_dummy_sheet_row_values():
    """Sjekker at DummySheet.row_values() returnerer dummy-data."""
    sheet = DummySheet()
    values = sheet.row_values(1)
    assert values == ["Header", "123", "456"]
