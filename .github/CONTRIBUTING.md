# Bidra til Fest i Vest Tippebot

Bidrag til prosjektet er velkomne! Her er noen retningslinjer for hvordan du kan hjelpe til.

## Rapportere problemer

1. Sjekk først om problemet allerede er rapportert i [issues](https://github.com/AnBasement/fiv-tippebot/issues)
2. Hvis ikke, opprett en ny issue med følgende informasjon:
   - En klar og beskrivende tittel
   - Detaljert beskrivelse av problemet
   - Steg for å reprodusere problemet
   - Forventet vs. faktisk oppførsel
   - Relevante logger eller feilmeldinger
   - Screenshots hvis relevant

## Foreslå endringer

1. Fork repositoriet
2. Opprett en ny branch fra `main`
3. Gjør endringene
4. Skriv tester som dekker endringene
5. Commit endringene med beskrivende meldinger
6. Push til din fork
7. Åpne en Pull Request mot hovedrepositoriet

## Kodestandard

- Bruk type hints for alle funksjoner og metoder
- Skriv docstrings for alle klasser og funksjoner
- Følg [PEP 8](https://peps.python.org/pep-0008/)
- Kjør ruff før du committer kode
- Hold kommentarer og dokumentasjon på norsk, eller påpek at de ikke er på norsk slik at de kan oversettes
- Sørg for at alle tester passerer

## Testing

- Skriv tester for all ny funksjonalitet
- Kjør hele testsuiten før du committer: `python -m pytest`
- Oppretthold eller forbedre testdekningen

## Pull Request sjekkliste

- [ ] Koden følger prosjektets stilguide
- [ ] Nye tester er lagt til
- [ ] All eksisterende kode fungerer fortsatt
- [ ] Dokumentasjon er oppdatert
- [ ] Commit-meldinger er beskrivende
- [ ] Koden er kommentert der det er nødvendig
- [ ] CI/CD pipelinen passerer

## Spørsmål?

Om du har spørsmål om hvordan du kan bidra, kan du opprette et issue og merke det med "spørsmål".
