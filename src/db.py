from sqlmodel import create_engine

from src.anki import SQLModel

engine = create_engine("sqlite:///db.sqlite")

SQLModel.metadata.create_all(engine)
