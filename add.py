from sqlmodel import Session
from src.anki import AnkiCard
from src.db import engine

cards = [
    {"a": "volver", "b": "zurückkehren"},
    {"a": "costar", "b": "kosten"},
    {"a": "dormir", "b": "schlafen"},
    {"a": "morir", "b": "sterben"},
    {"a": "poder", "b": "können"},
    {"a": "almorzar", "b": "zu Mittag essen"},
    {"a": "contar", "b": "erzählen, zählen"},
    {"a": "encontrar", "b": "finden"},
    {"a": "recordar", "b": "sich erinnern"},
    {"a": "mostrar", "b": "zeigen"},
]

with Session(engine) as session:
    objs = [AnkiCard(a_content=c["a"], b_content=c["b"]) for c in cards]
    session.add_all(objs)
    session.commit()
