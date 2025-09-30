# Håndterer humoristiske meldinger og svar fra botten

from discord.ext import commands
from discord.ext.commands import Bot, Context, Cog
from core.errors import ResponseError


class Responses(Cog):
    """Cog for kommandoer hvor botten svarer med forhåndsdefinerte meldinger.

    Denne cog-en inneholder enkle kommandoer som returnerer faste
    meldinger. Kommandoene er for det meste knyttet til inside-jokes.

    Attributes:
        bot (Bot): Discord bot-instansen
    """

    def __init__(self, bot: Bot) -> None:
        """Initialiserer Responses cog.

        Args:
            bot (Bot): Discord bot-instansen
        """
        self.bot: Bot = bot

    @commands.command(name="kaimi")
    async def kaimi(self, ctx: Context) -> None:
        """Poster det fulle navnet til Ka'imi Fairbairn.
        Vanligvis brukt når Ka'imi scorer.

        Args:
            ctx (Context): Discord context-objektet

        Raises:
            ResponseError: Hvis sending av meldingen feiler
        """
        try:
            await ctx.send(
                "<:hou:752546616526897243> LET'S GO "
                "JOHN CHRISTIAN KA'IMINOEAULOAMEKA'IKEOKEKUMUPA'A "
                "\"KA'IMI\" FAIRBAIRN! <:hou:752546616526897243>"
            )
        except Exception as e:
            raise ResponseError(
                "kaimi",
                f"Kunne ikke sende Ka'imi-melding: {str(e)}"
            )

    @commands.command(name="doc")
    async def doc(self, ctx: Context) -> None:
        """Deler lenken til Fest i Vest-dokumentet.

        Args:
            ctx (Context): Discord context-objektet

        Raises:
            ResponseError: Hvis sending av lenken feiler
        """
        try:
            await ctx.send(
                "https://docs.google.com/spreadsheets/d/"
                "1PBCDP_9ucjJ00RIdROJ-sXNJsQEhJoIlDMSZ3DGBvx4/edit?usp=sharing"
            )
        except Exception as e:
            raise ResponseError(
                "doc",
                f"Kunne ikke sende dokumentlenke: {str(e)}"
            )

    @commands.command(name="doink")
    async def doink(self, ctx):
        """Brukes når en kicker bommer/treffer målstengene.

        Args:
            ctx (commands.Context): Discord context-objektet

        Raises:
            ResponseError: Hvis sending av meldingen feiler
        """
        try:
            await ctx.send(
                "<:lamarbruh:764434396240805898> DOINK "
                "<:lamarbruh:764434396240805898> "
            )
        except Exception as e:
            raise ResponseError(
                "doink",
                f"Kunne ikke sende doink-melding: {str(e)}"
            )

    @commands.command(name="incel")
    async def incel(self, ctx):
        """Selvforklarende.

        Args:
            ctx (commands.Context): Discord context-objektet

        Raises:
            ResponseError: Hvis sending av meldingen feiler
        """
        try:
            await ctx.send("Harrison Bitchker er gerontofil")
        except Exception as e:
            raise ResponseError(
                "incel",
                f"Kunne ikke sende Butker-melding: {str(e)}"
            )


async def setup(bot):
    """Setter opp cog-en i Discord bot-instansen.

    Args:
        bot (commands.Bot): Discord bot-instansen som skal få cog-en
    """
    await bot.add_cog(Responses(bot))
