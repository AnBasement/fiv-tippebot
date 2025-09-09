import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.vestsk_tipping import VestskTipping

@pytest.mark.asyncio
async def test_resultater_mocked(monkeypatch):
    # Mock Google Sheets
    mock_sheet = MagicMock()
    mock_sheet.row_values.return_value = ["Header", "111", "222"]
    mock_sheet.get_all_values.return_value = [["Kamp"]*3]*10
    monkeypatch.setattr("cogs.sheets.get_sheet", lambda: mock_sheet)
    monkeypatch.setattr("cogs.sheets.green_format", lambda: "green")
    monkeypatch.setattr("cogs.sheets.red_format", lambda: "red")
    monkeypatch.setattr("cogs.sheets.yellow_format", lambda: "yellow")
    monkeypatch.setattr("cogs.sheets.format_cell", lambda *a, **kw: None)

    # Mock requests
    class DummyResp:
        def json(self):
            return {"events": []}
    monkeypatch.setattr("cogs.vestsk_tipping.requests.get", lambda *a, **kw: DummyResp())

    bot = MagicMock()
    cog = VestskTipping(bot)

    class DummyChannel:
        def __init__(self):
            self.history = AsyncMock(return_value=[])

    class DummyCtx:
        def __init__(self):
            self.sent_messages = []
            self.channel = DummyChannel()
            self.author = MagicMock()
        async def send(self, msg):
            self.sent_messages.append(msg)

    ctx = DummyCtx()
    await cog._resultater_impl(ctx)
    # Sjekk at meldingen om ingen kamper sendes
    assert any("Fant ingen kamper" in m for m in ctx.sent_messages)
