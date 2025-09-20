from discord.ext import commands
from discord.ext.commands import CheckFailure
import aiohttp
from datetime import datetime, timedelta
import pytz
import re
import asyncio
import os

from data.teams import teams, team_emojis, team_location, DRAW_EMOJI
from cogs.sheets import get_sheet, green_format, red_format, yellow_format
from core.errors import (
    APIFetchError,
    NoEventsFoundError,
    ExportError,
    ResultaterError,
)

CHANNEL_ID = 752538512250765314 

# === Hjelpefunksjon for å parse ESPN-datoer ===
def parse_espn_date(datestr: str) -> datetime:
    # Bytt Z (UTC) til +00:00 så fromisoformat kan tolke det
    return datetime.fromisoformat(datestr.replace("Z", "+00:00"))

# === Ekstern dekorator for admin-only kommandoer ===
def admin_only():
    ADMIN_IDS = {x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
    return commands.check(lambda ctx: str(ctx.author.id) in ADMIN_IDS)

class VestskTipping(commands.Cog):
    """Kommandoer for Vestsk Tipping"""

    def __init__(self, bot):
        self.bot = bot
        self.norsk_tz = pytz.timezone("Europe/Oslo")
        self.last_reminder_week = None
        self.last_reminder_sunday = None
        self.reminder_task = self.bot.loop.create_task(self.reminder_scheduler())

    def get_players(self, sheet):
        """Returnerer mapping: Discord ID → kolonne"""
        id_row = sheet.row_values(2)
        # Hopp over kolonne A (index 0), start fra B (index 1)
        players = {id_row[i]: i for i in range(1, len(id_row)) if id_row[i]}
        print(f"[DEBUG] get_players: {players}")
        return players

    def cog_unload(self):
        self.reminder_task.cancel()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, CheckFailure):
            await ctx.send("Kanskje hvis du spør veldig pent så kan du få lov te å bruke botten.")

    # === kamper ===
    @commands.command()
    @admin_only()
    async def kamper(self, ctx, uke: int = None):
        await self._kamper_impl(ctx, uke)

    async def _kamper_impl(self, ctx, uke: int = None):
        season = datetime.now().year
        url = (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={uke}"
               if uke else "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
        except Exception as e:
            raise APIFetchError(url, e) from e

        events = data.get("events", [])
        if not events:
            raise NoEventsFoundError(uke)

        events.sort(key=lambda ev: ev.get("date"))
        for ev in events:
            comps = ev["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            home_team = home["team"]["displayName"]
            away_team = away["team"]["displayName"]
            await ctx.send(f"{teams.get(away_team, {'emoji':''})['emoji']} {away_team} @ "
               f"{home_team} {teams.get(home_team, {'emoji':''})['emoji']}")

    async def reminder_scheduler(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)

        while True:
            now = datetime.now(self.norsk_tz)
            weekday = now.weekday()

            try:
                # === Torsdagspåminnelse ===
                if weekday == 3:
                    week_num = now.isocalendar()[1]
                    reminder_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
                    if now < reminder_time:
                        sleep_seconds = (reminder_time - now).total_seconds()
                        await asyncio.sleep(sleep_seconds)

                        if self.last_reminder_week is None or self.last_reminder_week != week_num:
                            await channel.send(
                                "@everyone RAUÅ I GIR, ukå begynne snart "
                                "så sjekk <#795485646545748058>!"
                            )
                            self.last_reminder_week = week_num
                            print(f"Torsdagspåminnelse sendt for uke {week_num} ({reminder_time})")

                        tomorrow = reminder_time + timedelta(days=1)
                        await asyncio.sleep((tomorrow - datetime.now(self.norsk_tz)).total_seconds())  # noqa: E501
                        continue

                # === Søndagspåminnelse ===
                if weekday == 6:
                    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url, timeout=10) as resp:
                                data = await resp.json()
                    except Exception as e:
                        print(
                            f"[ERROR] Kunne ikke hente data fra ESPN API: {e}. "
                            "Prøver igjen om 5 min."
                        )
                        await asyncio.sleep(300)  # backoff før retry
                        continue

                    events = data.get("events", [])
                    sunday_events = [
                        ev for ev in events
                        if parse_espn_date(ev["date"]).astimezone(self.norsk_tz).weekday() == 6
                    ]

                    if sunday_events:
                        sunday_events.sort(key=lambda ev: ev.get("date"))
                        first_sunday_game = parse_espn_date(sunday_events[0]["date"]).astimezone(self.norsk_tz)  # noqa: E501
                        reminder_time = first_sunday_game - timedelta(minutes=60)

                        if now < reminder_time:
                            sleep_seconds = (reminder_time - now).total_seconds()
                            await asyncio.sleep(sleep_seconds)

                            if self.last_reminder_sunday is None or self.last_reminder_sunday != first_sunday_game.date():  # noqa: E501
                                await channel.send(
                                    f"@everyone Early window snart, husk <#795485646545748058>: "
                                    f"{self._format_event(sunday_events[0])}"
                                )
                                self.last_reminder_sunday = first_sunday_game.date()
                                print(
                                    f"[INFO] Søndagspåminnelse sendt for {first_sunday_game.date()}"
                                    f"({reminder_time})"
                                )

                            tomorrow = reminder_time + timedelta(days=1)
                            await asyncio.sleep((tomorrow - datetime.now(self.norsk_tz)).total_seconds())  # noqa: E501
                            continue

                # === Beregn tid til neste vindu ===
                next_thursday = now + timedelta(days=(3 - weekday) % 7)
                next_thursday = next_thursday.replace(hour=18, minute=0, second=0, microsecond=0)
                if next_thursday <= now:
                    next_thursday += timedelta(days=7)

                next_sunday = now + timedelta(days=(6 - weekday) % 7)
                next_sunday = next_sunday.replace(hour=8, minute=0, second=0, microsecond=0)
                if next_sunday <= now:
                    next_sunday += timedelta(days=7)

                sleep_until = min(next_thursday, next_sunday)
                sleep_seconds = (sleep_until - now).total_seconds()
                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                print(f"[ERROR] Feil i reminder_scheduler: {e}. Prøver igjen om 5 min.")
                await asyncio.sleep(300)  # generell backoff før retry

    def _format_event(self, ev):
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
    async def export(self, ctx, uke: int = None):
        await self._export_impl(ctx, uke)

    async def _export_impl(self, ctx, uke: int = None):
        sheet = await asyncio.to_thread(get_sheet, "Vestsk Tipping")
        channel = ctx.channel

        players = self.get_players(sheet)
        num_players = len(players)

        norsk_tz = pytz.timezone("Europe/Oslo")
        now = datetime.now(norsk_tz)
        days_since_tue = (now.weekday() - 1) % 7
        start_of_week = now - timedelta(days=days_since_tue)
        start_of_week = start_of_week.replace(hour=10, minute=0, second=0, microsecond=0)

        emoji_to_team_short = {v: k for k, v in team_emojis.items()}

        messages = []
        async for msg in channel.history(limit=100, after=start_of_week):
            if msg.author == self.bot.user and "@" in msg.content:
                messages.append(msg)
        messages.sort(key=lambda m: m.created_at)

        if not messages:
            raise ExportError(f"Ingen meldinger funnet å eksportere etter {start_of_week}")

        values = []
        for msg in messages:
            clean_text = re.sub(r'<:.+?:\d+>', '', msg.content).strip()
            comps = clean_text.split("@")
            if len(comps) == 2:
                away_team_full = comps[0].strip()
                home_team_full = comps[1].strip()
                away = team_location.get(away_team_full, away_team_full.split()[-1])
                home = team_location.get(home_team_full, home_team_full.split()[-1])
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
                            row[col_idx] = emoji_to_team_short.get(emoji_str, "")
            values.append(row)

        all_rows_colA = await asyncio.to_thread(sheet.col_values, 1)
        last_data_row = len(all_rows_colA)
        start_row = last_data_row + 2

        if values:
            try:
                cell_range = await asyncio.to_thread(
                    sheet.range,
                    start_row,
                    1,
                    start_row + len(values) - 1,
                    1 + num_players,
                )
                flat_values = [cell for row in values for cell in row]
                for cell_obj, val in zip(cell_range, flat_values):
                    cell_obj.value = val
                await asyncio.to_thread(sheet.update_cells, cell_range)
            except Exception as e:
                raise ExportError(f"Feil ved eksport til sheet '{sheet.title}': {e}") from e

            await ctx.send("Kampdata eksportert til Sheets.")
        else:
            await ctx.send("Ingen verdier å oppdatere")

    # === resultater ===
    @commands.command(name="resultater")
    @admin_only()
    async def resultater(self, ctx, uke: int = None):

        print(f"[DEBUG] Kommando !resultater kjørt for uke={uke}")
        await self._resultater_impl(ctx, uke)

    async def _resultater_impl(self, ctx, uke: int = None):
        try:
            sheet = await asyncio.to_thread(get_sheet, "Vestsk Tipping")
            if not sheet:
                raise ResultaterError("Kunne ikke hente worksheet 'Vestsk Tipping'")
        except Exception as e:
            raise ResultaterError(f"Feil ved henting av sheet: {e}") from e

        print(f"[DEBUG] Henter sheet: {sheet.title if sheet else 'None'}")

        norsk_tz = pytz.timezone("Europe/Oslo")
        season = datetime.now(norsk_tz).year
        print(f"[DEBUG] Sesong: {season}")

        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        if uke:
            url += f"?dates={season}&seasontype=2&week={uke}"
        print(f"[DEBUG] Henter URL: {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
        except Exception as e:
            raise APIFetchError(url, e)

        events = data.get("events", [])
        print(f"[DEBUG] Antall events hentet: {len(events)}")

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
                    f"Feil ved parsing av kampdata for {ev.get('id', 'ukjent')}"
                ) from e

            if home_score > away_score:
                kamp_resultater[kampkode] = home_team
            elif away_score > home_score:
                kamp_resultater[kampkode] = away_team
            else:
                kamp_resultater[kampkode] = "Uavgjort"
        print(f"[DEBUG] Kampresultater: {kamp_resultater}")

        players = self.get_players(sheet)
        print(f"[DEBUG] Spillere funnet: {players}")
        num_players = len(players)

        # Hent alle relevante rader og kolonner i én batch
        sheet_rows = (await asyncio.to_thread(sheet.get_all_values))[2:]
        sheet_kamper = []
        row_mapping = {}
        for i, row in enumerate(sheet_rows, start=3):
            kampkode = row[0].strip()
            if kampkode:
                sheet_kamper.append(kampkode)
                row_mapping[len(sheet_kamper)-1] = i
        print(f"[DEBUG] Kamper i sheet: {sheet_kamper}")
        print(f"[DEBUG] Row mapping: {row_mapping}")

        uke_total_row = max(row_mapping.values(), default=3) + 1
        sesong_total_row = uke_total_row + 1
        print(f"[DEBUG] Uke total rad: {uke_total_row}, sesong total rad: {sesong_total_row}")

        green = green_format()
        red = red_format()
        yellow = yellow_format()

        uke_poeng = [0] * num_players

        # Kolonneindekser: discord_id → col_idx (start på 2, men batch-read starter på 2)
        player_ids = list(players.keys())
        start_col = 2
        end_col = start_col + num_players - 1
        start_row = min(row_mapping.values(), default=3)
        end_row = max(row_mapping.values(), default=3)

        # Hent alle celler for kampdata i én batch
        kamp_cell_range = await asyncio.to_thread(
            sheet.range,
            start_row,
            start_col,
            end_row,
            end_col
        )
        # Lag mapping: (row_idx, col_idx) -> cell_obj
        cell_map = {(cell.row, cell.col): cell for cell in kamp_cell_range}

        cell_updates = []
        format_updates = []

        for idx, kampkode in enumerate(sheet_kamper):
            row_idx = row_mapping[idx]
            riktig_vinner = kamp_resultater.get(kampkode)
            print(f"[DEBUG] Prosesserer kamp {kampkode} (riktig vinner: {riktig_vinner})")

            for pidx, discord_id in enumerate(player_ids):
                col_idx = start_col + pidx
                cell_obj = cell_map.get((row_idx, col_idx))
                if cell_obj is None:
                    continue
                cell_value = cell_obj.value
                gyldige_svar = (
                    [riktig_vinner] if riktig_vinner == "Uavgjort" 
                    else [
                        v["short"] 
                        for v in teams.values() 
                        if v["short"].lower() == riktig_vinner.lower()
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

        print(f"[DEBUG] Ukespoeng: {uke_poeng}")

        # Ukespoeng og sesongpoeng batch-read og batch-write
        uke_poeng_cells = await asyncio.to_thread(
            sheet.range,
            uke_total_row,
            start_col,
            uke_total_row,
            end_col
        )
        for pidx, cell_obj in enumerate(uke_poeng_cells):
            poeng = uke_poeng[pidx]
            if str(cell_obj.value) != str(poeng):
                cell_obj.value = poeng
                cell_updates.append(cell_obj)

        # Sesongpoeng: rad sesong_total_row, kolonner start_col -> end_col
        sesong_poeng_cells = await asyncio.to_thread(
            sheet.range,
            sesong_total_row,
            start_col,
            sesong_total_row,
            end_col
        )
        for pidx, cell_obj in enumerate(sesong_poeng_cells):
            prev = cell_obj.value
            prev_val = int(prev) if prev and str(prev).isdigit() else 0
            new_val = prev_val + uke_poeng[pidx]
            if str(cell_obj.value) != str(new_val):
                cell_obj.value = new_val
                cell_updates.append(cell_obj)

        # === Batch update alle celler ===
        if cell_updates:
            try:
                await asyncio.to_thread(sheet.update_cells, cell_updates)
            except Exception as e:
                raise ResultaterError(f"Feil ved batch-oppdatering av celler: {e}") from e

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
                    "fields": "userEnteredFormat.backgroundColor,userEnteredFormat.textFormat"
                }
            })

        if requests:
            try:
                await asyncio.to_thread(
                    sheet.spreadsheet.batch_update,
                    {"requests": requests}
                )
            except Exception as e:
                raise ResultaterError(f"Feil ved batch-formattering av celler: {e}")

        print("[DEBUG] Ferdig med oppdatering av sheet, sender Discord-melding")

        # Discord-melding
        header_row = (await asyncio.to_thread(sheet.row_values, 1))[1:1+num_players]
        discord_msg = []
        for idx, name in enumerate(header_row, start=2):
            uke_p = uke_poeng[idx-2]
            sesong_p_cell = (await asyncio.to_thread(sheet.cell, sesong_total_row, idx)).value
            sesong_p = int(sesong_p_cell) if sesong_p_cell and str(sesong_p_cell).isdigit() else 0
            discord_msg.append((name, uke_p, sesong_p))

        discord_msg.sort(key=lambda x: x[1], reverse=True)
        lines = [f"`Poeng for uke {uke if uke else 'nåværende'}:"]
        for i, (name, uke_p, _) in enumerate(discord_msg, start=1):
            lines.append(f"{i}. {name:<10} {uke_p}")

        lines.append("")
        lines.append("Sesongtotal:")
        discord_msg.sort(key=lambda x: x[2], reverse=True)
        for i, (name, _, sesong_p) in enumerate(discord_msg, start=1):
            lines.append(f"{i}. {name:<10} {sesong_p}")

        lines.append("`")
        await ctx.send("\n".join(lines))
        await ctx.send(f"✅ Resultater for uke {uke if uke else 'nåværende'} er oppdatert.")

# --- Setup ---
async def setup(bot):
    await bot.add_cog(VestskTipping(bot))
