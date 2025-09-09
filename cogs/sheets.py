import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import cellFormat, format_cell_range, color

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

def get_sheet():
    return client.open("Vestsk Tipping").sheet1

def get_players(sheet):
    """Returnerer mapping: Discord ID → kolonne"""
    id_row = sheet.row_values(2)
    return {id_row[i]: i for i in range(len(id_row))}

def format_cell(sheet, row, col, color_fmt):
    col_letter = chr(64 + col)
    format_cell_range(sheet, f"{col_letter}{row}", color_fmt)

def green_format():
    return cellFormat(backgroundColor=color(0,1,0))

def red_format():
    return cellFormat(backgroundColor=color(1,0,0))

def yellow_format():
    return cellFormat(backgroundColor=color(1,1,0))
