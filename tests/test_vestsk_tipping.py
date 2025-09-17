import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.vestsk_tipping import VestskTipping
from core.errors import NoEventsFoundError
from datetime import datetime, timedelta
import pytz

@pytest.mark.asyncio
async def test_resultater_no_events(monkeypatch):
    # Mock Google Sheets client slik at credentials ikke trengs
    monkeypatch.setattr("cogs.sheets.get_client", lambda: MagicMock())
    
    # Mock get_sheet til å returnere et dummy sheet
    mock_sheet = MagicMock()
    mock_sheet.row_values.return_value = ["Header", "111", "222"]
    mock_sheet.get_all_values.return_value = [["Kamp"]*3]*10
    monkeypatch.setattr("cogs.sheets.get_sheet", lambda name="Vestsk Tipping": mock_sheet)

    # Mock formateringsfunksjoner
    monkeypatch.setattr("cogs.sheets.green_format", lambda: "green")
    monkeypatch.setattr("cogs.sheets.red_format", lambda: "red")
    monkeypatch.setattr("cogs.sheets.yellow_format", lambda: "yellow")
    monkeypatch.setattr("cogs.sheets.format_cell", lambda *a, **kw: None)

    # Mock requests til å returnere tom events-liste
    class DummyResp:
        def json(self):
            return {"events": []}
    monkeypatch.setattr("cogs.vestsk_tipping.requests.get", lambda *a, **kw: DummyResp())

    # Opprett cog uten å kjøre __init__
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

    # Dummy context
    class DummyCtx:
        def __init__(self):
            self.sent_messages = []
            self.channel = MagicMock()
            self.author = MagicMock()
        async def send(self, msg):
            self.sent_messages.append(msg)

    ctx = DummyCtx()

    # Sjekk at riktig exception kastes
    with pytest.raises(NoEventsFoundError):
        await cog._resultater_impl(ctx)

@pytest.mark.asyncio
async def test_send_sunday_reminder(monkeypatch):
    bot = MagicMock()
    channel_mock = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel_mock)

    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = bot
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_sunday = None

    # Første søndagskamp, 1 time før
    now_sunday = datetime(2025, 9, 14, 12, 0, tzinfo=cog.norsk_tz)  # søndag 12:00
    sunday_game = {
        "date": (now_sunday + timedelta(minutes=60)).isoformat(),  # kickoff 13:00
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "HomeSun"}},
            {"homeAway": "away", "team": {"displayName": "AwaySun"}}
        ]}]
    }

    await cog._send_reminders(now_sunday, [sunday_game], channel_mock)

    # Sjekk at påminnelsen ble sendt
    assert channel_mock.send.call_count == 1
    assert "Early window" in channel_mock.send.call_args[0][0]
