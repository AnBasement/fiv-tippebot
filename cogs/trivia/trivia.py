import random
import asyncio
import time
from discord.ext import commands
from cogs.trivia.schema import load_questions, Question
from pathlib import Path
from data.brukere import DISCORD_TO_NAME, TEAM_NAMES, TEAM_ABBREVIATIONS
from cogs.trivia.poeng import update_score, get_scores

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
            navn = DISCORD_TO_NAME.get(msg.author.id, msg.author.name)
            update_score(navn, points)

            await ctx.send(
                f"{msg.author.mention} svarte riktig etter {elapsed:.1f} sekunder! +{points} poeng"
            )

        except asyncio.TimeoutError:
            await ctx.send(f"Too slow! Riktig svar: **{answer}**")

    @commands.command(name="toppliste")
    async def toppliste(self, ctx):
        scores = get_scores()
        if not scores:
            await ctx.send("Ingen har poeng!")
            return

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        lines = []
        for navn, poeng in sorted_scores[:10]:
            team_name = TEAM_NAMES.get(navn, navn)
            team_abbr = TEAM_ABBREVIATIONS.get(team_name, "")
            if team_abbr:
                lines.append(f"{navn} ({team_abbr}): {poeng} poeng")
            else:
                lines.append(f"{navn}: {poeng} poeng")

        leaderboard = "\n".join(lines)
        await ctx.send(f"Topplisten:\n{leaderboard}")

# --- Setup ---
async def setup(bot):
    """Legger til Trivia-cog i Discord-botten."""
    await bot.add_cog(Trivia(bot))
