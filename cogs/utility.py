from discord.ext import commands

class Utility(commands.Cog):
    """Små hjelpekommandoer"""

    def __init__(self, bot):
        self.bot = bot

    # Intern metode for testing
    async def _ping_impl(self, ctx):
        await ctx.send("Pong! ✅")

    @commands.command()
    async def ping(self, ctx):
        await self._ping_impl(ctx)

async def setup(bot):
    await bot.add_cog(Utility(bot))
