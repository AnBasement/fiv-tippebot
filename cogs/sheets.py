"""
Modul for håndtering av integrasjon med Google Sheets.

Denne modulen gir et grensesnitt for å interagere med Google Sheets' API,
inkludert autentisering, tilkobling, og celleformatering. Det håndterer
feilsituasjoner og gir feilmeldinger.
"""

from typing import List, Dict, Any
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import format_cell_range
from gspread.worksheet import Worksheet
from gspread.client import Client

from core.errors import (
    MissingCredentialsError,
    ClientAuthorizationError,
    SheetNotFoundError,
)

# Definerer hvilke Google API-tilganger som trengs
scope: List[str] = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def get_creds() -> ServiceAccountCredentials:
    """Henter Google API-credentials fra lokal fil.

    Returns:
        ServiceAccountCredentials: Credentials-objekt for Google API.

    Raises:
        MissingCredentialsError: Hvis credentials.json-filen ikke finnes.
    """
    keyfile = os.getenv("GOOGLE_SHEETS_KEYFILE", "credentials.json")
    if not os.path.exists(keyfile):
        raise MissingCredentialsError(
            f"Kunne ikke finne credentials-filen: {keyfile}"
        )
    try:
        return ServiceAccountCredentials.from_json_keyfile_name(
            keyfile, scope  # type: ignore
        )
    except Exception as e:
        raise MissingCredentialsError(f"Feil ved lesing av credentials {keyfile}: {str(e)}")


def get_client() -> Client:
    """Oppretter en autorisert Google Sheets-klient.

    Returns:
        Client: Autorisert gspread-klient.

    Raises:
        ClientAuthorizationError: Hvis autorisering mot Google feiler.
        MissingCredentialsError: Hvis credentials ikke kan hentes.
    """
    try:
        creds = get_creds()
        return gspread.authorize(creds)
    except MissingCredentialsError:
        raise
    except Exception as e:
        raise ClientAuthorizationError(f"Kunne ikke autorisere mot Google: {str(e)}")


def get_sheet(sheet_name: str, worksheet_index: int = 0) -> Worksheet:
    """Åpner et spesifikt Google Sheet-dokument og arbeidsark.

    Args:
        sheet_name (str): Navnet på Google Sheet-dokumentet.
        worksheet_index (int, optional):
            Indeks for ønsket arbeidsark. Standard er 0.

    Returns:
        gspread.Worksheet: Det forespurte arbeidsarket.

    Raises:
        SheetNotFoundError: Hvis dokumentet eller arbeidsarket ikke finnes.
        ClientAuthorizationError: Hvis det er problemer med autorisering.
    """
    try:
        client = get_client()
        return client.open(sheet_name).get_worksheet(worksheet_index)
    except gspread.SpreadsheetNotFound:
        raise SheetNotFoundError(
            sheet_name, worksheet_index, f"Fant ikke dokumentet '{sheet_name}'"
        )
    except Exception as e:
        raise SheetNotFoundError(
            sheet_name, worksheet_index, f"Feil ved åpning av dokument: {str(e)}"
        )


def format_cell(
    sheet: Worksheet, row: int, col: int, color_fmt: Dict[str, Any]
) -> None:
    """Formaterer en enkeltcelle i et Google Sheet.

    Args:
        sheet (Worksheet): Arbeidsarket som skal formateres.
        row (int): Radnummer (1-basert).
        col (int): Kolonnenummer (1-basert).
        color_fmt (Dict[str, Any]): Formateringsinstrukser for cellen.
    """
    try:
        col_letter = chr(64 + col)  # Konverterer kolonnenummer til bokstav
        cell_range = f"{col_letter}{row}"
        format_cell_range(sheet, cell_range, color_fmt)
    except Exception as e:
        # Logger feilen men lar den fortsette siden formatering ikke er kritisk
        print(f"Advarsel: Kunne ikke formatere celle {col_letter}{row}: {str(e)}")


def green_format() -> Dict[str, Any]:
    """Genererer formateringsinstrukser for grønne celler.

    Returns:
        Dict[str, Dict[str, float]]:
            Formateringsinstrukser med grønn bakgrunn og sort tekst.
    """
    return {
        "backgroundColor": {"red": 0.0, "green": 1.0, "blue": 0.0},
        "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}},
    }


def red_format() -> Dict[str, Any]:
    """Genererer formateringsinstrukser for røde celler.

    Returns:
        Dict[str, Dict[str, float]]:
            Formateringsinstrukser med rød bakgrunn og sort tekst.
    """
    return {
        "backgroundColor": {"red": 1.0, "green": 0.0, "blue": 0.0},
        "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}},
    }


def yellow_format() -> Dict[str, Any]:
    """Genererer formateringsinstrukser for gule celler.

    Returns:
        Dict[str, Dict[str, float]]:
            Formateringsinstrukser med gul bakgrunn og sort tekst.
    """
    return {
        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0},
        "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}},
    }
