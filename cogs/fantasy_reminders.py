import asyncio
from datetime import datetime, timedelta
import pytz
from discord.ext import commands
from data.channel_ids import PREIK_KANAL
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
        channel = self.bot.get_channel(PREIK_KANAL)

        while True:
            now: datetime = datetime.now(self.norsk_tz)
            weekday: int = now.weekday()

            try:
                # === Tirsdagspåminnelse ===
                if weekday == 1:  # tirsdag
                    week_num: int = now.isocalendar()[1]
                    reminder_time: datetime = now.replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )

                    if now < reminder_time:
                        sleep_seconds: float = (
                            reminder_time - now
                        ).total_seconds()
                        await asyncio.sleep(sleep_seconds)

                    if (
                        self.last_waiver_week is None or
                        self.last_waiver_week != week_num
                    ):
                        if channel:
                            await channel.send("@everyone Ikke glem waivers!")
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
                next_tuesday: datetime = now + timedelta(
                    days=(1 - weekday) % 7
                )
                next_tuesday = next_tuesday.replace(
                    hour=18, minute=0, second=0, microsecond=0
                )
                if next_tuesday <= now:
                    next_tuesday += timedelta(days=7)

                sleep_seconds: float = (next_tuesday - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                logger.error(
                    f"Feil i FantasyReminders: {e}. Prøver igjen om 5 min."
                )
                await asyncio.sleep(300)


async def setup(bot: Bot) -> None:
    """Setter opp cog-en i Discord bot-instansen.

    Args:
        bot (Bot): Discord bot-instansen som skal få cog-en
    """
    await bot.add_cog(FantasyReminders(bot))
