from typing import Dict
from cogs.sheets import get_sheet

SHEET_NAME = "FiV Trivia"

def get_scores() -> Dict[str, int]:
    """
    Leser poeng fra Google Sheets og returnerer en dict {navn: poeng}.
    Antar at kolonnene er: Plassering | Navn | Poeng
    """
    sheet = get_sheet(SHEET_NAME)
    rows = sheet.get_all_values()[1:]  # hopp over header
    scores = {}
    for row in rows:
        if len(row) >= 3 and row[1]:  # sjekk at Navn finnes
            navn = row[1]
            try:
                poeng = int(row[2])
            except ValueError:
                poeng = 0
            scores[navn] = poeng
    return scores


def update_score(navn: str, points: int) -> None:
    """
    Oppdaterer poengsummen for en spiller i Google Sheets.
    Øker eksisterende verdi eller legger inn ny rad om den ikke finnes.
    """
    sheet = get_sheet(SHEET_NAME)
    rows = sheet.get_all_values()
    
    # Finn rad med riktig navn
    for idx, row in enumerate(rows[1:], start=2):  # start=2 pga header
        if len(row) >= 2 and row[1] == navn:
            # Oppdater eksisterende poeng
            try:
                current_points = int(row[2])
            except ValueError:
                current_points = 0
            new_points = current_points + points
            sheet.update_cell(idx, 3, new_points)  # kolonne C = Poeng
            return
    
    # Hvis navnet ikke finnes: legg til ny rad nederst
    new_row = ["", navn, points]
    sheet.append_row(new_row)


def reset_scores() -> None:
    """
    Nullstiller poengene i Google Sheets, men beholder navnene.
    """
    sheet = get_sheet(SHEET_NAME)
    rows = sheet.get_all_values()
    for idx, row in enumerate(rows[1:], start=2):
        if len(row) >= 2 and row[1]:
            sheet.update_cell(idx, 3, 0)