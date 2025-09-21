from discord.ext import commands
from discord.ext.commands import Bot, Context

class Utility(commands.Cog):
    """Cog for enkle hjelpekommandoer og verktøy.
    
    Cogen inneholder per nå kun en ping-kommando for å sjekke
    at botten er aktiv og responderer.
    
    Attributes:
        bot (Bot): Discord bot-instansen
    """

    def __init__(self, bot: Bot) -> None:
        """Initialiserer Utility cog.
        
        Args:
            bot (Bot): Discord bot-instansen
        """
        self.bot: Bot = bot

    async def _ping_impl(self, ctx: Context) -> None:
        """Intern implementasjon av ping-kommandoen.
        
        Args:
            ctx (Context): Discord context-objektet
        """
        await ctx.send("Pong! ✅")

    @commands.command()
    async def ping(self, ctx: Context) -> None:
        """En enkel kommando for å sjekke om botten er aktiv.
        
        Botten svarer med 'Pong! ✅' for å indikere
        at botten er aktiv.

        Args:
            ctx (Context): Discord context-objektet
        """
        await self._ping_impl(ctx)

async def setup(bot: Bot) -> None:
    """Setter opp cog-en i Discord bot-instansen.
    
    Args:
        bot (Bot): Discord bot-instansen som skal få cog-en
    """
    await bot.add_cog(Utility(bot))
