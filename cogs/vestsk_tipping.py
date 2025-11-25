"""
Hovedmodul for Vestsk Tipping-funksjonalitet.

Denne modulen håndterer all funksjonalitet relatert til Vestsk Tipping,
inkludert:
- Registrering av bets
- Eksport av bets til Google Sheets
- Resultatoppdatering og poengberegning
- Automatiske påminnelser for tipping på torsdager og søndager
"""

from discord.ext import commands
from discord.ext.commands import CheckFailure
import aiohttp
from aiohttp import ClientTimeout
from datetime import datetime, timedelta
import pytz
import re
import asyncio
import logging

from data.teams import teams, team_emojis, team_location, DRAW_EMOJI
from cogs.sheets import get_sheet, green_format, red_format, yellow_format
from core.errors import (
    APIFetchError,
    NoEventsFoundError,
    ExportError,
    ResultaterError,
)
from core.decorators import admin_only
from data.channel_ids import PREIK_KANAL, VESTSK_KANAL

# Konfigurer logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_espn_date(datestr: str) -> datetime:
    """Konverterer ESPN API datoformat til datetime.

    Args:
        datestr (str): Datostrengen fra ESPN API (ISO format med 'Z')

    Returns:
        datetime: Konvertert datetime-objekt i UTC

    Example:
        >>> parse_espn_date("2025-09-21T18:00Z")
        datetime(2025, 9, 21, 18, 0, tzinfo=UTC)
    """
    return datetime.fromisoformat(datestr.replace("Z", "+00:00"))


class VestskTipping(commands.Cog):
    """Cog for håndtering av Vestsk Tipping.

    Denne cog-en inneholder all logikk for tipping på NFL-kamper,
    inkludert registrering av bets, eksport til Google Sheets,
    resultatoppdatering og automatiske påminnelser.

    Attributes:
        bot (commands.Bot): Discord bot-instansen
        norsk_tz (tzinfo): Tidssone for Norge (Europe/Oslo)
        last_reminder_week (Optional[int]): Siste uke det ble sendt
            påminnelse
        last_reminder_sunday (Optional[datetime]): Siste søndag det ble
            sendt påminnelse
        reminder_task (asyncio.Task): Async task for påminnelser
    """

    @staticmethod
    def is_valid_game_message(msg_content: str) -> bool:
        """Validerer om en melding er et gyldig kampformat.

        Godtar to formater:
        1. 'lag @ lag' for tipping
        2. 'lag - lag: score-score' for resultat

        Args:
            msg_content (str): Meldingsinnholdet som skal valideres

        Returns:
            bool: True hvis meldingen er gyldig kampformat

        Example:
            >>> is_valid_game_message("Patriots @ Bills")
            True
            >>> is_valid_game_message("Patriots - Bills: 24-17")
            True
            >>> is_valid_game_message("@everyone Patriots vs Bills")
            False
        """
        clean_text = re.sub(r'<:.+?:\d+>', '', msg_content).strip()
        if re.search(r'<@|@everyone|@here', clean_text):
            return False
        return bool(
            re.match(r'^[A-Za-z0-9 .]+ @ [A-Za-z0-9 .]+$', clean_text) or
            re.match(r'^[A-Za-z0-9 .]+ - [A-Za-z0-9 .]+: \d+-\d+$', clean_text)
        )

    def __init__(self, bot):
        """Initialiserer VestskTipping cog.

        Args:
            bot (commands.Bot): Discord bot-instansen
        """
        self.bot = bot
        self.norsk_tz = pytz.timezone("Europe/Oslo")
        self.last_reminder_week = None
        self.last_reminder_sunday = None
        task = self.reminder_scheduler()
        self.reminder_task = self.bot.loop.create_task(task)

    def get_players(self, sheet) -> dict:
        """
        Returnerer mapping: Discord ID → kolonne.
        Kolonneindekser starter på 1 (B=1, C=2, ...).
        """
        id_row = sheet.row_values(2)
        players = {id_row[i]: i for i in range(1, len(id_row)) if id_row[i]}
        logger.debug(f"get_players: {players}")
        return players

    def cog_unload(self):
        self.reminder_task.cancel()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, CheckFailure):
            await ctx.send(
                "Kanskje hvis du spør veldig pent så kan du få lov te å "
                "bruke botten."
            )
            return

    # === kamper ===
    @commands.command()
    @admin_only()
    async def kamper(self, ctx, uke: int | None = None):
        await self._kamper_impl(ctx, uke)

    async def _kamper_impl(self, ctx, uke: int | None = None):
        now = datetime.now()
        season = now.year if now.month >= 3 else now.year - 1
        base_url = (
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
            "scoreboard"
        )
        if uke:
            url = f"{base_url}?dates={season}&seasontype=2&week={uke}"
        else:
            url = base_url
        try:
            async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
                try:
                    async with session.get(url) as resp:
                        data = await resp.json()
                except asyncio.TimeoutError:
                    logger.warning(
                        "API timeout mot ESPN, prøver igjen om 5 sekunder. URL=%s",
                        url
                    )
                    await asyncio.sleep(5)
                    async with session.get(url) as resp:
                        data = await resp.json()
        except Exception as e:
            raise APIFetchError(url, e) from e

        events = data.get("events", [])
        if not events:
            raise NoEventsFoundError(uke)

        # Sorter events på datetime
        events.sort(key=lambda ev: parse_espn_date(ev.get("date")))
        for ev in events:
            comps = ev["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            home_team = home["team"]["displayName"]
            away_team = away["team"]["displayName"]
            away_emoji = teams.get(away_team, {'emoji': ''})['emoji']
            home_emoji = teams.get(home_team, {'emoji': ''})['emoji']
            await ctx.send(
                f"{away_emoji} {away_team} @ {home_team} {home_emoji}"
            )

        # Send en melding i preik
        kanal = ctx.bot.get_channel(PREIK_KANAL)
        if kanal:
            await kanal.send(
                f"@everyone Ukens kamper er lagt ut i <#{VESTSK_KANAL}>!"
                )

    async def reminder_scheduler(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(PREIK_KANAL)

        while True:
            now = datetime.now(self.norsk_tz)
            weekday = now.weekday()

            try:
                # === Torsdagspåminnelse ===
                if weekday == 3:
                    week_num = now.isocalendar()[1]
                    reminder_time = now.replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )
                    if now < reminder_time:
                        sleep_seconds = (reminder_time - now).total_seconds()
                        await asyncio.sleep(sleep_seconds)

                        if (self.last_reminder_week is None or
                                self.last_reminder_week != week_num):
                            await channel.send(
                                (
                                    "@everyone RAUÅ I GIR, ukå begynne snart "
                                    "så sjekk "
                                    f"<#{VESTSK_KANAL}>!"
                                )
                            )
                            self.last_reminder_week = week_num
                            logger.info(
                                f"Torsdagspåminnelse sendt for uke {week_num} "
                                f"({reminder_time})"
                            )

                        tomorrow = reminder_time + timedelta(days=1)
                        time_diff = (
                            tomorrow - datetime.now(self.norsk_tz)
                        ).total_seconds()
                        await asyncio.sleep(time_diff)
                        continue

                # === Søndagspåminnelse ===
                if weekday == 6:
                    url = (
                        "https://site.api.espn.com/apis/site/v2/sports/"
                        "football/"
                        "nfl/scoreboard"
                    )

                    try:
                        async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
                            try:
                                async with session.get(url) as resp:
                                    data = await resp.json()
                            except asyncio.TimeoutError:
                                logger.warning(
                                    "API timeout mot ESPN, prøver igjen om 5 sekunder. URL=%s",
                                    url
                                )
                                await asyncio.sleep(5)
                                async with session.get(url) as resp:
                                    data = await resp.json()
                    except Exception as e:
                        logger.error(
                            f"Kunne ikke hente data fra ESPN API: {e}. "
                            "Prøver igjen om 5 min."
                        )
                        await asyncio.sleep(300)  # backoff før retry
                        continue

                    events = data.get("events", [])
                    sunday_events = [
                        ev for ev in events
                        if parse_espn_date(ev["date"]).astimezone(
                            self.norsk_tz
                        ).weekday() == 6
                    ]

                    if sunday_events:
                        sunday_events.sort(key=lambda ev: ev.get("date"))
                        first_sunday_game = parse_espn_date(
                            sunday_events[0]["date"]
                        ).astimezone(self.norsk_tz)
                        reminder_time = (
                            first_sunday_game - timedelta(minutes=60)
                        )

                        if now < reminder_time:
                            sleep_seconds = (
                                reminder_time - now
                            ).total_seconds()
                            await asyncio.sleep(sleep_seconds)

                            if (
                                self.last_reminder_sunday is None
                                or (self.last_reminder_sunday !=
                                    first_sunday_game.date())
                            ):
                                await channel.send(
                                    "@everyone Early window snart, husk "
                                    f"<#{VESTSK_KANAL}>"
                                )
                                self.last_reminder_sunday = (
                                    first_sunday_game.date()
                                )
                                logger.info(
                                    "Søndagspåminnelse sendt for "
                                    f"{first_sunday_game.date()} "
                                    f"({reminder_time})"
                                )

                            tomorrow = reminder_time + timedelta(days=1)
                            await asyncio.sleep(
                                (
                                    tomorrow - datetime.now(self.norsk_tz)
                                ).total_seconds()
                            )
                            continue

                # === Beregn tid til neste vindu ===
                next_thursday = now + timedelta(days=(3 - weekday) % 7)
                next_thursday = next_thursday.replace(
                    hour=18, minute=0, second=0, microsecond=0
                )
                if next_thursday <= now:
                    next_thursday += timedelta(days=7)

                next_sunday = now + timedelta(days=(6 - weekday) % 7)
                next_sunday = next_sunday.replace(
                    hour=8, minute=0, second=0, microsecond=0
                )
                if next_sunday <= now:
                    next_sunday += timedelta(days=7)

                sleep_until = min(next_thursday, next_sunday)
                sleep_seconds = (sleep_until - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                logger.error(
                    f"Feil i reminder_scheduler: {e}. Prøver igjen om 5 min."
                )
                await asyncio.sleep(300)

    def _format_event(self, ev):
        if "home" in ev and "away" in ev:
            home_team = ev["home"]
            away_team = ev["away"]
        else:
            comps = ev["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            home_team = home["team"]["displayName"]
            away_team = away["team"]["displayName"]

        return (
            f"{teams.get(away_team, {'emoji': ''})['emoji']} {away_team} @ "
            f"{home_team} {teams.get(home_team, {'emoji': ''})['emoji']}"
        )

    # === eksport ===
    @commands.command(name="eksporter")
    @admin_only()
    async def export(self, ctx, uke: int | None = None):
        await self._export_impl(ctx, uke)

    async def _export_impl(self, ctx, uke: int | None = None):
        try:
            sheet = await asyncio.wait_for(
                asyncio.to_thread(get_sheet, "Vestsk Tipping"), timeout=10
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return
        channel = ctx.channel

        players = self.get_players(sheet)
        num_players = len(players)

        norsk_tz = pytz.timezone("Europe/Oslo")
        now = datetime.now(norsk_tz)

        # Søk bakover i tid for å finne siste gruppe med bot-meldinger
        # Begrens søket til siste 14 dager for å unngå for gamle meldinger
        search_limit = now - timedelta(days=14)

        emoji_to_team_short = {v: k for k, v in team_emojis.items()}
        is_valid_game_message = VestskTipping.is_valid_game_message

        # Hent alle bot-meldinger fra de siste 14 dagene
        all_bot_messages = []
        async for msg in channel.history(limit=200, after=search_limit):
            if (
                msg.author == self.bot.user
                and is_valid_game_message(msg.content)
            ):
                all_bot_messages.append(msg)

        if not all_bot_messages:
            raise ExportError(
                f"Ingen gyldige bot-meldinger funnet siden {search_limit}"
            )

        # Sorter meldingene etter tid (nyeste først)
        all_bot_messages.sort(key=lambda m: m.created_at, reverse=True)

        # Finn den nyeste gruppen med meldinger (samme sesjon)
        # Stopp ved første gap på mer enn 2 timer mellom meldinger
        messages = [all_bot_messages[0]]  # Start med nyeste melding

        for i in range(1, len(all_bot_messages)):
            current_msg = all_bot_messages[i]
            previous_msg = all_bot_messages[i-1]

            # Hvis det er mer enn 2 timer mellom meldingene, stopp
            time_diff = previous_msg.created_at - current_msg.created_at
            if time_diff.total_seconds() > 7200:  # 2 timer = 7200 sekunder
                break

            messages.append(current_msg)

        # Sorter tilbake til kronologisk rekkefølge
        messages.sort(key=lambda m: m.created_at)

        if not messages:
            raise ExportError("Ingen meldinger funnet fra siste posting")

        values = []
        for msg in messages:
            clean_text = re.sub(r'<:.+?:\d+>', '', msg.content).strip()
            comps = clean_text.split("@")
            if len(comps) == 2:
                away_team_full = comps[0].strip()
                home_team_full = comps[1].strip()
                away = team_location.get(
                    away_team_full, away_team_full.split()[-1]
                )
                home = team_location.get(
                    home_team_full, home_team_full.split()[-1]
                )
                kampkode = f"{away}@{home}"
            else:
                kampkode = clean_text

            row = [kampkode] + [""] * num_players
            for reaction in msg.reactions:
                async for user in reaction.users():
                    discord_id = str(user.id)
                    if user != self.bot.user and discord_id in players:
                        col_idx = players[discord_id]
                        emoji_str = str(reaction.emoji)
                        if emoji_str == DRAW_EMOJI:
                            row[col_idx] = "Uavgjort"
                        else:
                            row[col_idx] = emoji_to_team_short.get(
                                emoji_str, ""
                            )
            values.append(row)

        try:
            all_rows_colA = await asyncio.wait_for(
                asyncio.to_thread(sheet.col_values, 1), timeout=10
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return
        last_data_row = len(all_rows_colA)
        start_row = last_data_row + 2

        if values:
            try:
                end_row = start_row + len(values) - 1
                end_col = 1 + num_players
                range_notation = f"A{start_row}:{chr(64 + end_col)}{end_row}"
                try:
                    cell_range = await asyncio.wait_for(asyncio.to_thread(
                        sheet.range,
                        range_notation
                        ), timeout=10
                    )
                except asyncio.TimeoutError:
                    logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
                    return
                except Exception as e:
                    logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
                    return
                flat_values = [cell for row in values for cell in row]
                for cell_obj, val in zip(cell_range, flat_values):
                    cell_obj.value = val
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(sheet.update_cells, cell_range), timeout=10
                    )
                except asyncio.TimeoutError:
                    logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
                    return
                except Exception as e:
                    logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
                    return
            except Exception as e:
                raise ExportError(
                    f"Feil ved eksport til sheet '{sheet.title}': {e}"
                ) from e

            await ctx.send("Kampdata eksportert til Sheets.")
        else:
            await ctx.send("Ingen verdier å oppdatere")

    # === resultater ===
    @commands.command(name="resultater")
    @admin_only()
    async def resultater(self, ctx, uke: int | None = None):
        """Kommando for å vise resultater for en uke."""
        logger.info(f"Kommando !resultater kjørt for uke={uke}")
        await self._resultater_impl(ctx, uke)

    async def _resultater_impl(self, ctx, uke: int | None = None):
        try:
            sheet = await asyncio.wait_for(
                asyncio.to_thread(get_sheet, "Vestsk Tipping"),
                timeout=10
            )
            if not sheet:
                raise ResultaterError(
                    "Kunne ikke hente worksheet 'Vestsk Tipping'"
                )
        except asyncio.TimeoutError:
            raise ResultaterError(
                "Timeout ved åpning av sheet 'Vestsk Tipping'"
            )
        except Exception as e:
            raise ResultaterError(f"Feil ved henting av sheet: {e}") from e

        logger.debug(f"Henter sheet: {sheet.title if sheet else 'None'}")

        norsk_tz = pytz.timezone("Europe/Oslo")
        now = datetime.now(norsk_tz)
        season = now.year if now.month >= 3 else now.year - 1
        logger.debug(f"Sesong: {season}")

        url = (
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
            "scoreboard"
        )
        if uke:
            url += f"?dates={season}&seasontype=2&week={uke}"
        logger.debug(f"Henter URL: {url}")

        try:
            async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
                try:
                    async with session.get(url) as resp:
                        data = await resp.json()
                except asyncio.TimeoutError:
                    logger.warning(
                        "API timeout mot ESPN, prøver igjen om 5 sekunder. URL=%s",
                        url
                    )
                    await asyncio.sleep(5)
                    # Retry once
                    async with session.get(url) as resp:
                        data = await resp.json()
        except Exception as e:
            raise APIFetchError(url, e)

        events = data.get("events", [])
        logger.debug(f"Antall events hentet: {len(events)}")

        if not events:
            raise NoEventsFoundError(uke)

        kamp_resultater = {}
        for ev in events:
            try:
                comps = ev["competitions"][0]["competitors"]
                home = next(c for c in comps if c["homeAway"] == "home")
                away = next(c for c in comps if c["homeAway"] == "away")
                home_team = team_location.get(
                    home["team"]["displayName"],
                    home["team"]["displayName"].split()[-1],
                )
                away_team = team_location.get(
                    away["team"]["displayName"],
                    away["team"]["displayName"].split()[-1],
                )
                kampkode = f"{away_team}@{home_team}"

                home_score = int(home["score"])
                away_score = int(away["score"])
            except Exception as e:
                raise ResultaterError(
                    "Feil ved parsing av kampdata for "
                    f"{ev.get('id', 'ukjent')}"
                ) from e

            if home_score > away_score:
                kamp_resultater[kampkode] = home_team
            elif away_score > home_score:
                kamp_resultater[kampkode] = away_team
            else:
                kamp_resultater[kampkode] = "Uavgjort"
        logger.debug(f"Kampresultater: {kamp_resultater}")

        players = self.get_players(sheet)
        logger.debug(f"Spillere funnet: {players}")
        num_players = len(players)

        # Hent alle relevante rader og kolonner i én batch
        try:
            all_rows = await asyncio.wait_for(
                asyncio.to_thread(sheet.get_all_values),
                timeout=10
            )
            sheet_rows = all_rows[2:]
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return
        sheet_kamper = []
        row_mapping = {}
        gyldige_kampkoder = set(kamp_resultater.keys())
        for i, row in enumerate(sheet_rows, start=3):
            kampkode = row[0].strip()
            if kampkode in gyldige_kampkoder:
                sheet_kamper.append(kampkode)
                row_mapping[len(sheet_kamper)-1] = i

        logger.debug(f"Kamper i sheet: {sheet_kamper}")
        logger.debug(f"Row mapping: {row_mapping}")

        # Finn raden rett etter siste kamp for denne uken
        uke_total_row = max(row_mapping.values(), default=3) + 1
        sesong_total_row = uke_total_row + 1
        logger.debug(
            f"Uke total rad: {uke_total_row}, "
            f"sesong total rad: {sesong_total_row}"
        )

        green = green_format()
        red = red_format()
        yellow = yellow_format()

        uke_poeng = [0] * num_players

        # Kolonneindekser: discord_id → col_idx (batch-read starter på 2)
        player_ids = list(players.keys())
        start_col = 2
        end_col = start_col + num_players - 1
        start_row = min(row_mapping.values(), default=3)
        end_row = max(row_mapping.values(), default=3)

        # Hent alle celler for kampdata i én batch
        range_notation = (
            f"{chr(64 + start_col)}{start_row}:"
            f"{chr(64 + end_col)}{end_row}"
        )
        try:
            kamp_cell_range = await asyncio.wait_for(
                asyncio.to_thread(sheet.range, range_notation), timeout=10
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return

        # Lag mapping: (row_idx, col_idx) -> cell_obj
        cell_map = {(cell.row, cell.col): cell for cell in kamp_cell_range}

        cell_updates = []
        format_updates = []

        for idx, kampkode in enumerate(sheet_kamper):
            row_idx = row_mapping[idx]
            riktig_vinner = kamp_resultater.get(kampkode)
            logger.debug(
                f"Prosesserer kamp {kampkode} (riktig vinner: {riktig_vinner})"
            )

            for pidx, discord_id in enumerate(player_ids):
                col_idx = start_col + pidx
                cell_obj = cell_map.get((row_idx, col_idx))
                if cell_obj is None:
                    continue
                cell_value = cell_obj.value

                logger.debug(
                    f"Kampkode={kampkode}, riktig_vinner={riktig_vinner}, "
                    "teams=" + str([
                        (v.get('short'), v.get('name'))
                        for v in teams.values()
                    ])
                )

                gyldige_svar = (
                    [riktig_vinner] if riktig_vinner == "Uavgjort"
                    else [
                        v["short"]
                        for v in teams.values()
                        if (riktig_vinner and
                            v["short"].lower() == riktig_vinner.lower())
                    ]
                )

                if not cell_value:
                    fmt = yellow
                elif cell_value in gyldige_svar:
                    fmt = green
                    uke_poeng[pidx] += 1
                else:
                    fmt = red

                # Oppdater kun hvis verdi har endret seg
                new_value = cell_value if cell_value else ""
                if cell_obj.value != new_value:
                    cell_obj.value = new_value
                    cell_updates.append(cell_obj)
                format_updates.append((row_idx, col_idx, fmt))

        logger.info(f"Ukespoeng: {uke_poeng}")

        # --- Sett inn Ukespoeng på ny rad etter denne ukens kamper ---
        # Skriv "Ukespoeng" i kolA
        try:
            uke_label_cell = await asyncio.wait_for(
                asyncio.to_thread(sheet.cell, uke_total_row, 1),
                timeout=10
            )
            uke_label_cell.value = "Ukespoeng"
            cell_updates.append(uke_label_cell)
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return

        # Skriv ukespoeng i kolonnene
        for pidx, discord_id in enumerate(player_ids):
            col_idx = start_col + pidx
            try:
                cell_obj = await asyncio.wait_for(
                    asyncio.to_thread(sheet.cell, uke_total_row, col_idx),
                    timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
                return
            except Exception as e:
                logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
                return
            poeng = uke_poeng[pidx]
            if str(cell_obj.value) != str(poeng):
                cell_obj.value = str(poeng)
                cell_updates.append(cell_obj)

        # --- Finn siste Sesongpoeng-rad for å hente forrige totalsum ---
        try:
            all_sheet_rows = await asyncio.wait_for(
                asyncio.to_thread(sheet.get_all_values), timeout=10
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return
        forrige_sesong_row = None
        for i, row in enumerate(all_sheet_rows, start=1):
            if row and row[0].strip() == "Sesongpoeng":
                forrige_sesong_row = i

        # --- Sett inn Sesongpoeng på rad rett under Ukespoeng ---
        try:
            sesong_label_cell = await asyncio.wait_for(
                asyncio.to_thread(sheet.cell, uke_total_row + 1, 1),
                timeout=10
            )
            sesong_label_cell.value = "Sesongpoeng"
            cell_updates.append(sesong_label_cell)
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return

        for pidx, discord_id in enumerate(player_ids):
            col_idx = start_col + pidx
            tidligere_total = 0
            if forrige_sesong_row:
                val = all_sheet_rows[forrige_sesong_row-1][col_idx-1]
                tidligere_total = int(val) if val and str(val).isdigit() else 0

            ny_total = tidligere_total + uke_poeng[pidx]
            try:
                cell_obj = await asyncio.wait_for(
                    asyncio.to_thread(sheet.cell, uke_total_row + 1, col_idx),
                    timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
                return
            except Exception as e:
                logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
                return
            if str(cell_obj.value) != str(ny_total):
                cell_obj.value = str(ny_total)
                cell_updates.append(cell_obj)

        # === Batch update alle celler ===
        if cell_updates:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(sheet.update_cells, cell_updates), timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
                return
            except Exception as e:
                logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
                return
            except Exception as e:
                raise ResultaterError(
                    f"Feil ved batch-oppdatering av celler: {e}"
                ) from e

        # === Batch formatering med batchUpdate ===
        # Bruk green_format/red_format/yellow_format for batchUpdate.
        # Finn sheetId for arket
        try:
            sheet_id = sheet._properties['sheetId']
        except Exception as e:
            raise ResultaterError(f"Kunne ikke hente sheetId: {e}")

        # Lag batchUpdate-requests for alle celler som skal formateres
        requests = []
        for row_idx, col_idx, fmt in format_updates:
            # fmt er cellFormat-dict, f.eks. fra green_format()
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx-1,
                        "endRowIndex": row_idx,
                        "startColumnIndex": col_idx-1,
                        "endColumnIndex": col_idx
                    },
                    "cell": {"userEnteredFormat": fmt},
                    "fields": (
                        "userEnteredFormat.backgroundColor,"
                        "userEnteredFormat.textFormat"
                    )
                }
            })

        if requests:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        sheet.spreadsheet.batch_update,
                        {"requests": requests}
                    ),
                    timeout=10
                )
            except Exception as e:
                raise ResultaterError(
                    f"Feil ved batch-formattering av celler: {e}"
                )

        logger.info("Ferdig med oppdatering av sheet, sender Discord-melding")

        # Discord-melding
        try:
            header_row = await asyncio.wait_for(
                asyncio.to_thread(sheet.row_values, 1),
                timeout=10
            )
            header_row = header_row[1:1+num_players]
        except asyncio.TimeoutError:
            logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
            return
        except Exception as e:
            logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
            return
        
        discord_msg = []
        for idx, name in enumerate(header_row, start=2):
            uke_p = uke_poeng[idx-2]
            try:
                sesong_cell = await asyncio.wait_for(
                    asyncio.to_thread(sheet.cell, sesong_total_row, idx),
                    timeout=10
                )
                sesong_p_cell = sesong_cell.value
            except asyncio.TimeoutError:
                logger.warning("Timeout ved åpning av sheet Vestsk Tipping")
                return
            except Exception as e:
                logger.error(f"Kunne ikke åpne sheet Vestsk Tipping: {e}")
                return
            sesong_p = (
                int(sesong_p_cell)
                if sesong_p_cell and str(sesong_p_cell).isdigit()
                else 0
            )
            discord_msg.append((name, uke_p, sesong_p))

        discord_msg.sort(key=lambda x: x[1], reverse=True)
        lines = [f"```Poeng for uke {uke if uke else 'nåværende'}:"]
        for i, (name, uke_p, _) in enumerate(discord_msg, start=1):
            lines.append(f"{i}. {name:<10} {uke_p}")

        lines.append("")
        lines.append("Sesongtotal:")
        discord_msg.sort(key=lambda x: x[2], reverse=True)
        for i, (name, _, sesong_p) in enumerate(discord_msg, start=1):
            lines.append(f"{i}. {name:<10} {sesong_p}")

        lines.append("```")
        await ctx.send("\n".join(lines))
        await ctx.send(
            f"✅ Resultater for uke {uke if uke else 'nåværende'} er "
            "oppdatert."
        )


# --- Setup ---
async def setup(bot):
    """Legger til VestskTipping-cog i Discord-botten."""
    await bot.add_cog(VestskTipping(bot))
