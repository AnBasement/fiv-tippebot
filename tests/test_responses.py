import pytest
from unittest.mock import AsyncMock, MagicMock
from cogs.responses import Responses

@pytest.mark.asyncio
async def test_all_commands_exist():
    """
    Kjører alle kommandoene i Responses-cog-en og sjekker at ctx.send blir kalt.
    Ingen kommando-spesifikke tester trengs, så nye kommandoer testes automatisk.
    """
    bot = MagicMock()
    cog = Responses(bot)

    # Lag et mock-ctx
    ctx = MagicMock()
    ctx.send = AsyncMock()

    # Iterer gjennom alle kommandoene i cog-en
    for command in cog.get_commands():
        # Kall kommandoens callback med cog og ctx
        await command.callback(cog, ctx)

        # Sjekk at ctx.send ble kalt minst én gang
        ctx.send.assert_called()

        # Reset mock for neste kommando
        ctx.send.reset_mock()
