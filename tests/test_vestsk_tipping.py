import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.vestsk_tipping import VestskTipping
from datetime import datetime, timedelta, time
import pytz

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
    cog = VestskTipping.__new__(VestskTipping)  # hopp over __init__
    cog.bot = bot
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

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
    assert any("Fant ingen kamper" in m for m in ctx.sent_messages)

@pytest.mark.asyncio
async def test_send_reminders(monkeypatch):
    bot = MagicMock()
    channel_mock = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel_mock)

    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = bot
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

    # === Torsdag kl. 18:00 ===
    now_thursday = datetime(2025, 9, 11, 18, 5, tzinfo=cog.norsk_tz)  # torsdag 18:05
    await cog._send_reminders(now_thursday, [], channel_mock)
    assert channel_mock.send.call_count == 1
    assert "RAUÅ I GIR" in channel_mock.send.call_args[0][0]

    # === Første søndagskamp, 1 time før ===
    now_sunday = datetime(2025, 9, 14, 12, 0, tzinfo=cog.norsk_tz)  # søndag 12:00
    sunday_game = {
        "date": (now_sunday + timedelta(minutes=60)).isoformat(),  # kickoff 13:00
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "HomeSun"}},
            {"homeAway": "away", "team": {"displayName": "AwaySun"}}
        ]}]
    }

    await cog._send_reminders(now_sunday, [sunday_game], channel_mock)
    assert channel_mock.send.call_count == 2
    assert "Early window" in channel_mock.send.call_args[0][0]