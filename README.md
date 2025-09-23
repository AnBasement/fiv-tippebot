# Fest i Vest Tippebot

[![CI](https://github.com/AnBasement/fiv-tippebot/actions/workflows/main.yml/badge.svg)](https://github.com/AnBasement/fiv-tippebot/actions/workflows/main.yml) [![codecov](https://codecov.io/gh/AnBasement/fiv-tippebot/branch/main/graph/badge.svg?token=NRAJ4ITBQ0)](https://codecov.io/gh/AnBasement/fiv-tippebot)

Discord-bot for bruk på en privat server for NFL Fantasyligaen Fest i Vest. Utviklet som et prosjekt for å lære Python.

## Funksjoner

### Vestsk Tipping

Vestsk Tipping er ligaens tippelek. Hver uke tipper deltakere ved å reagere med lagets logo på meldinger som representerer hver kamp i uken. Dette ble tidligere sport manuelt. Botten håndterer nå hele spillet.
  - Integrert med Google Sheets API
  - Registrerer deltakernes bets og skriver dem til et Sheets-ark
  - Henter resultater fra ESPNs API og fargekoder Sheets-arket basert på om deltaker gjettet riktig
  - Sporer deltakernes bets og poengsummer ukentlig og gjennom sesongen
  - Poster ukesresultater og sesongresultater til dedikert Discord-kanal for tippeleken.

### PPR

PPR er fantasyligaens "power ranking" som forsøker å sette et tall til hvor bra et lag gjorde det i løpet av en sesong basert på totale poengsummer, laveste poengsum og sesongresultater, satt sammen med alle de andre lagene i ligaens resultater.
  - Henter PPR-verdien fra ligaens offisielle Sheets-dokument
  - Lagrer snapshots hver uke
  - Poster en oppdatert PPR-ranking hver uke som reflekterer bevegelser på topplisten og endring i PPR

### Respons-kommandoer

Botten har også en rekke enkle responskommandoer som for det meste kommer fra interne vitser.

## Planlagte funksjoner

### Trivia

En trivia-cog er under utvikling.
  - Deltakere har 60 sekunder på å svare. Kjappere svar gir flere poeng.
  - Topplisten spores i et eksternt Sheets-dokument.
  - Mulighet for enkeltspørsmål og runder med 10 spørsmål.
  - Flere kategorier, inkl. generell NFL-kategori og kategorier for hvert tiår.

### Oppdatering av ligadokumentet

Det er i teorien mulig å hel-automatisere oppdateringen av ligadokumentet med ESPN Fantasys API. Manglende dokumentasjon for APIen kompliserer det.
  - Hente sesongpoeng mot og sesongpoeng for
  - Sjekke siste ukes poengsum og sammenligne med celler for høyest eller lavest registrert kampresultat
  - Oppdatere antall seiere og tap samt plassering i ligaen
  - Oppdatere antall free agents
  - Oppdatere plassering/rekkefølge på karrieretopplisten

## Krav

- Python 3.11 eller nyere
- Discord Bot Token
- Google Sheets API credentials
- Se `requirements.txt` for Python-avhengigheter

## Installasjon

Vær klar over at denne botten er laget spesifikt for en privat server. Det vil derfor trolig være nødvendig å foreta en del endringer for å tilpasse til egen server. Ta kontakt om du ønsker å bruke botten og trenger hjelp.

1. Klon repositoriet:

    ```bash
    git clone https://github.com/AnBasement/fiv-tippebot.git
    cd fiv-tippebot
    ```

2. Installer avhengigheter:

    ```bash
    pip install -r requirements.txt
    ```

3. Sett opp miljøvariabler i `.env`:

    ```env
    DISCORD_TOKEN=din_discord_bot_token
    GOOGLE_SHEETS_KEYFILE=sti_til_credentials.json
    ADMIN_IDS=komma,separert,liste,med,discord,ids
    ADMIN_CHANNEL_ID=discord_kanal_id
    ```

4. Start botten:

    ```bash
    python -m core.bot
    ```

## Prosjektstruktur

```text
├── cogs/                        # Discord-bot moduler
│   ├── ppr.py                   # Oppdaterer PPR-leaderboard
│   ├── utility.py               # Små hjelpekommandoer
│   ├── vestsk_tipping.py        # Hovedlogikk for tippespillet
│   ├── sheets.py                # Google Sheets-integrasjon
│   └── responses.py             # Diverse respons-kommandoer
├── core/                        # Kjernefunksjonalitet
│   ├── bot.py                   # Bot-initialisering
│   ├── keep_alive.py            # Webserver for uptime
│   └── utils/                   # Hjelpeverktøy
│       ├── global_cooldown.py   # Cooldown for kommandospam
├── data/                        # Statisk data og konfigurasjon
│   ├── brukere.py               # Bruker- og lagdata
│   └── teams.py                 # NFL-lagdata og emojis
└── tests/                       # Testsuite
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

## Anerkjennelser

Dette prosjektet har hentet inspirasjon fra [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot), med ideer for cogs og strukturering av boten.

## Lisens

Dette prosjektet er lisensiert under GNU General Public License v3.0 - se [LICENSE](LICENSE) filen for detaljer.
