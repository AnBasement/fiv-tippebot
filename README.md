# Fest i Vest Tippebot

[![CI](https://github.com/AnBasement/fiv-tippebot/actions/workflows/main.yml/badge.svg)](https://github.com/AnBasement/fiv-tippebot/actions/workflows/main.yml) [![codecov](https://codecov.io/gh/AnBasement/fiv-tippebot/branch/main/graph/badge.svg?token=NRAJ4ITBQ0)](https://codecov.io/gh/AnBasement/fiv-tippebot)

Discord-bot for en fantasyliga med Google Sheets integrasjon. Botten har foreløpig en hovedfunksjon med å håndtere ukentlige NFL-kamper hvor brukere kan tippe resultater og følge med på poengsummer gjennom sesongen, men videre funksjonalitet utvikles.

## Funksjoner

- NFL-kamphåndtering
  - Henter kommende kamper og resultater fra ESPN API
  - Eksporterer kampresultater til Google Sheets
  - Automatiske påminnelser for kommende kamper
- Vestsk Tipping-håndtering
  - Sporer brukeres bets og poengsummer ukentlig og gjennom sesongen
  - Integrasjon med Google Sheets for resultater
  - Admin-kommandoer for ligahåndtering
- Verktøy
  - Global cooldown for å unngå kommandospam
  - Omfattende feilhåndtering og logging
  - Solid testdekning

## Krav

- Python 3.11 eller nyere
- Discord Bot Token
- Google Sheets API credentials
- Se `requirements.txt` for Python-avhengigheter

## Installasjon

1. Klon repositoriet:

    ```bash
    git clone https://github.com/AnBasement/fiv-tippebot.git
    cd fiv-tippebot
    ```

1. Installer avhengigheter:

    ```bash
    pip install -r requirements.txt
    ```

1. Sett opp miljøvariabler i `.env`:

    ```env
    DISCORD_TOKEN=din_discord_bot_token
    GOOGLE_SHEETS_KEYFILE=sti_til_credentials.json
    ADMIN_IDS=komma,separert,liste,med,discord,ids
    ADMIN_CHANNEL_ID=discord_kanal_id
    ```

1. Start botten:

```bash
python -m core.bot
```

## Prosjektstruktur

```text
├── cogs/                 # Discord-bot moduler
│   ├── ppr.py           # Oppdaterer PPR-leaderboard
│   ├── utility.py       # Små hjelpekommandoer
│   ├── vestsk_tipping.py# Hovedlogikk for tippespillet
│   ├── sheets.py        # Google Sheets-integrasjon
│   └── responses.py     # Diverse respons-kommandoer
├── core/                # Kjernefunksjonalitet
│   ├── bot.py          # Bot-initialisering
│   ├── keep_alive.py   # Webserver for uptime
│   └── utils/          # Hjelpeverktøy
├── data/               # Statisk data og konfigurasjon
│   ├── brukere.py     # Bruker- og lagdata
│   └── teams.py       # NFL-lagdata og emojis
└── tests/              # Testsuite
    ├── test_ppr.py    
    ├── test_responses.py
    ├── test_sheets.py
    ├── test_utility.py
    └── test_vestsk_tipping.py
```

## Konfigurasjon

Prosjektet bruker følgende konfigurasjonsfiler:

- `pyproject.toml`: Konfigurerer utviklingsverktøy (ruff, pytest)
- `requirements.txt`: Python-pakkeavhengigheter
- `runtime.txt`: Python-versjonsspesifikasjon
- `.env`: Miljøvariabler (ikke i repo)
- `credentials.json`: Google Sheets API-tilgang (ikke i repo)

## Utvikling

Prosjektet følger disse utviklingspraksisene:

- Type hints og docstrings for bedre kodeforståelse
- Omfattende testdekning med pytest
- Kodekvalitetssjekk med ruff
- CI/CD gjennom GitHub Actions
- Google Sheets-integrasjon for datalagring

For å bidra:

1. Fork repositoriet
2. Opprett en feature branch
3. Skriv tester for ny funksjonalitet
4. Send inn en pull request

Eventuelt, registrer et issue.

## Testing

Kjør testsuiten:

```bash
python -m pytest
```

## Lisens

Dette prosjektet er lisensiert under GNU General Public License v3.0 - se [LICENSE](LICENSE) filen for detaljer.
