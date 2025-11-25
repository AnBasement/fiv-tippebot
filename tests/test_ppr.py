import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
@patch("cogs.ppr.get_client")
def cog(mock_get_client):
    mock_bot = MagicMock()
    mock_sheet = MagicMock()
    # Sett mock_get_client til å returnere dummy client med open()->mock_sheet
    dummy_client = MagicMock()
    dummy_client.open.return_value = mock_sheet
    mock_get_client.return_value = dummy_client

    # Opprett PPR etter patchen er aktiv
    ppr_cog = PPR(mock_bot)
    return ppr_cog


# --- Tester ---
@pytest.mark.asyncio
async def test_get_players_returns_list(monkeypatch, cog):
    monkeypatch.setattr(cog, "_get_players", AsyncMock(return_value=DUMMY_PLAYERS))
    players = await cog._get_players()
    assert isinstance(players, list)
    assert all("team" in p and "ppr" in p for p in players)


@pytest.mark.asyncio
async def test_save_snapshot(monkeypatch, cog):
    monkeypatch.setattr("cogs.ppr.TEAM_NAMES", DUMMY_TEAM_NAMES)
    ws_mock = MagicMock()
    ws_mock.col_values.return_value = [""]  # tom kolonne
    ws_mock.range.return_value = [MagicMock() for _ in range(len(DUMMY_PLAYERS) * 3)]
    cog.sheet.worksheet.return_value = ws_mock

    await cog._save_snapshot(DUMMY_PLAYERS)
    ws_mock.update_cells.assert_called_once()


@pytest.mark.asyncio
async def test_ppr_command_logic(monkeypatch, cog):
    monkeypatch.setattr(cog, "_get_players", AsyncMock(return_value=DUMMY_PLAYERS))
    monkeypatch.setattr("cogs.ppr.TEAM_NAMES", DUMMY_TEAM_NAMES)
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ws_mock = MagicMock()
    ws_mock.get_all_values.return_value = DUMMY_HISTORY
    cog.sheet.worksheet.return_value = ws_mock

    await cog.ppr.callback(cog, ctx)

    ctx.send.assert_called_once()
    sent_msg = ctx.send.call_args[0][0]
    assert "Kris" in sent_msg
    assert "Aril" in sent_msg
    assert "Knuts" in sent_msg
