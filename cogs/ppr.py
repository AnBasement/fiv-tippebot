"""
Modul som håndterer PPR (points per reception) statistikk og historikk.

Denne modulen gir funksjonalitet for å hente PPR-verdier fra spillernes
individuelle ark, lagre snapshots av PPR-verdier over tid, og vise
oppdaterte rangeringer i Discord.

"""

import logging
from discord.ext import commands
from core.errors import PPRFetchError, PPRSnapshotError
from cogs.sheets import get_client
from data.brukere import TEAM_NAMES
import os

# Sett opp logging
logger = logging.getLogger(__name__)

class PPR(commands.Cog):
    """Cog for håndtering av PPR-statistikk og -kommandoer.
    
    Denne cog-en håndterer innhenting av PPR-verdier fra Google Sheets,
    lagring av historiske data, og posting av rangeringer i Discord.
    """

    def __init__(self, bot):
        """Initialiserer PPR cog.
        
        Args:
            bot (commands.Bot): Discord bot-instansen
        """
        self.bot = bot
        try:
            self.sheet = get_client().open("Fest i Vest")
            logger.info("PPR Cog: Tilkoblet Google Sheets")
        except Exception as e:
            logger.error(f"PPR Cog: Kunne ikke koble til Google Sheets: {e}")
            raise

    def _get_players(self, season="2025"):
        """Henter PPR-data for alle spillere for gitt sesong.
        
        Går gjennom hvert spillerark og henter ut PPR-verdier for
        spesifisert sesong. Sesong-verdien finnes i kolonne A
        og verdiene må være i kolonne B.
        
        Args:
            season (str, optional): Sesongen å hente PPR for. Standard er "2025".
        
        Returns:
            list[dict]: Liste med dictionaries som inneholder lagnavn og PPR for hver spiller.
                Format: [{"team": str, "ppr": float}, ...]
        
        Raises:
            PPRFetchError: Hvis PPR-data ikke kan hentes for en spiller.
        """
        target_names = [
            "Kristoffer", "Arild", "Knut",
            "Einar", "Torstein", "Peter",
            "Edvard H", "Tor"
        ]
        
        players = []
        logger.info(f"Henter PPR-data for sesong {season}")

        for ws in self.sheet.worksheets():
            if ws.title not in target_names:
                continue
            
            logger.debug(f"Prosesserer ark: {ws.title}")
            try:
                rows = ws.get_all_values()
                target_row = None
                for i, row in enumerate(rows, start=1):
                    if row[0] == season:
                        target_row = i
                        break
                        
                if target_row:
                    try:
                        ppr_value = float(rows[target_row-1][1])  # B = indeks 1
                        players.append({"team": ws.title, "ppr": ppr_value})
                        logger.debug(f"PPR for {ws.title}: {ppr_value}")
                    except ValueError as e:
                        raise PPRFetchError(
                            ws.title,
                            season,
                            f"Ugyldig PPR-verdi i rad {target_row}: {str(e)}"
                        )
                else:
                    raise PPRFetchError(
                        ws.title,
                        season,
                        f"Fant ingen rad for sesong {season}"
                    )
                    
            except Exception as e:
                raise PPRFetchError(
                    ws.title,
                    season,
                    f"Feil ved lesing av ark: {str(e)}"
                )

        logger.info(f"Hentet PPR-data for {len(players)} spillere")
        return players

    def _save_snapshot(self, players):
        """Lagrer et snapshot av dagens PPR-verdier.
        
        Oppdaterer arket 'PPR-historikk' med dagens
        PPR-verdier for alle spillere. Inkluderer rangering basert
        på PPR-verdi.
        
        Args:
            players (list[dict]): Liste med spillerdata.
                Format: [{"team": str, "ppr": float}, ...]
        
        Raises:
            PPRSnapshotError: Hvis snapshot ikke kan lagres.
        """
        try:
            history_ws = self.sheet.worksheet("PPR-historikk")
            logger.debug("Fant eksisterende PPR-historikk ark")
        except Exception:
            logger.info("Oppretter nytt PPR-historikk ark")
            history_ws = self.sheet.add_worksheet(title="PPR-historikk", rows=1000, cols=10)

        rows_to_add = []
        for rank, player in enumerate(players, start=1):
            display_name = TEAM_NAMES.get(player["team"], player["team"])
            rows_to_add.append([display_name, player["ppr"], rank])

        if not rows_to_add:
            logger.warning("Ingen PPR-data å lagre i snapshot")
            return

        try:
            all_rows_colA = history_ws.col_values(1)
            start_row = len(all_rows_colA) + 1
            num_rows = len(rows_to_add)
            num_cols = len(rows_to_add[0])

            cell_range = history_ws.range(
                start_row, 1,
                start_row + num_rows - 1,
                num_cols
            )
            flat_values = [val for row in rows_to_add for val in row]

            for cell_obj, val in zip(cell_range, flat_values):
                cell_obj.value = val

            history_ws.update_cells(cell_range)
            logger.info(f"Lagret snapshot med {num_rows} PPR-verdier")

        except Exception as e:
            raise PPRSnapshotError(
                f"Kunne ikke lagre PPR snapshot: {str(e)}"
            )

    @commands.command(name="ppr")
    @commands.check(lambda ctx: str(ctx.author.id) in os.getenv("ADMIN_IDS", "").split(","))
    async def ppr(self, ctx):
        """Poster oppdatert PPR-rangering i Discord.
        
        Henter dagens PPR-verdier, lagrer et snapshot, og viser
        rangeringen i Discord med endringer siden forrige snapshot.

        Args:
            ctx (commands.Context): Discord context-objektet

        Raises:
            PPRFetchError: Hvis PPR-data ikke kan hentes
            PPRSnapshotError: Hvis lagring av snapshot feiler
        """
        try:
            players = self._get_players()
            players_sorted = sorted(players, key=lambda x: x["ppr"], reverse=True)
            
            # Last historiske verdier
            history_ws = self.sheet.worksheet("PPR-historikk")
            rows = history_ws.get_all_values()
            logger.debug(f"Hentet {len(rows)} historiske PPR-verdier")
        except Exception as e:
            logger.error(f"Feil ved henting av PPR-data: {str(e)}")
            raise
        except Exception as e:
            print(f"[DEBUG] Kunne ikke åpne PPR-historikk: {e}")
            rows = []

        last_snapshot = {}
        last_ranks = {}
        for row in rows:
            if len(row) < 3:
                continue
            team, ppr_str, rank_str = row
            try:
                ppr_val = float(ppr_str)
                rank_val = int(rank_str)
            except ValueError:
                print(f"[DEBUG] Ugyldig rad i historikk: {row}")
                continue
            last_snapshot[team] = ppr_val
            last_ranks[team] = rank_val

        for rank, player in enumerate(players_sorted, start=1):
            team = TEAM_NAMES.get(player["team"], player["team"])
            old_ppr = last_snapshot.get(team)
            old_rank = last_ranks.get(team)
            player["rank"] = rank

            player["diff"] = player["ppr"] - old_ppr if old_ppr is not None else 0.0

            if old_rank is not None:
                if old_rank == rank:
                    player["rank_change"] = "="
                elif old_rank > rank:
                    player["rank_change"] = f"⇧{old_rank - rank}"
                else:
                    player["rank_change"] = f"⇩{rank - old_rank}"
            else:
                player["rank_change"] = "="

        msg_lines = []
        for player in players_sorted:
            diff_str = f"{player['diff']:+.3f}"
            team_name = TEAM_NAMES.get(player["team"], player["team"])
            line = (
                f"{player['rank']}. {team_name}: {player['ppr']:.3f} "
                f"({diff_str}) {player['rank_change']}"
            )
            msg_lines.append(line)
            print(f"[DEBUG] {line}")

        msg = "\n".join(msg_lines)
        await ctx.send(f"```text\n{msg}\n```")

        self._save_snapshot(players_sorted)
        print("[DEBUG] Snapshot lagret.")

# --- Setup ---
async def setup(bot):
    await bot.add_cog(PPR(bot))