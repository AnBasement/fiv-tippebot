import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure
import requests
from datetime import datetime, timedelta
import pytz
import re
import asyncio
import os

from data.teams import teams, team_emojis, team_location, DRAW_EMOJI
from cogs.sheets import get_sheet, get_players, green_format, red_format, yellow_format, format_cell

class VestskTipping(commands.Cog):
    """Kommandoer for Vestsk tippelek"""

    def __init__(self, bot):
        self.bot = bot
        self.ADMIN_IDS = tuple(os.getenv("ADMIN_IDS", "").split(","))

    def admin_only(self):
        return commands.check(lambda ctx: str(ctx.author.id) in self.ADMIN_IDS)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, CheckFailure):
            await ctx.send("Kanskje hvis du spør veldig pent så kan du få lov te å bruke botten.")

    @commands.command()
    @commands.check(lambda ctx: str(ctx.author.id) in os.getenv("ADMIN_IDS", "").split(","))
    async def kamper(self, ctx, uke: int = None):
        """Henter NFL-kamper for en gitt uke (kun admin)"""
        season = datetime.now().year
        url = (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={uke}"
               if uke else "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
        data = requests.get(url).json()
        events = data.get("events", [])
        if not events:
            await ctx.send("Fant ingen kamper")
            return

        events.sort(key=lambda ev: ev.get("date"))
        for ev in events:
            comps = ev["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            home_team = home["team"]["displayName"]
            away_team = away["team"]["displayName"]
            await ctx.send(f"{teams.get(away_team, {'emoji':''})['emoji']} {away_team} @ {home_team} {teams.get(home_team, {'emoji':''})['emoji']}")

    @commands.command(name="eksporter")
    @commands.check(lambda ctx: str(ctx.author.id) in os.getenv("ADMIN_IDS", "").split(","))
    async def export(self, ctx, uke: int = None):
        """Eksporter reaksjoner til Sheet i grid-format (kun admin)"""
        sheet = get_sheet()
        channel = ctx.channel

        id_row = sheet.row_values(2)
        players = {id_row[i]: i for i in range(len(id_row))}
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

        all_rows_colA = sheet.col_values(1)
        last_data_row = len(all_rows_colA)
        start_row = last_data_row + 2

        if values:
            cell_range = sheet.range(start_row, 1, start_row + len(values) - 1, 1 + num_players)
            flat_values = [cell for row in values for cell in row]
            for cell_obj, val in zip(cell_range, flat_values):
                cell_obj.value = val
            sheet.update_cells(cell_range)
            await ctx.send("<:brady:754803554102935692> Eksportski komplettski <:brady:754803554102935692>")
        else:
            await ctx.send("Ingen verdier å oppdatere")

    @commands.command(name="resultater")
    @commands.check(lambda ctx: str(ctx.author.id) in os.getenv("ADMIN_IDS", "").split(","))
    async def resultater(self, ctx, uke: int = None):
        """Sjekker tippinger og oppdaterer Sheet og Discord"""
        sheet = get_sheet()
        norsk_tz = pytz.timezone("Europe/Oslo")
        season = datetime.now(norsk_tz).year

        # Hent kamper fra API
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        if uke:
            url += f"?dates={season}&seasontype=2&week={uke}"

        data = requests.get(url).json()
        events = data.get("events", [])
        if not events:
            await ctx.send("Fant ingen kamper")
            return

        # Lag kampkode -> vinner mapping
        kamp_resultater = {}
        for ev in events:
            comps = ev["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            home_team = team_location.get(home["team"]["displayName"], home["team"]["displayName"].split()[-1])
            away_team = team_location.get(away["team"]["displayName"], away["team"]["displayName"].split()[-1])
            kampkode = f"{away_team}@{home_team}"

            home_score = int(home["score"])
            away_score = int(away["score"])
            if home_score > away_score:
                kamp_resultater[kampkode] = home_team
            elif away_score > home_score:
                kamp_resultater[kampkode] = away_team
            else:
                kamp_resultater[kampkode] = "Uavgjort"

        id_row = sheet.row_values(2)[1:]
        players = {id_row[i]: i+2 for i in range(len(id_row))}  # B=2
        num_players = len(players)

        sheet_rows = sheet.get_all_values()[2:]
        sheet_kamper = []
        row_mapping = {}
        for i, row in enumerate(sheet_rows, start=3):
            kampkode = row[0].strip()
            if kampkode:
                sheet_kamper.append(kampkode)
                row_mapping[len(sheet_kamper)-1] = i

        uke_total_row = max(row_mapping.values()) + 1
        sesong_total_row = uke_total_row + 1

        green = green_format()
        red = red_format()
        yellow = yellow_format()

        uke_poeng = [0] * num_players

        for idx, kampkode in enumerate(sheet_kamper):
            row_idx = row_mapping[idx]
            riktig_vinner = kamp_resultater.get(kampkode)

            for col_idx, discord_id in enumerate(players.keys(), start=2):
                cell_value = sheet.cell(row_idx, col_idx).value
                gyldige_svar = [riktig_vinner] if riktig_vinner == "Uavgjort" else [v["short"] for v in teams.values() if v["short"].lower() == riktig_vinner.lower()]

                if not cell_value:
                    fmt = yellow
                elif cell_value in gyldige_svar:
                    fmt = green
                    uke_poeng[col_idx-2] += 1
                else:
                    fmt = red

                try:
                    sheet.update_cell(row_idx, col_idx, cell_value if cell_value else "")
                    format_cell(sheet, row_idx, col_idx, fmt)
                except Exception as e:
                    print(f"[RESULTATER] FEIL ved celle {row_idx},{col_idx}: {e}")

                await asyncio.sleep(1.5)

        # Skriv ukespoeng
        for idx, poeng in enumerate(uke_poeng, start=2):
            try:
                sheet.update_cell(uke_total_row, idx, poeng)
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"[RESULTATER] FEIL ved ukespoeng, kolonne {idx}: {e}")

        # Skriv sesongpoeng
        for idx, discord_id in enumerate(players.keys(), start=2):
            try:
                prev = sheet.cell(sesong_total_row, idx).value
                prev_val = int(prev) if prev and prev.isdigit() else 0
                sheet.update_cell(sesong_total_row, idx, prev_val + uke_poeng[idx-2])
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"[RESULTATER] FEIL ved sesongpoeng, kolonne {idx}: {e}")

        # Lag Discord-oversikt
        header_row = sheet.row_values(1)[1:1+num_players]
        discord_msg = []
        for idx, name in enumerate(header_row, start=2):
            uke_p = uke_poeng[idx-2]
            sesong_p_cell = sheet.cell(sesong_total_row, idx).value
            sesong_p = int(sesong_p_cell) if sesong_p_cell and sesong_p_cell.isdigit() else 0
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

async def setup(bot):
    await bot.add_cog(VestskTipping(bot))
