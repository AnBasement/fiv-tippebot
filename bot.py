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
from gspread_formatting import cellFormat, format_cell_range, color

# === Team data ===
teams = {
    "New England Patriots": {"emoji": "<:ne:752546616207999056>", "short": "New England"},
    "Buffalo Bills": {"emoji": "<:buf:752546615876780083>", "short": "Buffalo"},
    "New York Jets": {"emoji": "<:nyj:1283701476002103322>", "short": "New York"},
    "Miami Dolphins": {"emoji": "<:mia:752546616220713071>", "short": "Miami"},
    "Baltimore Ravens": {"emoji": "<:bal:752546616098947192>", "short": "Baltimore"},
    "Cincinnati Bengals": {"emoji": "<:cin:752546615893426207>", "short": "Cincinnati"},
    "Cleveland Browns": {"emoji": "<:cle:752546616648663130>", "short": "Cleveland"},
    "Pittsburgh Steelers": {"emoji": "<:pit:752546616287953027>", "short": "Pittsburgh"},
    "Houston Texans": {"emoji": "<:hou:752546616526897243>", "short": "Houston"},
    "Indianapolis Colts": {"emoji": "<:ind:752546615998414930>", "short": "Indianapolis"},
    "Jacksonville Jaguars": {"emoji": "<:jax:752546616216518727>", "short": "Jacksonville"},
    "Tennessee Titans": {"emoji": "<:ten:752546616732287056>", "short": "Tennessee"},
    "Denver Broncos": {"emoji": "<:den:752546616136826948>", "short": "Denver"},
    "Kansas City Chiefs": {"emoji": "<:kc:752546616065392711>", "short": "Kansas City"},
    "Las Vegas Raiders": {"emoji": "<:lv:752546616233295882>", "short": "Las Vegas"},
    "Los Angeles Chargers": {"emoji": "<:lac:752546615818190919>", "short": "Los Angeles"},
    "Dallas Cowboys": {"emoji": "<:dal:752546616124112896>", "short": "Dallas"},
    "New York Giants": {"emoji": "<:nyg:752546615826317393>", "short": "New York"},
    "Philadelphia Eagles": {"emoji": "<:phi:752546616329633792>", "short": "Philadelphia"},
    "Washington Commanders": {"emoji": "<:was:1022586486845096016>", "short": "Washington"},
    "Chicago Bears": {"emoji": "<:chi:1283701338034671689>", "short": "Chicago"},
    "Detroit Lions": {"emoji": "<:det:752546616216518747>", "short": "Detroit"},
    "Green Bay Packers": {"emoji": "<:gb:752546616149278840>", "short": "Green Bay"},
    "Minnesota Vikings": {"emoji": "<:min:752546616023449751>", "short": "Minnesota"},
    "Atlanta Falcons": {"emoji": "<:atl:752546616182833243>", "short": "Atlanta"},
    "Carolina Panthers": {"emoji": "<:car:752546616275239003>", "short": "Carolina"},
    "New Orleans Saints": {"emoji": "<:no:752546616250204321>", "short": "New Orleans"},
    "Tampa Bay Buccaneers": {"emoji": "<:tb:752546616262787132>", "short": "Tampa Bay"},
    "Arizona Cardinals": {"emoji": "<:ari:752546616598069420>", "short": "Arizona"},
    "Los Angeles Rams": {"emoji": "<:lar:885711442723090502>", "short": "Los Angeles"},
    "San Francisco 49ers": {"emoji": "<:sf:752546616266981418>", "short": "San Francisco"},
    "Seattle Seahawks": {"emoji": "<:sea:752546616090689627>", "short": "Seattle"},
}

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
    header_row = sheet.row_values(1)
    id_row = sheet.row_values(2)
    players = {id_row[i]: i for i in range(len(id_row))}
    num_players = len(players)

    # Startdato for uken (onsdag)
    norsk_tz = pytz.timezone("Europe/Oslo")
    now = datetime.now(norsk_tz)
    days_since_wed = (now.weekday() - 2) % 7
    start_of_week = now - timedelta(days=days_since_wed)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    # Emoji til team-navn
    emoji_to_team = {v: k for k, v in team_emojis.items()}

    # Hent meldinger fra botten
    messages = []
    async for msg in channel.history(limit=100, after=start_of_week):
        if msg.author == bot.user and "@" in msg.content:
            messages.append(msg)
    messages.sort(key=lambda m: m.created_at)

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
                if user == bot.user:
                    continue
                discord_id = str(user.id)
                if discord_id in players:
                    col_idx = players[discord_id]
                    emoji_str = str(reaction.emoji)
                    row[col_idx] = emoji_to_team.get(emoji_str, emoji_str)
        values.append(row)

    # Finn start-rad for nye kampkoder
    all_rows_colA = sheet.col_values(1)
    last_data_row = len(all_rows_colA)
    start_row = last_data_row + 2  # én blank rad mellom forrige sesongpoeng og nye kamper

    if values:
        sheet.update(f"A{start_row}", values=values)

    await ctx.send("<:brady:754803554102935692> Eksportski komplettski <:brady:754803554102935692>")

# === Resultater ===
@bot.command(name="resultater")
@admin_only()
async def resultater(ctx, uke: int = None):
    """Sjekker tippinger, farger riktig/feil/manglende, summerer ukes- og sesongpoeng"""
    norsk_tz = pytz.timezone("Europe/Oslo")
    season = datetime.now().year

    # Hent kamper fra API
    if uke is None:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    else:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={uke}&season={season}&seasontype=2"
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

        home_score = home["score"]
        away_score = away["score"]
        if home_score > away_score:
            kamp_resultater[kampkode] = home_team
        elif away_score > home_score:
            kamp_resultater[kampkode] = away_team
        else:
            kamp_resultater[kampkode] = "Uavgjort"

    # Hent spillere
    header_row = sheet.row_values(1)
    id_row = sheet.row_values(2)
    players = {id_row[i]: i for i in range(len(id_row))}
    num_players = len(players)

    # Hent kampene fra Sheet (rad 3+)
    sheet_kamper = sheet.col_values(1)[2:]
    uke_total_row = 3 + len(sheet_kamper)
    sesong_total_row = uke_total_row + 1

    # Formatering
    green = cellFormat(backgroundColor=color(0,1,0))
    red = cellFormat(backgroundColor=color(1,0,0))
    yellow = cellFormat(backgroundColor=color(1,1,0))

    uke_poeng = [0] * num_players

    for row_idx, kampkode in enumerate(sheet_kamper, start=3):
        riktig_vinner = kamp_resultater.get(kampkode)
        for col_idx in range(2, num_players+2):
            cell_value = sheet.cell(row_idx, col_idx).value
            if not cell_value:
                fmt = yellow
            elif cell_value == riktig_vinner:
                fmt = green
                uke_poeng[col_idx-2] += 1
            else:
                fmt = red
            format_cell_range(sheet, f"{get_column_letter(col_idx)}{row_idx}", fmt)

    # Skriv ukes- og sesongpoeng
    for idx, poeng in enumerate(uke_poeng, start=2):
        sheet.update_cell(uke_total_row, idx, poeng)
        prev = sheet.cell(sesong_total_row, idx).value
        prev_val = int(prev) if prev and prev.isdigit() else 0
        sheet.update_cell(sesong_total_row, idx, prev_val + poeng)

    await ctx.send(f"✅ Resultater for uke {uke if uke else 'nåværende'} er oppdatert i Sheets.")

bot.run(TOKEN)
