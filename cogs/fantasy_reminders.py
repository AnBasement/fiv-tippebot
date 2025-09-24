import asyncio
from datetime import datetime, timedelta
import pytz
from discord.ext import commands
from data.channel_ids import PREIK_KANAL
import logging

logger = logging.getLogger(__name__)

class FantasyReminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.norsk_tz = pytz.timezone("Europe/Oslo")
        self.last_waiver_week = None
        self.bot.loop.create_task(self.reminder_scheduler())

    async def reminder_scheduler(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(PREIK_KANAL)

        while True:
            now = datetime.now(self.norsk_tz)
            weekday = now.weekday()

            try:
                # === Tirsdagspåminnelse ===
                if weekday == 1:  # tirsdag
                    week_num = now.isocalendar()[1]
                    reminder_time = now.replace(hour=18, minute=0, second=0, microsecond=0)

                    if now < reminder_time:
                        sleep_seconds = (reminder_time - now).total_seconds()
                        await asyncio.sleep(sleep_seconds)

                    if self.last_waiver_week is None or self.last_waiver_week != week_num:
                        if channel:
                            await channel.send("@everyone Ikke glem waivers!")
                            self.last_waiver_week = week_num
                            logger.info(
                                f"Tirsdagspåminnelse sendt for uke {week_num} ({reminder_time})"
                            )

                    # Vent til neste dag for å unngå dobbelposting
                    tomorrow = reminder_time + timedelta(days=1)
                    await asyncio.sleep((tomorrow - datetime.now(self.norsk_tz)).total_seconds())
                    continue

                # === Beregn tid til neste tirsdag ===
                next_tuesday = now + timedelta(days=(1 - weekday) % 7)
                next_tuesday = next_tuesday.replace(hour=18, minute=0, second=0, microsecond=0)
                if next_tuesday <= now:
                    next_tuesday += timedelta(days=7)

                # Sov til neste tirsdag
                sleep_seconds = (next_tuesday - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                logger.error(f"Feil i FantasyReminders: {e}. Prøver igjen om 5 min.")
                await asyncio.sleep(300)
