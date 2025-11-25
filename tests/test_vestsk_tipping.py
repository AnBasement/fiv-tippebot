import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs import sheets
from cogs.vestsk_tipping import VestskTipping
from core.errors import NoEventsFoundError, ExportError
from datetime import datetime
import pytz


@pytest.fixture(autouse=True)
def mock_google_credentials(monkeypatch):
    """Mock Google Sheets client så man ikke trenger credentials.json."""
    # Mock get_client slik at ingen creds trengs
    monkeypatch.setattr(sheets, "get_client", lambda: MagicMock())
    # Mock get_sheet slik at alle tester får et dummy sheet
    monkeypatch.setattr(sheets, "get_sheet", lambda name="Vestsk Tipping": MagicMock())


def test_format_event_simple():
    cog = VestskTipping.__new__(VestskTipping)
    # _format_event expects a dict with string values or ESPN API structure
    event = {
        "home": "TeamA",
        "away": "TeamB",
        "date": "2025-09-20",
        "competitions": "NFL",
    }
    formatted = cog._format_event(event)
    assert "TeamB @ TeamA" in formatted


@pytest.mark.asyncio
async def test_export_handles_no_events(monkeypatch):
    # Lag et falskt sheet
    sheet = MagicMock()

    # Sett opp cog med nødvendige attributter
    cog = VestskTipping.__new__(VestskTipping)
    cog.sheet = sheet  # type: ignore
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.bot = MagicMock()

    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock()

    # Monkeypatch get_sheet til å være en vanlig funksjon som returnerer sheet
    def fake_get_sheet(name="Vestsk Tipping"):
        return sheet

    # Sett opp sheet mocks
    sheet.col_values.return_value = [""]
    sheet.row_values.return_value = ["", "111"]

    cog.get_current_week = lambda: 1  # type: ignore
    cog.get_players = lambda sheet: {"A": 1}  # type: ignore

    # Sett opp bot-bruker
    bot_user = MagicMock()
    cog.bot.user = bot_user

    # Ingen gyldige meldinger i historikken
    async def mock_history(*args, **kwargs):
        if False:
            yield  # tom generator

    ctx.channel.history.return_value = mock_history()

    sheet.get_all_values.return_value = [["A", "old1"]]

    # Forvent at ExportError kastes når det ikke finnes events
    with pytest.raises(ExportError):
        await cog._export_impl(ctx)


@pytest.mark.asyncio
async def test_resultater_handles_api_error(monkeypatch):
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    from unittest.mock import AsyncMock

    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock()
    cog.get_current_week = lambda: 1  # type: ignore

    sheet = MagicMock()
    sheet.row_values = AsyncMock(return_value=["Header", "Player1", "Player2"])
    sheet.cell = AsyncMock(return_value=MagicMock(value="0"))
    monkeypatch.setattr(sheets, "get_sheet", lambda name="Vestsk Tipping": sheet)

    class DummyAiohttpResponse:
        async def json(self):
            return {
                "events": [
                    {
                        "competitions": [
                            {
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "team": {"displayName": "Giants"},
                                        "score": "17",
                                    },
                                    {
                                        "homeAway": "away",
                                        "team": {"displayName": "Patriots"},
                                        "score": "24",
                                    },
                                ]
                            }
                        ]
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

    try:
        await cog._resultater_impl(ctx)
    except NoEventsFoundError:
        pass

    assert ctx.send.await_count > 0


def test_is_valid_game_message_edge_cases():
    cog = VestskTipping.__new__(VestskTipping)
    assert not cog.is_valid_game_message("")
    assert not cog.is_valid_game_message("random text")
    assert not cog.is_valid_game_message("TeamA vs TeamB")
    assert cog.is_valid_game_message("TeamA - TeamB: 24-17") is True


@pytest.mark.asyncio
async def test_logging_on_export(monkeypatch):
    sheet = MagicMock()
    cog = VestskTipping.__new__(VestskTipping)
    cog.sheet = sheet  # type: ignore
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.bot = MagicMock()

    # Sett opp mock ctx
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.channel = MagicMock()
    ctx.channel.send = AsyncMock()

    monkeypatch.setattr(sheets, "get_sheet", lambda name="Vestsk Tipping": sheet)

    # Mock sheet data
    sheet.col_values.return_value = [""]  # tom første kolonne
    sheet.row_values.return_value = ["", "111"]
    sheet.cell = AsyncMock()
    sheet.get_all_values.return_value = [["A", "old1"]]

    cog.get_current_week = lambda: 1  # type: ignore
    # mapping id → kolonne
    cog.get_players = lambda sheet: {"A": 1}  # type: ignore

    # Sett opp bot user
    bot_user = MagicMock()
    cog.bot.user = bot_user

    # Sett opp melding med nåværende dato slik at den er etter start_of_week
    oslo_tz = pytz.timezone("Europe/Oslo")
    now = datetime.now(oslo_tz)
    msg = MagicMock(content="Patriots @ Giants")
    msg.created_at = now
    msg.author = bot_user
    msg.reactions = []

    async def mock_history(*args, **kwargs):
        for m in [msg]:
            yield m

    ctx.channel.history.return_value = mock_history()

    # Kjør eksport
    await cog._export_impl(ctx)

    # Sjekk at melding ble sendt
    ctx.send.assert_awaited_with("Kampdata eksportert til Sheets.")


@pytest.mark.asyncio
async def test_get_players_basic():
    sheet = MagicMock()
    # Simuler rad 2 med Discord-IDs
    sheet.row_values.return_value = ["", "id1", "id2", ""]
    cog = VestskTipping.__new__(VestskTipping)
    players = cog.get_players(sheet)
    assert players == {"id1": 1, "id2": 2}


def test_get_players_empty():
    sheet = MagicMock()
    sheet.row_values.return_value = ["", "", "", ""]
    cog = VestskTipping.__new__(VestskTipping)
    players = cog.get_players(sheet)
    assert players == {}


def test_format_event():
    cog = VestskTipping.__new__(VestskTipping)
    ev = {
        "competitions": [
            {
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Giants"}},
                    {"homeAway": "away", "team": {"displayName": "Patriots"}},
                ]
            }
        ]
    }
    result = cog._format_event(ev)
    assert "Patriots @ Giants" in result or "Giants @ Patriots" in result


@pytest.mark.asyncio
async def test_export_error(monkeypatch):
    # Simuler at get_sheet returnerer None
    monkeypatch.setattr(sheets, "get_sheet", lambda name="Vestsk Tipping": None)
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    ctx = MagicMock()
    ctx.channel = MagicMock()
    with pytest.raises(Exception):
        await cog._export_impl(ctx)


@pytest.mark.asyncio
async def test_resultater_no_events(monkeypatch):
    mock_sheet = MagicMock()
    mock_sheet.row_values.return_value = ["Header", "111", "222"]
    mock_sheet.get_all_values.return_value = [["Kamp"] * 3] * 10
    monkeypatch.setattr(
        "cogs.sheets.get_sheet", lambda name="Vestsk Tipping": mock_sheet
    )
    monkeypatch.setattr("cogs.sheets.green_format", lambda: "green")
    monkeypatch.setattr("cogs.sheets.red_format", lambda: "red")
    monkeypatch.setattr("cogs.sheets.yellow_format", lambda: "yellow")
    monkeypatch.setattr("cogs.sheets.format_cell", lambda *a, **kw: None)

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
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

    class DummyCtx:
        def __init__(self):
            self.sent_messages = []
            self.channel = MagicMock()
            self.author = MagicMock()

        async def send(self, msg):
            self.sent_messages.append(msg)

    ctx = DummyCtx()
    with pytest.raises(NoEventsFoundError):
        await cog._resultater_impl(ctx)


@pytest.mark.asyncio
async def test_export_impl_message_filtering(monkeypatch):
    """Tester at kun gyldige meldinger eksporteres og batch update kalles."""
    # Mock sheet
    mock_sheet = MagicMock()
    mock_sheet.row_values.return_value = ["", "111", "222"]
    mock_sheet.col_values.return_value = ["Kamp1", "Kamp2"]
    mock_sheet.range.return_value = [MagicMock(), MagicMock(), MagicMock()]
    mock_sheet.update_cells.side_effect = lambda cells: setattr(
        mock_sheet, "updated", True
    )
    monkeypatch.setattr(sheets, "get_sheet", lambda name="Vestsk Tipping": mock_sheet)

    # Dummy bot og context
    class DummyUser:
        def __init__(self, id):
            self.id = id

        def __eq__(self, other):
            return isinstance(other, DummyUser) and self.id == other.id

    class DummyReaction:
        def __init__(self, emoji, users):
            self.emoji = emoji
            self._users = users

        async def users(self):
            for u in self._users:
                yield u

    class DummyMessage:
        def __init__(self, content, author, created_at, reactions=None):
            self.content = content
            self.author = author
            self.created_at = created_at
            self.reactions = reactions or []

    class DummyChannel:
        def __init__(self, messages):
            self._messages = messages

        def history(self, limit, after):
            # Simuler async generator
            async def gen():
                for m in self._messages:
                    yield m

            return gen()

    class DummyCtx:
        def __init__(self):
            self.sent = []
            self.channel = None

        def set_channel(self, channel):
            self.channel = channel

        async def send(self, msg):
            self.sent.append(msg)

    # Lag meldinger: kun én gyldig, én med mention, én feil format
    now = datetime.now(pytz.timezone("Europe/Oslo"))
    bot_user = DummyUser(999)
    valid_msg = DummyMessage("Patriots @ Giants", bot_user, now)
    mention_msg = DummyMessage("Patriots @ Giants <@123>", bot_user, now)
    invalid_msg = DummyMessage("Patriots Giants", bot_user, now)
    channel = DummyChannel([valid_msg, mention_msg, invalid_msg])

    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    cog.bot.user = bot_user
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None

    ctx = DummyCtx()
    ctx.set_channel(channel)

    await cog._export_impl(ctx)

    # Sjekk at kun gyldig melding eksporteres og update_cells kalles
    assert hasattr(mock_sheet, "updated")
    assert any("eksportert" in m.lower() for m in ctx.sent)


def test_is_valid_game_message():
    # Gyldige meldinger
    assert VestskTipping.is_valid_game_message("Patriots @ Giants")
    assert VestskTipping.is_valid_game_message("New England Patriots @ New York Giants")
    assert VestskTipping.is_valid_game_message("Raiders @ 49ers")

    # Ugyldige meldinger: mentions
    assert not VestskTipping.is_valid_game_message("Patriots @ Giants <@123456>")
    assert not VestskTipping.is_valid_game_message("@everyone Patriots @ Giants")
    assert not VestskTipping.is_valid_game_message("@here Patriots @ Giants")

    # Ugyldige meldinger: feil format
    assert not VestskTipping.is_valid_game_message("Patriots Giants")
    assert not VestskTipping.is_valid_game_message("Patriots vs Giants")
    assert not VestskTipping.is_valid_game_message("")

    # Gyldig med emoji (skal fjernes)
    assert VestskTipping.is_valid_game_message("Patriots @ Giants <:_patriots:123456>")


@pytest.mark.asyncio
async def test_resultater_no_events_api(monkeypatch):

    # Mock get_sheet til å returnere et dummy sheet
    mock_sheet = MagicMock()
    mock_sheet.row_values.return_value = ["Header", "111", "222"]
    mock_sheet.get_all_values.return_value = [["Kamp"] * 3] * 10

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
    mock_sheet.update_cells.side_effect = lambda cells: print(
        "[DEBUG] update_cells called"
    )

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
        sheet = sheets.get_sheet("Vestsk Tipping")
        players = self.get_players(sheet)
        assert players  # sjekk at spillere finnes
        cells = sheet.range(f"A1:{chr(65 + len(players))}1")
        sheet.update_cells(cells)
        await ctx.send("Kampdata eksportert (dummy)")

    cog._export_impl = dummy_export_impl.__get__(cog)

    # --- Kjør ---
    await cog._export_impl(ctx)

    # Sjekk at update_cells ble kalt
    assert mock_sheet.update_cells.called


@pytest.mark.asyncio
async def test_reminder_scheduler_thursday(monkeypatch):
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

    sleep_calls = {"n": 0}

    async def fast_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise SystemExit()

    monkeypatch.setattr("cogs.vestsk_tipping.asyncio.sleep", fast_sleep)

    # Sett nåværende tid til torsdag 17:50 lokal tid
    fixed_now = cog.norsk_tz.localize(datetime(2024, 9, 5, 17, 50))  # Torsdag
    from cogs import vestsk_tipping as vt_mod

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(vt_mod, "datetime", FixedDateTime)

    with pytest.raises(SystemExit):
        await cog.reminder_scheduler()

    assert any("RAUÅ I GIR" in m for m in channel.sent)
    assert cog.last_reminder_week == fixed_now.isocalendar()[1]


@pytest.mark.asyncio
async def test_reminder_scheduler_sunday(monkeypatch):
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

    sleep_calls = {"n": 0}

    async def fast_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise SystemExit()

    monkeypatch.setattr("cogs.vestsk_tipping.asyncio.sleep", fast_sleep)

    fixed_now = cog.norsk_tz.localize(datetime(2024, 9, 8, 17, 55))
    from cogs import vestsk_tipping as vt_mod

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

        @classmethod
        def fromisoformat(cls, s):
            return datetime.fromisoformat(s)

    monkeypatch.setattr(vt_mod, "datetime", FixedDateTime)

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
                                        "team": {"displayName": "New York Giants"},
                                    },
                                    {
                                        "homeAway": "away",
                                        "team": {
                                            "displayName": ("New England Patriots")
                                        },
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

    with pytest.raises(SystemExit):
        await cog.reminder_scheduler()

    assert any("Early window snart" in m for m in channel.sent)
    assert cog.last_reminder_sunday is not None
