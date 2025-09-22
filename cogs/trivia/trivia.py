import random
from pathlib import Path
from cogs.trivia.schema import load_questions, Question

# Map kategori til YAML-fil
CATEGORY_FILES = {
    "nfl": "cogs/trivia/data/lists/nfl.yaml",
}

def get_random_question(category: str = "nfl") -> Question:
    """
    Henter et tilfeldig spørsmål fra valgt kategori.
    Hvis kategorien ikke finnes, fallback til 'nfl'.
    """
    file_path = CATEGORY_FILES.get(category.lower())
    if not file_path or not Path(file_path).exists():
        # Fallback til NFL hvis fil mangler
        file_path = CATEGORY_FILES["nfl"]
        category = "nfl"

    questions = load_questions(file_path, kategori=category)
    if not questions:
        raise ValueError(f"Ingen spørsmål funnet i kategori {category}")

    return random.choice(questions)
