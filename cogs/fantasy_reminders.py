import asyncio
from datetime import datetime, timedelta
import pytz
from discord.ext import commands
import discord
from data.channel_ids import PREIK_KANAL
from core.utils.espn_helpers import get_league
import logging
from discord.ext.commands import Bot

logger = logging.getLogger(__name__)


class FantasyReminders(commands.Cog):
    """Cog for ukentlige påminnelser i fantasyligaen.

    Denne cog-en håndterer automatiske meldinger i PREIK_KANAL,
    som påminnelser om å gjøre waiver-picks hver tirsdag kl. 18:00.

    Attributes:
        bot (commands.Bot): Discord bot-instansen
        norsk_tz (tzinfo): Tidssone for Norge (Europe/Oslo)
        last_waiver_week (Optional[int]):
            Siste uke det ble sendt tirsdagspåminnelse
    """

    def __init__(self, bot: Bot) -> None:
        """Initialiserer FantasyReminders cog.

        Args:
            bot (commands.Bot): Discord bot-instansen
        """
        self.bot: Bot = bot
        self.norsk_tz = pytz.timezone("Europe/Oslo")
        self.last_waiver_week: int | None = None
        self.bot.loop.create_task(self.reminder_scheduler())

    def _current_streak(self, team):
        length = getattr(team, "streak_length", 0)
        streak_type = getattr(team, "streak_type", "")
        if not length or not streak_type:
            return None, 0
        last = "W" if streak_type.upper().startswith("WIN") else "L"
        return last, length

    async def build_matchup_digest(self, channel):
        league = get_league()
        current_week = league.current_week
        last_week = max(1, current_week - 1)
        next_week = current_week

        msg = []

        # Recap: Ukens oppsummering (Uke X)
        msg.append(f"**Ukens oppsummering (Uke {last_week}):**")
        recap_boxes = league.box_scores(week=last_week)

        recap_lines = []
        nailbiter = None
        toppscorer = None
        lavest = None
        bench_award = None
        overachiever = None
        underachiever = None
        for box in recap_boxes:
            home, away = box.home_team, box.away_team
            hs, ascore = box.home_score, box.away_score
            if hs > ascore:
                line = (
                    f"- **{home.team_name} ({hs:.2f})** – "
                    f"{away.team_name} ({ascore:.2f})"
                )
            elif ascore > hs:
                line = (
                    f"- {home.team_name} ({hs:.2f}) – "
                    f"**{away.team_name} ({ascore:.2f})**"
                )
            else:
                line = (
                    f"- {home.team_name} ({hs:.2f}) – {away.team_name} ({ascore:.2f})"
                )
            recap_lines.append(line)
            margin = abs(hs - ascore)
            if nailbiter is None or margin < nailbiter[0]:
                nailbiter = (
                    margin,
                    f"{home.team_name} vs {away.team_name} (margin {margin:.2f})",
                )
            for team, score in [(home, hs), (away, ascore)]:
                if toppscorer is None or score > toppscorer[0]:
                    toppscorer = (score, f"{team.team_name} med {score:.2f} poeng")
                if lavest is None or score < lavest[0]:
                    lavest = (score, f"{team.team_name} med {score:.2f} poeng")

            # Poeng på benken (slot_position BE)
            def bench_points(lineup):
                return sum(p.points for p in lineup if p.slot_position == "BE")

            home_bench = bench_points(box.home_lineup)
            away_bench = bench_points(box.away_lineup)
            for team, bench_sum in [(home, home_bench), (away, away_bench)]:
                if bench_award is None or bench_sum > bench_award[0]:
                    bench_award = (
                        bench_sum,
                        f"{team.team_name} med {bench_sum:.2f} poeng på benken",
                    )

            # Over/underprestert basert på projisert poeng
            for team, actual, projected in [
                (home, hs, box.home_projected),
                (away, ascore, box.away_projected),
            ]:
                diff = actual - projected if projected not in (None, -1) else actual
                if overachiever is None or diff > overachiever[0]:
                    overachiever = (
                        diff,
                        f"{team.team_name} overpresterte med {diff:.2f} mot proj.",
                    )
                if underachiever is None or diff < underachiever[0]:
                    underachiever = (
                        diff,
                        f"{team.team_name} underpresterte med {diff:.2f} mot proj.",
                    )

        if recap_lines:
            msg += recap_lines
        else:
            msg.append("- Ingen kamper å oppsummere.")

        # Ukespriser/høydepunkter
        msg.append("")
        msg.append("**Ukespriser:**")
        if nailbiter:
            msg.append(f"- Ukens neglebiter: {nailbiter[1]}")
        if toppscorer:
            msg.append(f"- Toppscorer: {toppscorer[1]}")
        if lavest:
            msg.append(f"- Bunnsuger: {lavest[1]}")
        if bench_award:
            msg.append(f"- Benkesliteren: {bench_award[1]}")
        if overachiever:
            msg.append(f"- Overpresterte: {overachiever[1]}")
        if underachiever:
            msg.append(f"- Underpresterte: {underachiever[1]}")

        # Streaks (3+)
        msg.append("")
        msg.append("**Seierrekker (3+):**")
        streaks = []
        for team in league.teams:
            last, run = self._current_streak(team)
            if run >= 3:
                streaks.append((team.team_name, last, run))
        hot = [s for s in streaks if s[1] == "W"]
        cold = [s for s in streaks if s[1] == "L"]
        if hot:
            for name, _, run in hot:
                msg.append(f"- {name}: {run} seiere på rad")
        else:
            msg.append("- Ingen")

        msg.append("")
        msg.append("**Tapsrekker (3+):**")
        if cold:
            for name, _, run in cold:
                msg.append(f"- {name}: {run} tap på rad")
        else:
            msg.append("- Ingen")

        # Preview: Ukens kamper (Uke next_week)
        msg.append("")
        msg.append(f"**Neste ukes kamper (Uke {next_week}):**")
        preview_boxes = league.box_scores(week=next_week)
        for box in preview_boxes:
            home, away = box.home_team, box.away_team
            msg.append(
                f"- {away.team_name} ({away.wins}-{away.losses}) @ "
                f"{home.team_name} ({home.wins}-{home.losses})"
            )

        if channel:
            await channel.send("\n".join(msg))

    async def reminder_scheduler(self) -> None:
        """
        Scheduler som sender ukentlig påminnelse om waivers
        tirsdager kl. 18:00.

            Sjekker tidspunkt for neste tirsdag, og sover til det tidspunktet.
            Hvis botten startes midt i uken, finner den automatisk neste tirsdag.
            Sørger for at meldingen kun sendes én gang per uke ved å sjekke
            `last_waiver_week`.
            Logger eventuelle feil og backoff på 5 minutter ved exception.

            Attributes:
                channel (discord.TextChannel): Discord-kanalen der meldingen sendes
                now (datetime): Nåværende tidspunkt i norsk tidssone
                weekday (int):
                    Ukedag for nåværende tidspunkt (0=mandag, 1=tirsdag, …)
                week_num (int): ISO-ukenummer for nåværende uke
                reminder_time (datetime): Tidspunkt meldingen skal sendes
                tomorrow (datetime):
                    Dagen etter reminder_time, for å unngå dobbelposting
                next_tuesday (datetime): Beregnet tidspunkt for neste tirsdag

            Example:
                Scheduler kjører i bakgrunnen som en asyncio-task:

                    >>> fantasy_cog = FantasyReminders(bot)
                    >>> bot.add_cog(fantasy_cog)
        """
        await self.bot.wait_until_ready()
        channel: discord.TextChannel | None = None
        while not isinstance(channel, discord.TextChannel):
            channel = self.bot.get_channel(PREIK_KANAL)
            if not isinstance(channel, discord.TextChannel):
                logger.warning(
                    f"Fant ikke tekstkanal med id {PREIK_KANAL}, prøver igjen om 30s"
                )
                await asyncio.sleep(30)

        while True:
            now: datetime = datetime.now(self.norsk_tz)
            weekday: int = now.weekday()

            try:
                # === Tirsdagspåminnelse ===
                if weekday == 1:  # tirsdag
                    week_num: int = now.isocalendar()[1]
                    week_num = 1
                    reminder_time: datetime = now.replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )

                    if now < reminder_time:
                        sleep_seconds: float = (reminder_time - now).total_seconds()
                        await asyncio.sleep(sleep_seconds)

                    if (
                        self.last_waiver_week is None
                        or self.last_waiver_week != week_num
                    ):
                        if channel:
                            await channel.send("@everyone Ikke glem waivers!")
                            await self.build_matchup_digest(channel)
                            self.last_waiver_week = week_num
                            logger.info(
                                f"Tirsdagspåminnelse sendt for uke {week_num} "
                                f"({reminder_time})"
                            )

                    tomorrow: datetime = reminder_time + timedelta(days=1)
                    sleep_seconds = (
                        tomorrow - datetime.now(self.norsk_tz)
                    ).total_seconds()
                    await asyncio.sleep(sleep_seconds)
                    continue

                # === Beregn tid til neste tirsdag ===
                next_tuesday: datetime = now + timedelta(days=(1 - weekday) % 7)
                next_tuesday = next_tuesday.replace(
                    hour=18, minute=0, second=0, microsecond=0
                )
                if next_tuesday <= now:
                    next_tuesday += timedelta(days=7)

                sleep_seconds: float = (next_tuesday - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                logger.error(f"Feil i FantasyReminders: {e}. Prøver igjen om 5 min.")
                await asyncio.sleep(300)


async def setup(bot: Bot) -> None:
    """Setter opp cog-en i Discord bot-instansen.

    Args:
        bot (Bot): Discord bot-instansen som skal få cog-en
    """
    await bot.add_cog(FantasyReminders(bot))
