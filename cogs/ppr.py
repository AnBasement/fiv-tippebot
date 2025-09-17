# Cog som håndterer posting av ppr-informasjon til Discord 
# og lagrer snapshots til skjult ark.

from discord.ext import commands
from core.errors import PPRFetchError, PPRSnapshotError
from cogs.sheets import get_client
from data.brukere import TEAM_NAMES
import os

class PPR(commands.Cog):
    """Cog for PPR-relaterte kommandoer."""

    def __init__(self, bot):
        self.bot = bot
        self.sheet = get_client().open("Fest i Vest")

    def _get_players(self, season="2025"):
        # Liste over lagene vi vil hente PPR for
        target_names = [
            "Kristoffer", "Arild", "Knut",
            "Einar", "Torstein", "Peter",
            "Edvard H", "Tor"
        ]
        
        players = []

        for ws in self.sheet.worksheets():
            if ws.title not in target_names:
                continue
            print(f"Henter ark: {ws.title}")  # debug
            rows = ws.get_all_values()
            target_row = None
            for i, row in enumerate(rows, start=1):
                if row[0] == season:
                    target_row = i
                    break
            if target_row:
                try:
                    ppr_value = float(rows[target_row-1][1])  # B = indeks 1
                except ValueError:
                    raise PPRFetchError(ws.title, season, f"Ugyldig PPR-verdi i rad {target_row}")
                print(f"Finner PPR for {ws.title}: {ppr_value}")  # debug
                players.append({"team": ws.title, "ppr": ppr_value})
            else:
                raise PPRFetchError(ws.title, season, f"Fant ingen rad for {season} i {ws.title}")

        print(f"Totalt spillere funnet: {len(players)}")  # debug
        return players

    def _save_snapshot(self, players):
        """
        Lagre snapshot av dagens PPR i ark 'PPR-historikk' med batch-update.
        Hver rad: Lag | PPR | Rank
        """
        try:
            history_ws = self.sheet.worksheet("PPR-historikk")
        except Exception:
            history_ws = self.sheet.add_worksheet(title="PPR-historikk", rows=1000, cols=10)
            # optional: history_ws.hide()

        rows_to_add = []
        for rank, player in enumerate(players, start=1):
            # Bruk visningsnavn fra TEAM_NAMES, fallback til ark-tittel
            display_name = TEAM_NAMES.get(player["team"], player["team"])
            rows_to_add.append([display_name, player["ppr"], rank])

        if not rows_to_add:
            print("Ingen spillere å lagre i snapshot")
            return

        all_rows_colA = history_ws.col_values(1)
        start_row = len(all_rows_colA) + 1
        num_rows = len(rows_to_add)
        num_cols = len(rows_to_add[0])

        cell_range = history_ws.range(start_row, 1, start_row + num_rows - 1, num_cols)
        flat_values = [val for row in rows_to_add for val in row]

        for cell_obj, val in zip(cell_range, flat_values):
            cell_obj.value = val

        try:
            history_ws.update_cells(cell_range)
        except Exception as e:
            raise PPRSnapshotError(f"Kunne ikke oppdatere celler i PPR-historikk: {e}")

        print(f"Lagt til {num_rows} rader i PPR-historikk")  # beholde debug

    @commands.command(name="ppr")
    @commands.check(lambda ctx: str(ctx.author.id) in os.getenv("ADMIN_IDS", "").split(","))
    async def ppr(self, ctx):
        """Printer oppdatert PPR til Discord med endringer fra forrige snapshot."""
        players = self._get_players()

        players_sorted = sorted(players, key=lambda x: x["ppr"], reverse=True)

        try:
            history_ws = self.sheet.worksheet("PPR-historikk")
            rows = history_ws.get_all_values()
            print(f"[DEBUG] Antall rader i PPR-historikk: {len(rows)}")
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