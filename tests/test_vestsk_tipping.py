"""Tester for vestsk_tipping.py."""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import discord
import pytest
import pytz
import gspread.exceptions
from gspread.exceptions import WorksheetNotFound

from cogs.vestsk_tipping import VestskTipping
from core.errors import ExportError


def make_cog(**attrs):
    """Lager en VestskTipping-instans uten å kjøre __init__ (som starter
    bakgrunnstasks vi ikke ønsker i gang under testing)."""
    cog = VestskTipping.__new__(VestskTipping)
    cog.bot = MagicMock()
    cog.norsk_tz = pytz.timezone("Europe/Oslo")
    cog.last_reminder_week = None
    cog.last_reminder_sunday = None
    cog.last_posted_week = None
    cog.last_processed_week = None
    cog.state_loaded = False
    cog._state_dirty = False
    for key, value in attrs.items():
        setattr(cog, key, value)
    return cog


# === Rene funksjoner uten avhengighet til Sheets/Discord ===


class TestIsValidGameMessage:
    def test_valid_formats(self):
        assert VestskTipping.is_valid_game_message("Patriots @ Giants")
        assert VestskTipping.is_valid_game_message(
            "New England Patriots @ New York Giants"
        )
        assert VestskTipping.is_valid_game_message("Raiders @ 49ers")
        assert VestskTipping.is_valid_game_message(
            "Patriots @ Giants <:_patriots:123456>"
        )

    def test_accepts_result_format(self):
        assert VestskTipping.is_valid_game_message("TeamA - TeamB: 24-17")

    def test_rejects_mentions(self):
        assert not VestskTipping.is_valid_game_message("Patriots @ Giants <@123456>")
        assert not VestskTipping.is_valid_game_message("@everyone Patriots @ Giants")
        assert not VestskTipping.is_valid_game_message("@here Patriots @ Giants")

    def test_rejects_wrong_format(self):
        assert not VestskTipping.is_valid_game_message("Patriots Giants")
        assert not VestskTipping.is_valid_game_message("Patriots vs Giants")
        assert not VestskTipping.is_valid_game_message("")


class TestFormatEvent:
    def test_from_home_away_dict(self):
        cog = make_cog()
        event = {"home": "TeamA", "away": "TeamB", "date": "2025-09-20"}
        assert "TeamB @ TeamA" in cog._format_event(event)

    def test_from_espn_competitions_structure(self):
        cog = make_cog()
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
        assert "Patriots @ Giants" in cog._format_event(ev)


class TestGetPlayers:
    def test_maps_discord_ids_to_columns(self):
        sheet = MagicMock()
        sheet.row_values.return_value = ["", "id1", "id2", ""]
        cog = make_cog()
        assert cog.get_players(sheet) == {"id1": 1, "id2": 2}

    def test_empty_row_gives_empty_mapping(self):
        sheet = MagicMock()
        sheet.row_values.return_value = ["", "", "", ""]
        cog = make_cog()
        assert cog.get_players(sheet) == {}


# === Eksport - riktig mocket via cogs.vestsk_tipping.get_sheet (ikke cogs.sheets.get_sheet) ===


@pytest.mark.asyncio
async def test_export_raises_when_no_bot_messages(monkeypatch):
    """Ingen gyldige bot-meldinger i kanalhistorikken skal gi ExportError."""
    monkeypatch.setattr("cogs.vestsk_tipping.get_sheet", lambda name: MagicMock())

    cog = make_cog()
    ctx = MagicMock()

    async def empty_history(*args, **kwargs):
        return
        yield  # gjør funksjonen til en (tom) async generator

    ctx.channel.history.return_value = empty_history()

    with pytest.raises(ExportError):
        await cog._export_impl(ctx)


@pytest.mark.asyncio
async def test_export_writes_valid_messages_to_sheet(monkeypatch):
    """En gyldig kampmelding skal føre til at update_cells kalles og
    brukeren får bekreftelse."""
    sheet = MagicMock()
    sheet.row_values.return_value = ["", "111", "222"]
    sheet.col_values.return_value = ["Kamp1", "Kamp2"]
    sheet.range.return_value = [MagicMock(), MagicMock(), MagicMock()]
    monkeypatch.setattr("cogs.vestsk_tipping.get_sheet", lambda name: sheet)

    now = datetime.now(pytz.timezone("Europe/Oslo"))
    bot_user = MagicMock()
    valid_msg = MagicMock(
        content="Patriots @ Giants", author=bot_user, created_at=now, reactions=[]
    )

    async def history(*args, **kwargs):
        yield valid_msg

    cog = make_cog()
    cog.bot.user = bot_user
    ctx = MagicMock()
    ctx.channel.history = history
    ctx.send = AsyncMock()

    await cog._export_impl(ctx)

    assert sheet.update_cells.called
    ctx.send.assert_awaited_with("Kampdata eksportert til Sheets.")


# === Reminder scheduler (uendret oppførsel fra før) ===


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

    cog = make_cog(bot=bot)

    sleep_calls = {"n": 0}

    async def fast_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise SystemExit()

    monkeypatch.setattr("cogs.vestsk_tipping.asyncio.sleep", fast_sleep)

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

    cog = make_cog(bot=bot)

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
                                        "team": {"displayName": "New England Patriots"},
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


# === State persistence: _load_state / _save_state / _get_state_sheet ===


class TestLoadState:
    @pytest.mark.asyncio
    async def test_loads_existing_values(self):
        cog = make_cog()
        state_ws = MagicMock()
        state_ws.get.return_value = [["3", "4"]]
        cog._get_state_sheet = AsyncMock(return_value=state_ws)

        await cog._load_state()

        assert cog.last_processed_week == 3
        assert cog.last_posted_week == 4
        assert cog.state_loaded is True

    @pytest.mark.asyncio
    async def test_preserves_zero_as_a_real_value(self):
        """Tallet 0 skal lastes som 0, ikke forveksles med 'ingen verdi'."""
        cog = make_cog()
        state_ws = MagicMock()
        state_ws.get.return_value = [["0", "1"]]
        cog._get_state_sheet = AsyncMock(return_value=state_ws)

        await cog._load_state()

        assert cog.last_processed_week == 0
        assert cog.last_posted_week == 1
        assert cog.state_loaded is True

    @pytest.mark.asyncio
    async def test_first_ever_run_with_no_data_is_not_an_error(self):
        cog = make_cog()
        state_ws = MagicMock()
        state_ws.get.return_value = []
        cog._get_state_sheet = AsyncMock(return_value=state_ws)

        await cog._load_state()

        assert cog.last_processed_week is None
        assert cog.last_posted_week is None
        assert cog.state_loaded is True

    @pytest.mark.asyncio
    async def test_corrupt_data_is_not_loaded_and_admin_notified(self):
        cog = make_cog()
        state_ws = MagicMock()
        state_ws.get.return_value = [["ikke-et-tall", "4"]]
        cog._get_state_sheet = AsyncMock(return_value=state_ws)
        cog._notify_admin = AsyncMock()

        await cog._load_state()

        assert cog.state_loaded is False
        cog._notify_admin.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sheet_error_leaves_state_unloaded_for_retry(self):
        cog = make_cog()
        cog._get_state_sheet = AsyncMock(
            side_effect=gspread.exceptions.GSpreadException("nettverksfeil")
        )
        cog._notify_admin = AsyncMock()

        await cog._load_state()

        assert cog.state_loaded is False
        cog._notify_admin.assert_awaited_once()


class TestSaveState:
    @pytest.mark.asyncio
    async def test_does_nothing_if_state_never_loaded(self):
        cog = make_cog(state_loaded=False)
        cog._get_state_sheet = AsyncMock()

        saved = await cog._save_state()

        assert saved is False
        cog._get_state_sheet.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_writes_values_and_clears_dirty_flag(self):
        state_ws = MagicMock()
        cog = make_cog(
            state_loaded=True,
            last_processed_week=0,
            last_posted_week=7,
            _state_dirty=True,
        )
        cog._get_state_sheet = AsyncMock(return_value=state_ws)

        saved = await cog._save_state()

        assert saved is True
        assert cog._state_dirty is False
        written_values = state_ws.update.call_args.args[1]
        assert written_values == [[0, 7]]  # 0 skal skrives som 0, ikke ""

    @pytest.mark.asyncio
    async def test_failure_sets_dirty_flag_and_notifies_admin(self):
        cog = make_cog(state_loaded=True, last_processed_week=3, last_posted_week=3)
        cog._get_state_sheet = AsyncMock(
            side_effect=gspread.exceptions.GSpreadException("Sheets nede")
        )
        cog._notify_admin = AsyncMock()

        saved = await cog._save_state()

        assert saved is False
        assert cog._state_dirty is True
        cog._notify_admin.assert_awaited_once()


class TestProcessPreviousWeek:
    @pytest.mark.asyncio
    async def test_notifies_admin_when_export_step_fails(self):
        cog = make_cog(last_processed_week=2)
        channel = MagicMock(spec=discord.TextChannel)
        channel.send = AsyncMock()
        cog._export_impl = AsyncMock(side_effect=RuntimeError("Sheets nede"))
        cog._resultater_impl = AsyncMock()
        cog._save_state = AsyncMock(return_value=True)
        cog._notify_admin = AsyncMock()

        result = await cog._process_previous_week(current_week=4, channel=channel)

        assert result is False
        cog._notify_admin.assert_awaited_once()


class TestNotifyAdmin:
    @pytest.mark.asyncio
    async def test_swallows_errors_from_discord_send(self):
        """En feilet varsling skal aldri spre unntaket videre til kalleren -
        dette var CodeRabbit sin første kommentar."""
        cog = make_cog()
        admin_channel = MagicMock()
        admin_channel.send = AsyncMock(side_effect=RuntimeError("Discord nede"))
        cog._admin_channel = lambda: admin_channel

        await cog._notify_admin("test")  # skal ikke kaste

    @pytest.mark.asyncio
    async def test_does_nothing_without_admin_channel_configured(self):
        cog = make_cog()
        cog._admin_channel = lambda: None

        await cog._notify_admin("test")  # skal ikke kaste


class TestFlushPendingState:
    @pytest.mark.asyncio
    async def test_noop_when_nothing_pending(self):
        cog = make_cog(_state_dirty=False)
        cog._save_state = AsyncMock()

        await cog._flush_pending_state()

        cog._save_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_failed_save_and_clears_dirty_only_on_success(self):
        """CodeRabbit sin konkrete scenario: første lagringsforsøk feiler,
        neste scheduler-runde (flush) prøver på nytt, og _state_dirty
        ryddes kun etter at lagringen faktisk lykkes."""
        cog = make_cog(state_loaded=True, last_processed_week=7, last_posted_week=7)

        state_ws = MagicMock()
        state_ws.update.side_effect = [
            gspread.exceptions.GSpreadException("Sheets API nede"),
            None,
        ]
        cog._get_state_sheet = AsyncMock(return_value=state_ws)
        cog._notify_admin = AsyncMock()

        # Første lagringsforsøk (f.eks. fra _process_previous_week) feiler
        first_attempt = await cog._save_state()
        assert first_attempt is False
        assert cog._state_dirty is True

        # Neste runde i scheduleren kaller _flush_pending_state()
        await cog._flush_pending_state()

        assert cog._state_dirty is False
        assert state_ws.update.call_count == 2

    @pytest.mark.asyncio
    async def test_stays_dirty_if_retry_also_fails(self):
        cog = make_cog(state_loaded=True, _state_dirty=True)
        cog._get_state_sheet = AsyncMock(
            side_effect=gspread.exceptions.GSpreadException("fortsatt nede")
        )
        cog._notify_admin = AsyncMock()

        await cog._flush_pending_state()

        assert cog._state_dirty is True


class TestGetStateSheet:
    @pytest.mark.asyncio
    async def test_creates_state_worksheet_when_missing(self, monkeypatch):
        base_sheet = MagicMock()
        spreadsheet = MagicMock()
        new_ws = MagicMock()
        base_sheet.spreadsheet = spreadsheet
        spreadsheet.worksheet.side_effect = WorksheetNotFound("State")
        spreadsheet.add_worksheet.return_value = new_ws
        monkeypatch.setattr("cogs.vestsk_tipping.get_sheet", lambda name: base_sheet)

        cog = make_cog()
        result = await cog._get_state_sheet()

        assert result is new_ws
        new_ws.update.assert_called_once_with(
            "A1:B1", [["last_processed_week", "last_posted_week"]]
        )

    @pytest.mark.asyncio
    async def test_reuses_existing_state_worksheet(self, monkeypatch):
        base_sheet = MagicMock()
        spreadsheet = MagicMock()
        existing_ws = MagicMock()
        base_sheet.spreadsheet = spreadsheet
        spreadsheet.worksheet.return_value = existing_ws
        monkeypatch.setattr("cogs.vestsk_tipping.get_sheet", lambda name: base_sheet)

        cog = make_cog()
        result = await cog._get_state_sheet()

        assert result is existing_ws
        spreadsheet.add_worksheet.assert_not_called()


# === auto_post_scheduler: bekreft at flush faktisk kjøres i løkken, før guards ===


@pytest.mark.asyncio
async def test_scheduler_flushes_pending_state_before_guards(monkeypatch):
    """Bekrefter at en tidligere feilet lagring forsøkes på nytt helt i
    starten av hver løkke-runde, før markør-sjekkene (last_processed_week
    osv.) får avgjøre om noe skal hoppes over."""
    cog = make_cog(
        state_loaded=True,
        last_processed_week=5,
        last_posted_week=5,
        _state_dirty=True,
    )
    cog.bot.wait_until_ready = AsyncMock()
    cog.bot.get_channel.return_value = MagicMock()

    flush_calls = []

    async def fake_flush():
        flush_calls.append(1)
        cog._state_dirty = False

    cog._flush_pending_state = fake_flush

    # Stopp løkken rett etter flush - vi trenger ikke teste resten av
    # runden her, bare at flush faktisk skjer før guard-logikken under.
    from cogs import vestsk_tipping as vt_mod

    class ExplodingDatetime:
        @classmethod
        def now(cls, tz=None):
            raise SystemExit()

    monkeypatch.setattr(vt_mod, "datetime", ExplodingDatetime)

    with pytest.raises(SystemExit):
        await cog.auto_post_scheduler()

    assert flush_calls == [1]
