import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat, format_cell_range, color
import os

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """Returnerer credentials eller None hvis fil mangler (brukes i tester/CI)."""
    if not os.path.exists("credentials.json"):
        return None
    return ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

def get_client():
    creds = get_creds()
    if creds is None:
        return None
    return gspread.authorize(creds)

def get_sheet(sheet_name, worksheet_index=0):
    """Åpne et Google Sheet basert på navn."""
    client = get_client()
    if client is None:
        return None
    return client.open(sheet_name).get_worksheet(worksheet_index)

def format_cell(sheet, row, col, color_fmt):
    col_letter = chr(64 + col)
    format_cell_range(sheet, f"{col_letter}{row}", color_fmt)

def green_format():
    return cellFormat(backgroundColor=color(0, 1, 0))

def red_format():
    return cellFormat(backgroundColor=color(1, 0, 0))

def yellow_format():
    return cellFormat(backgroundColor=color(1, 1, 0))
