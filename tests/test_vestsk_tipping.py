import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.vestsk_tipping import VestskTipping
from core.errors import NoEventsFoundError
import pytz
from data.teams import teams
from discord.ext.commands import CheckFailure

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
async def test_get_players_mapping_skips_empty_and_offsets_index(monkeypatch):
    # Opprett cog uten __init__
    cog = VestskTipping.__new__(VestskTipping)
    # Sheet med ID-er i rad 2, inkludert tomt felt som skal ignoreres
    sheet = MagicMock()
    sheet.row_values.return_value = ["Header", "111", "", "222"]

    players = cog.get_players(sheet)
    assert players == {"111": 2, "222": 4}

@pytest.mark.asyncio
async def test_on_command_error_sends_message():
    cog = VestskTipping.__new__(VestskTipping)
    ctx = MagicMock()
    ctx.send = AsyncMock()

    await VestskTipping.on_command_error(cog, ctx, CheckFailure())
    ctx.send.assert_awaited_once()
    assert "Kanskje hvis du spør veldig pent" in ctx.send.await_args.args[0]

@pytest.mark.asyncio
async def test_kamper_no_events_raises(monkeypatch):
    # Mock requests.get for å returnere tom events-liste
    class DummyResp:
        def json(self):
            return {"events": []}
    monkeypatch.setattr("cogs.vestsk_tipping.requests.get", lambda *a, **kw: DummyResp())

    cog = VestskTipping.__new__(VestskTipping)

    class DummyCtx:
        async def send(self, msg):
            pass
    ctx = DummyCtx()

    with pytest.raises(NoEventsFoundError):
        await cog._kamper_impl(ctx)

@pytest.mark.asyncio
async def test_kamper_sends_formatted_messages(monkeypatch):
    # Lag to dummy events, sortert på dato
    def make_event(date_iso, home_name, away_name):
        return {
            "date": date_iso,
            "competitions": [
                {
                    "competitors": [
                        {"homeAway": "home", "team": {"displayName": home_name}},
                        {"homeAway": "away", "team": {"displayName": away_name}},
                    ]
                }
            ],
        }

    events = [
        make_event("2024-09-08T17:00:00Z", "New England Patriots", "Buffalo Bills"),
        make_event("2024-09-09T01:20:00Z", "Miami Dolphins", "New York Jets"),
    ]

    class DummyResp:
        def json(self):
            return {"events": events}

    monkeypatch.setattr("cogs.vestsk_tipping.requests.get", lambda *a, **kw: DummyResp())

    # Dummy ctx som samler meldinger
    class DummyCtx:
        def __init__(self):
            self.sent_messages = []
        async def send(self, msg):
            self.sent_messages.append(msg)

    ctx = DummyCtx()
    cog = VestskTipping.__new__(VestskTipping)

    await cog._kamper_impl(ctx)

    assert len(ctx.sent_messages) == 2
    # Sjekk format på første melding
    expected1 = (
        f"{teams['Buffalo Bills']['emoji']} Buffalo Bills @ "
        f"New England Patriots {teams['New England Patriots']['emoji']}"
    )
    assert ctx.sent_messages[0] == expected1

@pytest.mark.asyncio
async def test_resultater_builds_url_with_week_and_sends_messages(monkeypatch):
    # Gjør sleep no-op
    monkeypatch.setattr("asyncio.sleep", lambda *a, **kw: AsyncMock())

    # Mock Sheets-tilgang og formatering til no-op
    mock_sheet = MagicMock()
    mock_sheet.title = "Vestsk Tipping"
    mock_sheet.row_values.side_effect = lambda n: ["Header", "Navn1", "Navn2"] if n == 1 else ["Header"]  # noqa: E501
    mock_sheet.get_all_values.return_value = [[], []]
    mock_sheet.cell.return_value.value = ""
    mock_sheet.update_cell.return_value = None

    monkeypatch.setattr("cogs.sheets.get_sheet", lambda name="Vestsk Tipping": mock_sheet)
    monkeypatch.setattr("cogs.sheets.green_format", lambda: "green")
    monkeypatch.setattr("cogs.sheets.red_format", lambda: "red")
    monkeypatch.setattr("cogs.sheets.yellow_format", lambda: "yellow")
    monkeypatch.setattr("cogs.sheets.format_cell", lambda *a, **kw: None)

    # Fang URL som brukes av requests.get
    captured = {"url": None}

    class DummyResp:
        def json(self):
            return {
                "events": [
                    {
                        "id": "1",
                        "date": "2024-09-08T17:00:00Z",
                        "competitions": [
                            {
                                "competitors": [
                                    {"homeAway": "home", "team": {"displayName": "New England Patriots"}, "score": "10"},  # noqa: E501
                                    {"homeAway": "away", "team": {"displayName": "Buffalo Bills"}, "score": "10"},  # noqa: E501
                                ]
                            }
                        ],
                    }
                ]
            }

    def fake_get(url, *a, **kw):
        captured["url"] = url
        return DummyResp()

    monkeypatch.setattr("cogs.vestsk_tipping.requests.get", fake_get)

    # Dummy ctx som samler meldinger
    class DummyCtx:
        def __init__(self):
            self.sent_messages = []
            self.channel = MagicMock()
            self.author = MagicMock()
        async def send(self, msg):
            self.sent_messages.append(msg)

    ctx = DummyCtx()

    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    cog.bot.user = MagicMock()
    cog.norsk_tz = pytz.timezone("Europe/Oslo")

    await cog._resultater_impl(ctx, uke=5)

    # Verifiser at uke-param ble brukt i URL
    assert "seasontype=2" in captured["url"]
    assert "week=5" in captured["url"]
    assert "dates=" in captured["url"]

    # Forvent to Discord-meldinger: poengliste og bekreftelse
    assert len(ctx.sent_messages) >= 2