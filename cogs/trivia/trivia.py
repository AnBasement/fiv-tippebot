import random
import asyncio
import time
from discord.ext import commands
from cogs.trivia.schema import load_questions, Question
from pathlib import Path
from data.brukere import DISCORD_TO_NAME, TEAM_NAMES, TEAM_ABBREVIATIONS

# Enkel poenglogg (kan senere byttes ut med Sheets)
scores = {}  # key: user_id, value: {"username": str, "points": int}

def update_score(user_id: int, username: str, points: int):
    if user_id in scores:
        scores[user_id]["points"] += points
    else:
        scores[user_id] = {"username": username, "points": points}

def get_random_question(category: str = "nfl") -> Question:
    """
    Henter et tilfeldig spørsmål fra valgt kategori.
    """
    file_path = Path(f"cogs/trivia/data/lists/{category.lower()}.yaml")
    if not file_path.exists():
        # fallback til nfl hvis fil mangler
        file_path = Path("cogs/trivia/data/lists/nfl.yaml")
        category = "nfl"
    questions = load_questions(file_path, kategori=category.upper())
    if not questions:
        raise ValueError(f"Ingen spørsmål funnet i kategori {category}")
    return random.choice(questions)

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def trivia(self, ctx, category: str = "nfl"):
        """
        Starter en trivia-runde i den gitte kategorien.
        """
        question = get_random_question(category)
        question_text = question.spørsmål_tekst
        answer = question.svar

        await ctx.send(f" Spørsmål ({category.upper()}): {question_text}")

        start_time = time.monotonic()

        def check(msg):
            return (
                msg.channel == ctx.channel
                and not msg.author.bot
                and msg.content.lower() == answer.lower()
            )

        try:
            # Vent på første riktige svar i maks 10 sekunder
            msg = await self.bot.wait_for("message", timeout=10.0, check=check)
            elapsed = time.monotonic() - start_time

            # Gi poeng basert på tid
            points = 3 if elapsed <= 5 else 1
            update_score(msg.author.id, msg.author.name, points)

            await ctx.send(
                f"{msg.author.mention} svarte riktig etter {elapsed:.1f} sekunder! +{points} poeng"
            )

        except asyncio.TimeoutError:
            await ctx.send(f"Too slow! Riktig svar: **{answer}**")

    @commands.command(name="toppliste")
    async def toppliste(self, ctx):
        """
        Viser topplisten med lag-/spillernavn basert på Discord-ID.
        """
        if not scores:
            await ctx.send("Ingen har poeng!")
            return

        sorted_scores = sorted(scores.items(), key=lambda x: x[1]["points"], reverse=True)

        lines = []
        for user_id, data in sorted_scores[:10]:
            navn = DISCORD_TO_NAME.get(user_id, data["username"])  # hent spiller
            team_name = TEAM_NAMES.get(navn, navn)                # hent lag
            team_abbr = TEAM_ABBREVIATIONS.get(team_name, "")     # hent forkortelse

            if team_abbr:
                lines.append(f"{navn} ({team_abbr}): {data['points']} poeng")
            else:
                lines.append(f"{navn}: {data['points']} poeng")

# --- Setup ---
async def setup(bot):
    """Legger til Trivia-cog i Discord-botten."""
    await bot.add_cog(Trivia(bot))
