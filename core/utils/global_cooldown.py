"""Global cooldown for å unngå spam av kommandoer"""

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

    @bot.check
    async def global_cooldown(ctx: commands.Context):
        bucket = cooldown.get_bucket(ctx.message)
        if bucket is None:
            return True
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(
                bucket.cooldown, retry_after, commands.BucketType.user
            )
        return True

    # Merk: on_command_error håndteres nå sentralt i core/bot.py
