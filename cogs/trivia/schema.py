from pathlib import Path
import yaml

class Question:
    def __init__(self, spørsmål_tekst, svar, kategori):
        self.spørsmål_tekst = spørsmål_tekst
        self.svar = svar
        self.kategori = kategori

def load_questions(file_path: str, kategori: str = "NFL"):
    """
    Leser en YAML-fil med spørsmål og lager Question-objekter.

    Args:
        file_path: Stien til YAML-filen.
        kategori: Valgfri kategori for spørsmålene.

    Returns:
        Liste av Question-objekter.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Filen {file_path} finnes ikke.")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    questions = []
    for key, value in data.items():
        # Hopp over metadata
        if key.upper() in ("FORFATTER", "BESKRIVELSE"):
            continue
        if isinstance(value, list) and len(value) > 0:
            answer = value[0]
            questions.append(Question(spørsmål_tekst=key, svar=answer, kategori=kategori))

    return questions
