import os
import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pytz
import re
import requests
from gspread_formatting import cellFormat, format_cell_range, color, batch_updater
import time
from keep_alive import keep_alive
keep_alive()

# === Team data ===
teams = {
    "New England Patriots": {"emoji": "<:ne:752546616207999056>", "short": "Patriots"},
    "Buffalo Bills": {"emoji": "<:buf:752546615876780083>", "short": "Bills"},
    "New York Jets": {"emoji": "<:nyj:1283701476002103322>", "short": "Jets"},
    "Miami Dolphins": {"emoji": "<:mia:752546616220713071>", "short": "Dolphins"},
    "Baltimore Ravens": {"emoji": "<:bal:752546616098947192>", "short": "Ravens"},
    "Cincinnati Bengals": {"emoji": "<:cin:752546615893426207>", "short": "Bengals"},
    "Cleveland Browns": {"emoji": "<:cle:752546616648663130>", "short": "Browns"},
    "Pittsburgh Steelers": {"emoji": "<:pit:752546616287953027>", "short": "Steelers"},
    "Houston Texans": {"emoji": "<:hou:752546616526897243>", "short": "Texans"},
    "Indianapolis Colts": {"emoji": "<:ind:752546615998414930>", "short": "Colts"},
    "Jacksonville Jaguars": {"emoji": "<:jax:752546616216518727>", "short": "Jaguars"},
    "Tennessee Titans": {"emoji": "<:ten:752546616732287056>", "short": "Titans"},
    "Denver Broncos": {"emoji": "<:den:752546616136826948>", "short": "Broncos"},
    "Kansas City Chiefs": {"emoji": "<:kc:752546616065392711>", "short": "Chiefs"},
    "Las Vegas Raiders": {"emoji": "<:lv:752546616233295882>", "short": "Raiders"},
    "Los Angeles Chargers": {"emoji": "<:lac:752546615818190919>", "short": "Chargers"},
    "Dallas Cowboys": {"emoji": "<:dal:752546616124112896>", "short": "Cowboys"},
    "New York Giants": {"emoji": "<:nyg:752546615826317393>", "short": "Giants"},
    "Philadelphia Eagles": {"emoji": "<:phi:752546616329633792>", "short": "Eagles"},
    "Washington Commanders": {"emoji": "<:was:1022586486845096016>", "short": "Commanders"},
    "Chicago Bears": {"emoji": "<:chi:1283701338034671689>", "short": "Bears"},
    "Detroit Lions": {"emoji": "<:det:752546616216518747>", "short": "Lions"},
    "Green Bay Packers": {"emoji": "<:gb:752546616149278840>", "short": "Packers"},
    "Minnesota Vikings": {"emoji": "<:min:752546616023449751>", "short": "Vikings"},
    "Atlanta Falcons": {"emoji": "<:atl:752546616182833243>", "short": "Falcons"},
    "Carolina Panthers": {"emoji": "<:car:752546616275239003>", "short": "Panthers"},
    "New Orleans Saints": {"emoji": "<:no:752546616250204321>", "short": "Saints"},
    "Tampa Bay Buccaneers": {"emoji": "<:tb:752546616262787132>", "short": "Buccaneers"},
    "Arizona Cardinals": {"emoji": "<:ari:752546616598069420>", "short": "Cardinals"},
    "Los Angeles Rams": {"emoji": "<:lar:885711442723090502>", "short": "Rams"},
    "San Francisco 49ers": {"emoji": "<:sf:752546616266981418>", "short": "49ers"},
    "Seattle Seahawks": {"emoji": "<:sea:752546616090689627>", "short": "Seahawks"},
}

# === Mapping ===
# Uavgjort-emoji
DRAW_EMOJI = "<:gulfrglaff:800175714909028393>"

# Emoji-mapping: short-name → emoji
team_emojis = {v['short']: v['emoji'] for v in teams.values()}

# Short-name lookup for Sheets og API
team_location = {v['short']: v['short'] for v in teams.values()}

# === Last miljøvariabler ===
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

# === Google Sheets oppsett ===
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Vestsk Tipping").sheet1

# === Admin ===
ADMIN_IDS = tuple(os.getenv("ADMIN_IDS", "").split(","))

def admin_only():
    return commands.check(lambda ctx: str(ctx.author.id) in ADMIN_IDS)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send("Kanskje hvis du spør veldig pent så kan du få lov te å bruke botten.")

# === Helpers ===
def get_players(sheet):
    id_row = sheet.row_values(2)
    return {id_row[i]: i for i in range(len(id_row))}

def msg_to_kampkode(msg):
    clean_text = re.sub(r'<:.+?:\d+>', '', msg.content).strip()
    comps = clean_text.split("@")
    if len(comps) == 2:
        away = teams.get(comps[0].strip(), {"short": comps[0].strip()})["short"]
        home = teams.get(comps[1].strip(), {"short": comps[1].strip()})["short"]
        return f"{away}@{home}"
    return clean_text

# === Events ===
@bot.event
async def on_ready():
    print(f"✅ Botten er logget inn som {bot.user}")

# === Commands ===
@bot.command()
@admin_only()
async def kamper(ctx, uke: int = None):
    """Henter NFL-kamper for en gitt uke (kun admin)"""
    import requests
    season = datetime.now().year
    url = (f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={uke}&season={season}&seasontype=2"
           if uke else "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
    data = requests.get(url).json()
    events = data.get("events", [])
    if not events:
        await ctx.send("Fant ingen kamper")
        return

    events.sort(key=lambda ev: ev.get("date"))
    norsk_tz = pytz.timezone("Europe/Oslo")

    for ev in events:
        comps = ev["competitions"][0]["competitors"]
        home = next(c for c in comps if c["homeAway"] == "home")
        away = next(c for c in comps if c["homeAway"] == "away")
        home_team = home["team"]["displayName"]
        away_team = away["team"]["displayName"]
        await ctx.send(f"{teams.get(away_team, {'emoji':''})['emoji']} {away_team} @ {home_team} {teams.get(home_team, {'emoji':''})['emoji']}")

@bot.command(name="eksporter")
@admin_only()
async def export(ctx, uke: int = None):
    """Eksporter reaksjoner til Sheet i grid-format (kun admin)"""
    channel = ctx.channel

    # Hent header og ID-rad
    id_row = sheet.row_values(2)
    players = {id_row[i]: i for i in range(len(id_row))}
    num_players = len(players)

    # Startdato for uken (onsdag)
    norsk_tz = pytz.timezone("Europe/Oslo")
    now = datetime.now(norsk_tz)
    days_since_wed = (now.weekday() - 2) % 7
    start_of_week = now - timedelta(days=days_since_wed)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    # Emoji til team short-navn
    emoji_to_team_short = {v: k for k, v in team_emojis.items()}

    # Hent meldinger fra botten
    messages = []
    async for msg in channel.history(limit=100, after=start_of_week):
        if msg.author == bot.user and "@" in msg.content:
            messages.append(msg)
    messages.sort(key=lambda m: m.created_at)

    print(f"[EXPORT] Fant {len(messages)} meldinger å eksportere")

    # Bygg verdier
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
                if user != bot.user and discord_id in players:
                    col_idx = players[discord_id]
                    emoji_str = str(reaction.emoji)
                    if emoji_str == DRAW_EMOJI:
                        row[col_idx] = "Uavgjort"
                    else:
                        row[col_idx] = emoji_to_team_short.get(emoji_str, "")
        values.append(row)

    print(f"[EXPORT] Ferdig med bygging av verdier: {values[:5]}{'...' if len(values) > 5 else ''}")

    # Finn start-rad for nye kampkoder
    all_rows_colA = sheet.col_values(1)
    last_data_row = len(all_rows_colA)
    start_row = last_data_row + 2  # én blank rad mellom forrige sesongpoeng og nye kamper

    # Batch-update
    if values:
        cell_range = sheet.range(start_row, 1, start_row + len(values) - 1, 1 + num_players)
        flat_values = [cell for row in values for cell in row]

        for cell_obj, val in zip(cell_range, flat_values):
            cell_obj.value = val

        sheet.update_cells(cell_range)
        await ctx.send("<:brady:754803554102935692> Eksportski komplettski <:brady:754803554102935692>")
    else:
        await ctx.send("Ingen verdier å oppdatere")

# === Resultater ===
@bot.command(name="resultater")
@admin_only()
async def resultater(ctx, uke: int = None):
    """Sjekker tippinger, farger riktig/feil/manglende, summerer ukes- og sesongpoeng"""
    import time

    norsk_tz = pytz.timezone("Europe/Oslo")
    season = datetime.now(norsk_tz).year

    # Hent kamper fra API
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    if uke:
        url += f"?week={uke}&season={season}&seasontype=2"

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

        # DEBUG: vis API-resultater
        print(f"[DEBUG API] {kampkode}: vinner='{kamp_resultater[kampkode]}' (Home {home_score}-{away_score} Away)")

    # Hent spillere (ignorer første kolonne, som er "Discord ID")
    id_row = sheet.row_values(2)[1:]
    players = {id_row[i]: i+2 for i in range(len(id_row))}  # B=2
    num_players = len(players)
    print(f"[RESULTATER] Spillere ({num_players}): {list(players.keys())}")

    # Hent kampene fra Sheet (rad 3+)
    sheet_rows = sheet.get_all_values()[2:]
    sheet_kamper = []
    row_mapping = {}
    for i, row in enumerate(sheet_rows, start=3):
        kampkode = row[0].strip()
        if kampkode:
            sheet_kamper.append(kampkode)
            row_mapping[len(sheet_kamper)-1] = i

    print(f"[RESULTATER] Kamper som skal oppdateres: {len(sheet_kamper)}")

    uke_total_row = max(row_mapping.values()) + 1
    sesong_total_row = uke_total_row + 1

    # Formatering
    green = cellFormat(backgroundColor=color(0,1,0))
    red = cellFormat(backgroundColor=color(1,0,0))
    yellow = cellFormat(backgroundColor=color(1,1,0))

    uke_poeng = [0] * num_players

    for idx, kampkode in enumerate(sheet_kamper):
        row_idx = row_mapping[idx]
        riktig_vinner = kamp_resultater.get(kampkode)

        for col_idx, discord_id in enumerate(players.keys(), start=2):
            cell_value = sheet.cell(row_idx, col_idx).value

            # Lag liste med alle gyldige svar for riktig vinner
            gyldige_svar = []
            if riktig_vinner != "Uavgjort":
                for full, data in teams.items():
                    if data["short"].lower() == riktig_vinner.lower():
                        gyldige_svar.append(data["short"])
            else:
                gyldige_svar.append("Uavgjort")


            # DEBUG
            print(f"[DEBUG] Rad {row_idx} Kol {col_idx}: Sheet='{cell_value}' | API='{riktig_vinner}' | Gyldige='{gyldige_svar}'")

            # Bestem farge
            if not cell_value:
                fmt = yellow
            elif cell_value in gyldige_svar:
                fmt = green
                uke_poeng[col_idx-2] += 1
            else:
                fmt = red

            # Oppdater verdi og farge
            try:
                sheet.update_cell(row_idx, col_idx, cell_value if cell_value else "")
                col_letter = chr(64 + col_idx)  # A=1, B=2, osv
                format_cell_range(sheet, f"{col_letter}{row_idx}", fmt)
            except Exception as e:
                print(f"[RESULTATER] FEIL ved celle {row_idx},{col_idx}: {e}")

            time.sleep(1.2)

        print(f"[RESULTATER] Ferdig med kamp {idx+1}/{len(sheet_kamper)}")

    # Skriv ukespoeng
    for idx, poeng in enumerate(uke_poeng, start=2):
        try:
            sheet.update_cell(uke_total_row, idx, poeng)
            time.sleep(1.2)
        except Exception as e:
            print(f"[RESULTATER] FEIL ved ukespoeng, kolonne {idx}: {e}")

    # Skriv sesongpoeng
    for idx, discord_id in enumerate(players.keys(), start=2):
        try:
            prev = sheet.cell(sesong_total_row, idx).value
            prev_val = int(prev) if prev and prev.isdigit() else 0
            sheet.update_cell(sesong_total_row, idx, prev_val + uke_poeng[idx-2])
            time.sleep(1.2)
        except Exception as e:
            print(f"[RESULTATER] FEIL ved sesongpoeng, kolonne {idx}: {e}")

    await ctx.send(f"✅ Resultater for uke {uke if uke else 'nåværende'} er oppdatert i Sheets.")

@bot.command()
async def ping(ctx):
    """Tester om botten svarer"""
    await ctx.send("Pong! ✅")

bot.run(TOKEN)
