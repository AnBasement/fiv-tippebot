# Vestsk Tipping Discord Bot

Bot for privat tippelek ved siden av NFL Fantasy-ligaen.

## Filstruktur

```
bot.py                # Starter botten og laster cogs
keep_alive.py         # Holder botten i live på Render/UptimeRobot
credentials.json      # Google Sheets API credentials (i .gitignore)
.env                  # Miljøvariabler (DISCORD_TOKEN, ADMIN_IDS)
requirements.txt
runtime.txt

cogs/
├─ utility.py          # Små hjelpekommandoer (f.eks. ping)
├─ vestsk_tipping.py   # Tippelek: kamper, eksporter, resultater
├─ sheets.py           # Helpers for Google Sheets (formatering, kolonner, farger)

data/
├─ teams.py            # Team-data og emojis
```

## Struktur og funksjonalitet

- **bot.py**: Starter botten, laster alle cogs, og setter opp intents.
- **cogs/utility.py**: Små hjelpekommandoer, f.eks. ping.
- **cogs/vestsk_tipping.py**: Kommandoer for tippeleken: kamper, eksporter og resultater. Inkluderer admin-sjekk der nødvendig.
- **cogs/sheets.py**: Funksjoner for å hente Sheet, formatere celler og fargelegge.
- **data/teams.py**: Inneholder team-data, short-names og emojis.

## Miljøvariabler

- **DISCORD_TOKEN**: Token for Discord-botten.
- **ADMIN_IDS**: Komma-separert liste over Discord ID-er som skal ha admin-tilgang til tippekommandoene.
