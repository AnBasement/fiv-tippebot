# Håndterer errors

__all__ = (
    "BotError",
    "PPRFetchError",
    "PPRSnapshotError",
    "ResponseError",
    "SheetsError",
    "MissingCredentialsError",
    "ClientAuthorizationError",
    "SheetNotFoundError",
)


class BotError(Exception):
    """Grunnklasse for alle errors relatert til botten."""
    pass


class PPRFetchError(BotError):
    """Raised når botten ikke klarer å hente PPR."""
    def __init__(self, team_name: str, season: str, message: str = None):
        self.team_name = team_name
        self.season = season
        self.message = message or (
            f"Kunne ikke hente PPR for laget '{team_name}' "
            f"i sesong {season}"
        )
        super().__init__(self.message)


class PPRSnapshotError(BotError):
    """Raised når botten ikke klarer å lagre et PPR snapshot."""
    def __init__(self, message: str = None):
        self.message = message or "Klarte ikke lagre snapshot av PPR"
        super().__init__(self.message)


class ResponseError(BotError):
    """Raised når en responses-kommando feiler."""
    def __init__(self, command_name: str, message: str = None):
        self.command_name = command_name
        self.message = message or (
            f"Noe gikk galt i responses-kommandoen '{command_name}'"
        )
        super().__init__(self.message)


class SheetsError(BotError):
    """Grunnklasse for errors knyttet til Google Sheets."""
    pass


class MissingCredentialsError(SheetsError):
    """Raised når credentials.json mangler."""
    def __init__(self, path="credentials.json"):
        self.path = path
        self.message = f"Fant ikke Google API credentials-filen: '{path}'"
        super().__init__(self.message)


class ClientAuthorizationError(SheetsError):
    """Raised når gspread ikke kan autorisere klient."""
    def __init__(self, message: str = None):
        self.message = message or (
            "Kunne ikke autorisere Google Sheets-klienten"
        )
        super().__init__(self.message)


class SheetNotFoundError(SheetsError):
    """Raised når et sheet eller worksheet ikke kan åpnes."""
    def __init__(
        self,
        sheet_name: str,
        worksheet_index: int = 0,
        message: str = None
    ):
        self.sheet_name = sheet_name
        self.worksheet_index = worksheet_index
        self.message = message or (
            f"Kunne ikke åpne '{sheet_name}' eller {worksheet_index}"
        )
        super().__init__(self.message)


class VestskError(BotError):
    """Grunnklasse for errors knyttet til Vestsk Tipping-cogen."""
    pass


class APIFetchError(VestskError):
    """Raised når ESPNs API ikke kan hentes."""
    def __init__(self, url: str, original_exception: Exception = None):
        self.url = url
        self.original_exception = original_exception
        self.message = f"Kunne ikke hente data fra ESPN API: {url}"
        if original_exception:
            self.message += f" ({original_exception})"
        super().__init__(self.message)


class NoEventsFoundError(VestskError):
    """Raised når ingen kamper/events finnes for gitt uke."""
    def __init__(self, week: int = None):
        self.week = week
        self.message = (
            f"Ingen kamper funnet for uke {week}"
            if week else "Ingen kamper funnet"
        )
        super().__init__(self.message)


class ExportError(VestskError):
    """Raised ved feil under eksport til Sheets."""
    def __init__(self, message: str = None):
        self.message = message or "Feil under eksport av kampdata til Sheets"
        super().__init__(self.message)


class ResultaterError(VestskError):
    """Raised ved feil under oppdatering av resultater i Sheets."""
    def __init__(self, message: str = None):
        self.message = message or (
            "Feil under oppdatering av resultater i Sheets"
        )
        super().__init__(self.message)


class ReminderError(VestskError):
    """Raised når påminnelse feiler."""
    def __init__(self, message: str = None):
        self.message = message or "Feil i reminder-task"
        super().__init__(self.message)
