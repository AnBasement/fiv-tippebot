# Tullekommandoer, for det meste

from discord.ext import commands
from core.errors import ResponseError

class Responses(commands.Cog):
    """Cog for kommandoer hvor botten svarer med enkel melding."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kaimi")
    async def kaimi(self, ctx):
        """Når kaimi scorer."""
        try:
            await ctx.send(
                "<:hou:752546616526897243> LET'S GO "
                "JOHN CHRISTIAN KA'IMINOEAULOAMEKA'IKEOKEKUMUPA'A "
                "\"KA'IMI\" FAIRBAIRN! <:hou:752546616526897243>"
            )

        except Exception as e:
            raise ResponseError("kaimi", str(e))

    @commands.command(name="doc")
    async def doc(self, ctx):
        """Lenker til FiV-dokumentet."""
        try:
            await ctx.send("https://docs.google.com/spreadsheets/d/1PBCDP_9ucjJ00RIdROJ-sXNJsQEhJoIlDMSZ3DGBvx4/edit?usp=sharing")
        except Exception as e:
            raise ResponseError("doc", str(e))

    @commands.command(name="doink")
    async def doink(self, ctx):
        """Når kickere bommer."""
        try:
            await ctx.send("<:lamarbruh:764434396240805898> DOINK <:lamarbruh:764434396240805898> ")
        except Exception as e:
            raise ResponseError("doink", str(e))

    @commands.command(name="incel")
    async def incel(self, ctx):
        """Fordi Butker e ein incel."""
        try:
            await ctx.send("Harrison Bitchker er gerontofil")
        except Exception as e:
            raise ResponseError("incel", str(e))

# --- Setup ---
async def setup(bot):
    await bot.add_cog(Responses(bot))
