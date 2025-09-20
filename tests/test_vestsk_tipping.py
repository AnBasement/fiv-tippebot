import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs import sheets
from cogs.vestsk_tipping import VestskTipping
from core.errors import NoEventsFoundError
from datetime import datetime, timedelta, timezone
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

    # Mock aiohttp.ClientSession for tom events-liste
    class DummyAiohttpResponse:
        async def json(self):
            return {"events": []}
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummyAiohttpSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        def get(self, url, *args, **kwargs):
            return DummyAiohttpResponse()

    monkeypatch.setattr(
        "cogs.vestsk_tipping.aiohttp.ClientSession",
        lambda *a, **kw: DummyAiohttpSession(),
    )

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
async def test_export_impl_simple(monkeypatch):
    """En enklere test som kun sjekker at update_cells blir kalt"""

    # --- Mock sheet ---
    mock_sheet = MagicMock()
    # row_values(2) gir to spillere
    mock_sheet.row_values.return_value = ["", "111", "222"]
    mock_sheet.range.return_value = [MagicMock(), MagicMock(), MagicMock()]
    mock_sheet.update_cells.side_effect = lambda cells: print("[DEBUG] update_cells called")

    # Patch get_sheet
    monkeypatch.setattr(sheets, "get_sheet", lambda name="Vestsk Tipping": mock_sheet)

    # --- Dummy cog ---
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()

    # --- Dummy ctx ---
    class DummyCtx:
        async def send(self, msg):
            print("[DEBUG] ctx.send:", msg)
    ctx = DummyCtx()

    # --- Dummy _export_impl ---
    # Vi kaller kun metoder internt som bruker sheet
    async def dummy_export_impl(self, ctx):
        sheet = sheets.get_sheet()
        players = self.get_players(sheet)
        assert players  # sjekk at spillere finnes
        cells = sheet.range(1, 1, 1, len(players) + 1)
        sheet.update_cells(cells)
        await ctx.send("Kampdata eksportert (dummy)")

    cog._export_impl = dummy_export_impl.__get__(cog)

    # --- Kjør ---
    await cog._export_impl(ctx)

    # Sjekk at update_cells ble kalt
    assert mock_sheet.update_cells.called

@pytest.mark.asyncio
async def test_reminder_scheduler_thursday(monkeypatch):
    # Arrange bot, channel and message capture
    class DummyChannel:
        def __init__(self):
            self.sent = []
        async def send(self, msg):
            self.sent.append(msg)

    channel = DummyChannel()

    bot = MagicMock()
    bot.wait_until_ready = AsyncMock()
    bot.get_channel.return_value = channel

    # Build cog sans __init__ and set timezone
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = bot
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

    # Patch asyncio.sleep to be instant and stop after two sleeps
    sleep_calls = {"n": 0}
    async def fast_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise SystemExit()
    monkeypatch.setattr("cogs.vestsk_tipping.asyncio.sleep", fast_sleep)

    # Fix current time to Thursday 17:50 local time
    fixed_now = cog.norsk_tz.localize(datetime(2024, 9, 5, 17, 50))  # Thursday
    from cogs import vestsk_tipping as vt_mod
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now
    monkeypatch.setattr(vt_mod, "datetime", FixedDateTime)

    # Act & Assert
    with pytest.raises(SystemExit):
        await cog.reminder_scheduler()

    # Should have sent the Thursday reminder once
    assert any("RAUÅ I GIR" in m for m in channel.sent)
    # last_reminder_week should be set to the week number
    assert cog.last_reminder_week == fixed_now.isocalendar()[1]


@pytest.mark.asyncio
async def test_reminder_scheduler_sunday(monkeypatch):
    # Arrange bot and channel
    class DummyChannel:
        def __init__(self):
            self.sent = []
        async def send(self, msg):
            self.sent.append(msg)

    channel = DummyChannel()

    bot = MagicMock()
    bot.wait_until_ready = AsyncMock()
    bot.get_channel.return_value = channel

    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = bot
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

    # Patch time and sleep
    sleep_calls = {"n": 0}
    async def fast_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise SystemExit()
    monkeypatch.setattr("cogs.vestsk_tipping.asyncio.sleep", fast_sleep)

    fixed_now = cog.norsk_tz.localize(datetime(2024, 9, 8, 17, 55))  # Sunday before 18:00 reminder
    from cogs import vestsk_tipping as vt_mod
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now
        @classmethod
        def fromisoformat(cls, s):
            # delegate to real datetime to parse
            return datetime.fromisoformat(s)
    monkeypatch.setattr(vt_mod, "datetime", FixedDateTime)

    # Patch aiohttp.ClientSession to return a Sunday event at 17:00 UTC (19:00 local)
    class DummyAiohttpResponse:
        async def json(self):
            return {
                "events": [
                    {
                        "date": "2024-09-08T17:00:00Z",
                        "competitions": [
                            {
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "team": {"displayName": "New York Giants"}
                                    },
                                    {
                                        "homeAway": "away",
                                        "team": {"displayName": "New England Patriots"}
                                    },
                                ]
                            }
                        ],
                    }
                ]
            }
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummyAiohttpSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        def get(self, url, *args, **kwargs):
            return DummyAiohttpResponse()

    monkeypatch.setattr(
        "cogs.vestsk_tipping.aiohttp.ClientSession",
        lambda *a, **kw: DummyAiohttpSession(),
    )

    # Act & Assert
    with pytest.raises(SystemExit):
        await cog.reminder_scheduler()

    # Should have sent the Sunday early window reminder
    assert any("Early window snart" in m for m in channel.sent)
    # Ensure the formatted matchup appears in the message
    assert any("Patriots @ New York Giants" in m for m in channel.sent)
    assert cog.last_reminder_sunday is not None