from datetime import date

from sqlmodel import Session, create_engine, select

from src.anki import AnkiCard, CardCategory
from src.audio import add_audios_inplance

engine = create_engine("sqlite:///db.sqlite")


def get_cards_next_cards(category="All") -> list[AnkiCard]:
    with Session(engine) as sess:
        statement = select(AnkiCard).where(AnkiCard.next_date <= date.today())

        if category != "All":
            statement = statement.where(AnkiCard.category == category)
        statement = statement.order_by(AnkiCard.easiness_factor)

    return list(sess.exec(statement).all())


def add_card(a_content: str, b_content: str, category: CardCategory, notes: str | None):
    with Session(engine) as session:
        obj = AnkiCard(
            a_content=a_content,
            b_content=b_content,
            category=category,
            notes=notes,
        )
        add_audios_inplance(obj)
        session.add(obj)
        session.commit()
