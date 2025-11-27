"""Statisk liste over NFL-lag med emojis og korte navn."""

# Teams og emojis
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
    "Washington Commanders": {
        "emoji": "<:was:1022586486845096016>",
        "short": "Commanders",
    },
    "Chicago Bears": {"emoji": "<:chi:1283701338034671689>", "short": "Bears"},
    "Detroit Lions": {"emoji": "<:det:752546616216518747>", "short": "Lions"},
    "Green Bay Packers": {"emoji": "<:gb:752546616149278840>", "short": "Packers"},
    "Minnesota Vikings": {"emoji": "<:min:752546616023449751>", "short": "Vikings"},
    "Atlanta Falcons": {"emoji": "<:atl:752546616182833243>", "short": "Falcons"},
    "Carolina Panthers": {"emoji": "<:car:752546616275239003>", "short": "Panthers"},
    "New Orleans Saints": {"emoji": "<:no:752546616250204321>", "short": "Saints"},
    "Tampa Bay Buccaneers": {
        "emoji": "<:tb:752546616262787132>",
        "short": "Buccaneers",
    },
    "Arizona Cardinals": {"emoji": "<:ari:752546616598069420>", "short": "Cardinals"},
    "Los Angeles Rams": {"emoji": "<:lar:885711442723090502>", "short": "Rams"},
    "San Francisco 49ers": {"emoji": "<:sf:752546616266981418>", "short": "49ers"},
    "Seattle Seahawks": {"emoji": "<:sea:752546616090689627>", "short": "Seahawks"},
}

DRAW_EMOJI = "<:gulfrglaff:800175714909028393>"
team_emojis = {v["short"]: v["emoji"] for v in teams.values()}
team_location = {v["short"]: v["short"] for v in teams.values()}
