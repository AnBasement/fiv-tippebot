import pytest
from cogs.utility import Utility
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_ping_command():
    bot = MagicMock()
    cog = Utility(bot)

    class DummyCtx:
        def __init__(self):
            self.sent = None

        async def send(self, msg):
            self.sent = msg

    ctx = DummyCtx()
    await cog._ping_impl(ctx)  # type: ignore[arg-type]
    assert ctx.sent == "Pong! ✅"
