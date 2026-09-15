"""Sentral konfigurasjon for verdier som bør kunne endres uten kodeendring.
"""

import os

# Google Sheets-dokumenter
VESTSK_TIPPING_SHEET_NAME = os.getenv("VESTSK_TIPPING_SHEET_NAME", "Vestsk Tipping")
FEST_I_VEST_SHEET_NAME = os.getenv("FEST_I_VEST_SHEET_NAME", "Fest i Vest")

# PPR
# Kommaseparert liste over spillernavn (må matche fane-navnene i
# Fest i Vest-arket). Endres dersom ligaens deltakere endrer seg mellom sesonger.
PPR_PLAYER_NAMES = [
    name.strip()
    for name in os.getenv(
        "PPR_PLAYER_NAMES",
        "Kristoffer,Arild,Knut,Einar,Torstein,Peter,Edvard H,Tor",
    ).split(",")
    if name.strip()
]