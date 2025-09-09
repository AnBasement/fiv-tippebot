import pytest
from cogs import sheets

def test_get_players_mapping():
    class DummySheet:
        def row_values(self, n):
            return ["Header", "123", "456"]
    sheet = DummySheet()
    players = sheets.get_players(sheet)
    assert players == {"Header":0, "123":1, "456":2}

def test_color_formats():
    assert sheets.green_format() is not None
    assert sheets.red_format() is not None
    assert sheets.yellow_format() is not None
