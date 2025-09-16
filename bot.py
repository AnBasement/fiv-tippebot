import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive
import asyncio
import time

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

# === Global cooldown ===
# 1 kommando per 5 sekunder per bruker
cooldown = commands.CooldownMapping.from_cooldown(1, 5, commands.BucketType.user)

@bot.check
async def global_cooldown(ctx: commands.Context):
    bucket = cooldown.get_bucket(ctx.message)
    retry_after = bucket.update_rate_limit()
    if retry_after:
        raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)
    return True

last_warned = {}

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        now = time.time()
        uid = ctx.author.id
        
        if uid not in last_warned or now - last_warned[uid] > 5:
            last_warned[uid] = now
            await ctx.send(
                f"{ctx.author.mention} e ein liten pissemaur. STRAFFESHOT! "
                f"(Prøv igjen om {error.retry_after:.1f} sekunder.)"
            )

    else:
        raise error

# === Cogs ===
cogs = [
    "cogs.utility",          # ping, småkommandoer
    "cogs.vestsk_tipping",   # kamper, eksporter, resultater
    "cogs.responses",        # forskjellige humorkommandoer
    "cogs.ppr",              # oppdaterer og poster PPRs
]

# === Events ===
@bot.event
async def on_ready():
    print(f"✅ Botten er logget inn som {bot.user}")

# === Main async startup ===
async def main():
    keep_alive()  # starter Flask-serveren for uptime
    async with bot:
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"[COG] Lastet {cog}")
            except Exception as e:
                print(f"[COG] FEIL ved lasting av {cog}: {e}")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())