"""Oppstart og hendelser for Discord-botten."""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.keep_alive import keep_alive
from core.utils.global_cooldown import setup_global_cooldown
from core.errors import BotError
from data.channel_ids import ADMIN_CHANNEL_ID

# === Last miljøvariabler ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# === Discord intents ===
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global cooldown for å unngå kommandospam
setup_global_cooldown(bot)

# === Cogs ===
COGS = [
    "cogs.utility",  # ping, småkommandoer
    "cogs.vestsk_tipping",  # kamper, eksporter, resultater
    "cogs.responses",  # forskjellige humorkommandoer
    "cogs.ppr",  # oppdaterer og poster PPRs
    "cogs.fantasy_reminders",  # generelle påminnelser for fantasyligaen
]


# === Events ===
@bot.event
async def on_ready():
    """Logger til konsollen når botten er klar og pålogget."""
    print(f"✅ Botten er logget inn som {bot.user}")


# --- Global error handler ---
@bot.event
async def on_command_error(ctx, error):
    """Global feilhåndtering: sender admin-varsel og enkel feedback."""
    # Ignorer kommandoer som ikke finnes
    if isinstance(error, commands.CommandNotFound):
        return
    # Cooldown-meldinger til brukeren
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"{ctx.author.mention} e ein liten pissemaur. STRAFFESHOT! "
            f"(Prøv igjen om {error.retry_after:.1f} sekunder.)"
        )
        return

    # Sjekk om error er en BotError
    if isinstance(error, BotError):
        error_msg = f"⚠️ BotError i `{ctx.command}`:\n```{error}```"
    else:
        # Andre exceptions
        error_msg = f"❌ Uventet feil i `{ctx.command}`:\n```{error}```"

    # Send til admin-kanal
    admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
    if admin_channel and isinstance(admin_channel, discord.TextChannel):
        await admin_channel.send(error_msg)

    # Logg i terminal
    print(f"[ERROR] Command: {ctx.command}, User: {ctx.author}, Error: {error}")


# === Main async startup ===
async def main():
    """Starter flask keep_alive, laster cogs og starter botten."""
    keep_alive()  # starter Flask-serveren for uptime
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"[COG] Lastet {cog}")
            except commands.ExtensionNotFound as e:
                print(f"[COG] Ikke funnet: {cog} ({e})")
            except commands.ExtensionFailed as e:
                print(f"[COG] FEIL ved lasting av {cog}: {e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"[COG] Uventet feil ved lasting av {cog}: {e}")

        if TOKEN is None:
            raise ValueError("TOKEN ikke definert i miljøvariabler")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
