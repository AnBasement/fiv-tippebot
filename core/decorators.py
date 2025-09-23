import os
from discord.ext import commands

def admin_only():
    """Dekorator som sjekker om brukeren har admin-tilgang.
    
    Henter admin-IDer fra miljøvariabelen ADMIN_IDS og sjekker om
    brukerens Discord ID er i denne listen.
    
    Returns:
        function: En check-funksjon som returnerer True for admin-brukere
    
    Raises:
        CheckFailure: Hvis brukeren ikke er admin
    """
    ADMIN_IDS = {x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
    return commands.check(lambda ctx: str(ctx.author.id) in ADMIN_IDS)