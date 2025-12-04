"""Bruker- og lagnavn-mapping for Fest i Vest."""

from __future__ import annotations

import json
from pathlib import Path


TEAM_NAMES = {
    "Kristoffer": "Stavanger Unge Gutter",
    "Arild": "Wergeland Vipers",
    "Knut": "Storhaug Javeeelins",
    "Einar": "Hamburg Hurricanes",
    "Torstein": "Madla Lard Lads",
    "Peter": "Bjørgvin Latskap",
    "Edvard H": "Bergaluf Hvidings",
    "Tor": "Møhlenpris Bondelag",
}


def load_discord_ids(path: str | Path = "discord_ids.json") -> dict[int, int]:
    """Leser mapping fra ESPN lag-ID til Discord-bruker-ID fra en privat JSON-fil."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Fant ikke Discord-ID filen: {file_path}")

    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Kunne ikke lese JSON fra {file_path}") from exc

    try:
        return {int(key): int(value) for key, value in raw.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError(
            'Discord-ID filen må ha formatet {"team_id": "discord_id"}'
        ) from exc
