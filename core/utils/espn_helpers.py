"""
Hjelpefunksjoner knyttet opp mot ESPNs API for fantasy
"""

import os
from espn_api.football import League

def get_league():
    """
    Henter informasjon om ligaen fra ESPNs API for fantasy football.
    """
    return League(
        league_id=int(os.getenv("ESPN_LEAGUE_ID")),
        year=int(os.getenv("ESPN_YEAR")),
        espn_s2=os.getenv("ESPN_S2"),
        swid=os.getenv("ESPN_SWID"),
    )
