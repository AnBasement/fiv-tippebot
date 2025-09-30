# Global cooldown for å unngå spam av kommandoer
import time
from discord.ext import commands


def setup_global_cooldown(bot, rate=1, per=5):
    """
    Setter opp en global cooldown på botten.

    bot: commands.Bot
        Discord-bot instans.
    rate: int
        Antall kommandoer tillatt per tidsperiode.
    per: int
        Tidsperiode i sekunder.
    """
    cooldown = commands.CooldownMapping.from_cooldown(
        rate, per, commands.BucketType.user
        )
    last_warned = {}

    @bot.check
    async def global_cooldown(ctx: commands.Context):
        bucket = cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(
                bucket, retry_after, commands.BucketType.user
                )
        return True

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            now = time.time()
            uid = ctx.author.id
            if uid not in last_warned or now - last_warned[uid] > per:
                last_warned[uid] = now
                await ctx.send(
                    f"{ctx.author.mention} e ein liten pissemaur. "
                    f"STRAFFESHOT! "
                    f"(Prøv igjen om {error.retry_after:.1f} sekunder.)"
                )
        else:
            raise error
