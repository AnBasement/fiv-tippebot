import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

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

# === Last cogs ===
cogs = [
    "cogs.utility",          # ping, småkommandoer
    "cogs.vestsk_tipping",   # kamper, eksporter, resultater
]

for cog in cogs:
    try:
        bot.load_extension(cog)
        print(f"[COG] Lastet {cog}")
    except Exception as e:
        print(f"[COG] FEIL ved lasting av {cog}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Botten er logget inn som {bot.user}")

keep_alive()
bot.run(TOKEN)
