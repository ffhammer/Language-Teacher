import io

from gtts import gTTS
from loguru import logger

from src.anki import AnkiCard


def _single_try(word: str, lang: str) -> io.BytesIO | None:
    try:
        mp3_bytes = io.BytesIO()
        gTTS(word, lang=lang).write_to_fp(mp3_bytes)
        return mp3_bytes.getvalue()
    except Exception as e:
        logger.exception(f"Failed to generate audio - {e}")


def add_audios_inplance(card: AnkiCard, a_lang="es", b_lang="de"):
    card.a_mp3 = _single_try(card.a_content, a_lang)
    card.b_mp3 = _single_try(card.b_content, b_lang)
