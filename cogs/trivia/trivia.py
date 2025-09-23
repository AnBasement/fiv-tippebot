import random
import asyncio
import time
from discord.ext import commands
from cogs.trivia.schema import load_questions, Question
from pathlib import Path
from data.brukere import DISCORD_TO_NAME, TEAM_NAMES, TEAM_ABBREVIATIONS
from cogs.trivia.poeng import update_score, get_scores
from core.decorators import admin_only

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
        self.active_sessions = {}

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
            # Vent på første riktige svar i maks 60 sekunder
            msg = await self.bot.wait_for("message", timeout=60.0, check=check)
            elapsed = time.monotonic() - start_time

            # Gi poeng basert på tid
            if elapsed <= 5:
                points = 5
            elif elapsed <= 30:
                points = 3
            else:
                points = 1
            navn = DISCORD_TO_NAME.get(msg.author.id, msg.author.name)
            await ctx.send(
                f"{msg.author.mention} svarte riktig etter {elapsed:.1f} sekunder! +{points} poeng"
            )
            update_score(navn, points)

        except asyncio.TimeoutError:
            await ctx.send(f"Too slow! Riktig svar: **{answer}**")

    @commands.command(name="triviasesh")
    @admin_only()
    async def triviasesh(self, ctx, category: str = "nfl"):
        if ctx.channel.id in self.active_sessions:
            await ctx.send("Det er allerede en aktiv trivia i denne kanalen.")
            return

        task = self.bot.loop.create_task(self.run_trivia_session(ctx, category))
        self.active_sessions[ctx.channel.id] = task

    async def run_trivia_session(self, ctx, category: str):
        try:
            session_scores = {}
            for i in range(1, 11):
                question = get_random_question(category)
                question_text = question.spørsmål_tekst
                answer = question.svar

                await ctx.send(f"Spørsmål {i}/10 ({category.upper()}): {question_text}")

                start_time = time.monotonic()

                def check(msg):
                    return (
                        msg.channel == ctx.channel
                        and not msg.author.bot
                        and msg.content.lower() == answer.lower()
                    )

                try:
                    msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                    elapsed = time.monotonic() - start_time

                    # Poeng basert på tid
                    if elapsed <= 5:
                        points = 5
                    elif elapsed <= 30:
                        points = 3
                    else:
                        points = 1

                    navn = DISCORD_TO_NAME.get(msg.author.id, msg.author.name)
                    await ctx.send(
                        f"{msg.author.mention} svarte riktig etter {elapsed:.1f} sekunder! "
                        f"+{points} poeng"
                    )

                    # Oppdater både midlertidig session-score og den globale
                    session_scores[navn] = session_scores.get(navn, 0) + points
                    update_score(navn, points)

                except asyncio.TimeoutError:
                    await ctx.send(f"Too slow! Riktig svar: **{answer}**")

                # liten pause mellom spørsmål
                await asyncio.sleep(1)

            # Etter alle spørsmålene: vis poengsummer for denne sesjonen
            if session_scores:
                leaderboard_lines = [
                    f"{navn}: {poeng} poeng"
                    for navn, poeng in sorted(
                        session_scores.items(), key=lambda x: x[1], reverse=True
                    )
                ]

                leaderboard_text = "\n".join(leaderboard_lines)
                await ctx.send(f"Triviasesh ferdig! Toppliste:\n{leaderboard_text}")
            else:
                await ctx.send("Ingen fikk poeng denne runden.")
        except asyncio.CancelledError:
            await ctx.send("Trivia avbrutt.")
            raise
        finally:
            self.active_sessions.pop(ctx.channel.id, None)

    @commands.command(name="stopptrivia")
    async def stopptrivia(self, ctx):
        task = self.active_sessions.get(ctx.channel.id)
        if not task:
            await ctx.send("Ingen aktiv trivia i denne kanalen.")
            return

        task.cancel()

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
        await ctx.send(f"Triviasjefene:\n{leaderboard}")

# --- Setup ---
async def setup(bot):
    """Legger til Trivia-cog i Discord-botten."""
    await bot.add_cog(Trivia(bot))
