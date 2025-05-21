from src.anki import SQLModel, AnkiCard
from sqlmodel import create_engine, Session, select
from datetime import date

engine = create_engine("sqlite:///db.sqlite")

SQLModel.metadata.create_all(engine)
