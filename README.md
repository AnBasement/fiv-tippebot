# Fest i Vest Discord Bot

Discord-bot laget for privat bruk i Fest i Vests server.  
Botten håndterer vestsk-tipping inkl. integrasjon med Google Sheets og diverse kommandoer.

## Filstruktur

    bot.py                # Starter boten og laster cogs
    keep_alive.py         # Holder boten i live på Render
    credentials.json      # Google Sheets API credentials (i .gitignore)
    .env                  # Miljøvariabler (i .gitignore)
    requirements.txt      # Python dependencies
    pyproject.toml        # Prosjektkonfig (ruff, pytest, osv.)
    runtime.txt           # Python-versjon for hosting
    .gitignore            # Ignorerte filer for git

    cogs/
        ppr.py              # Oppdaterer leaderboard for PPR
        utility.py          # Små hjelpekommandoer (f.eks. ping)
        vestsk_tipping.py   # Tippelek: kamper, eksporter, resultater og påminnelser
        sheets.py           # Hjelpefunksjoner for Google Sheets
        responses.py        # Diverse kommandoer med enkle svar

    data/
        brukere.py          # Kobler navn til lagnavn i FiV
        teams.py            # Team-data, short-names og emojis

    tests/                   
        __init__.py
        conftest.py
        test_ppr.py              # Tester for ppr.py
        test_responses.py        # Tester for responses.py
        test_sheets.py           # Tester for sheets.py
        test_utility.py          # Tester for utility.py
        test_vestsk_tipping.py   # Tester for vestsk_tipping.py

    .github/
        workflows/          # GitHub Actions CI/CD-oppsett

    .pytest_cache/         # Lokal cache (i .gitignore)
    .ruff_cache/           # Ruff cache (i .gitignore)

## Miljøvariabler

- DISCORD_TOKEN: Token for Discord-boten.
- GOOGLE_SHEETS_KEYFILE: Credentials.json inneholder info for bruk av Googe Sheets API.
- ADMIN_IDS: Komma-separert liste over Discord ID-er med admin-tilgang til tippekommandoene.

Credentials.json og .env pushes ikke til repo; begge er listet i .gitignore.

## Bidra

- Foreslå features, legg inn et issue.
- Legg til nye funksjoner i cogs/ eller hjelpere i cogs/.
- Skriv tester i tests/ for ny logikk.
- Åpne en PR mot hovedbranch; CI kjører tester og linting automatisk.

## Notater

- Prosjektet bruker pyproject.toml til å konfigurere verktøy (f.eks. ruff, pytest).
