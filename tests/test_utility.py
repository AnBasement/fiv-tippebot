"""Tester for utility.py"""

from unittest.mock import MagicMock
import pytest
from cogs.utility import Utility


@pytest.mark.asyncio
async def test_ping_command():
    """Tester at ping-kommandoen sender Pong! ✅."""
    bot = MagicMock()
    cog = Utility(bot)

    class DummyCtx:
        """Enkel dummy-ctx som fanger opp meldinger sendt."""

        def __init__(self):
            self.sent = None

        async def send(self, msg):
            """Fanger opp meldingen som sendes."""
            self.sent = msg

    ctx = DummyCtx()
    await cog._ping_impl(ctx)  # pylint: disable=protected-access
    assert ctx.sent == "Pong! ✅"
