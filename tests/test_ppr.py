import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.ppr import PPR

# --- Dummy data ---
DUMMY_PLAYERS = [
    {"team": "Kristoffer", "ppr": 10.0},
    {"team": "Arild", "ppr": 8.5},
    {"team": "Knut", "ppr": 9.2},
]

DUMMY_HISTORY = [
    ["Kristoffer", "9.5", "2"],
    ["Arild", "8.0", "3"],
    ["Knut", "9.0", "1"],
]

DUMMY_TEAM_NAMES = {
    "Kristoffer": "Kris",
    "Arild": "Aril",
    "Knut": "Knuts",
}

# --- Fixtures ---
@pytest.fixture
def cog():
    # Opprett en PPR-instans med mock bot og mock sheet
    mock_bot = MagicMock()
    ppr_cog = PPR(mock_bot)
    ppr_cog.sheet = MagicMock()
    return ppr_cog

# --- Tester ---
@pytest.mark.asyncio
async def test_get_players_returns_list(monkeypatch, cog):
    # Patch _get_players internt hvis nødvendig
    monkeypatch.setattr(cog, "_get_players", MagicMock(return_value=DUMMY_PLAYERS))
    players = cog._get_players()
    assert isinstance(players, list)
    assert all("team" in p and "ppr" in p for p in players)

@pytest.mark.asyncio
async def test_save_snapshot(monkeypatch, cog):
    # Patch TEAM_NAMES
    monkeypatch.setattr("cogs.ppr.TEAM_NAMES", DUMMY_TEAM_NAMES)

    # Mock worksheet
    ws_mock = MagicMock()
    ws_mock.col_values.return_value = [""]  # tom kolonne
    # Lag et mock for alle celler som oppdateres
    ws_mock.range.return_value = [MagicMock() for _ in range(len(DUMMY_PLAYERS) * 3)]
    cog.sheet.worksheet.return_value = ws_mock

    # Kjør _save_snapshot synkront
    cog._save_snapshot(DUMMY_PLAYERS)

    # Sjekk at update_cells ble kalt
    ws_mock.update_cells.assert_called_once()

@pytest.mark.asyncio
async def test_ppr_command_logic(monkeypatch, cog):
    # Patch _get_players og TEAM_NAMES
    monkeypatch.setattr(cog, "_get_players", MagicMock(return_value=DUMMY_PLAYERS))
    monkeypatch.setattr("cogs.ppr.TEAM_NAMES", DUMMY_TEAM_NAMES)

    # Mock Discord ctx
    ctx = MagicMock()
    ctx.send = AsyncMock()

    # Mock worksheet og get_all_values
    ws_mock = MagicMock()
    ws_mock.get_all_values.return_value = DUMMY_HISTORY
    cog.sheet.worksheet.return_value = ws_mock

    # Kall den interne logikken direkte
    # Her kaller vi ppr funksjonen som et async kall med ctx
    await cog.ppr.callback(cog, ctx)

    # Sjekk at ctx.send ble kalt
    ctx.send.assert_called_once()
    sent_msg = ctx.send.call_args[0][0]
    # Sjekk at melding inneholder rank og team shortnames
    assert "Kris" in sent_msg
    assert "Aril" in sent_msg
    assert "Knuts" in sent_msg
