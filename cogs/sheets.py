# Håndterer lesing av og skriving til sheets

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat, format_cell_range, color

from core.errors import MissingCredentialsError, ClientAuthorizationError, SheetNotFoundError

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """Returnerer credentials eller kaster MissingCredentialsError hvis fil mangler."""
    if not os.path.exists("credentials.json"):
        raise MissingCredentialsError()
    return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

def get_client():
    """Returnerer autorisert gspread-klient eller kaster ClientAuthorizationError."""
    creds = get_creds()
    try:
        return gspread.authorize(creds)
    except Exception as e:
        raise ClientAuthorizationError(str(e))

def get_sheet(sheet_name, worksheet_index=0):
    """Åpner et Google Sheet basert på navn, eller kaster SheetNotFoundError."""
    client = get_client()
    try:
        return client.open(sheet_name).get_worksheet(worksheet_index)
    except Exception as e:
        raise SheetNotFoundError(sheet_name, worksheet_index, str(e))

def format_cell(sheet, row, col, color_fmt):
    """Formaterer en enkeltcelle i et sheet."""
    col_letter = chr(64 + col)  # A=1, B=2, ...
    format_cell_range(sheet, f"{col_letter}{row}", color_fmt)

def green_format():
    """Returnerer grønn bakgrunn for celler."""
    return cellFormat(backgroundColor=color(0, 1, 0))

def red_format():
    """Returnerer rød bakgrunn for celler."""
    return cellFormat(backgroundColor=color(1, 0, 0))

def yellow_format():
    """Returnerer gul bakgrunn for celler."""
    return cellFormat(backgroundColor=color(1, 1, 0))
