from discord.ext import commands

class Utility(commands.Cog):
    """Små hjelpekommandoer"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Tester om botten svarer"""
        await ctx.send("Pong! ✅")

def setup(bot):
    bot.add_cog(Utility(bot))
