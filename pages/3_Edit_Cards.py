import streamlit as st
from datetime import date
from sqlmodel import Session, select
from src.db import engine
from src.anki import AnkiCard

st.title("Edit Anki Cards")

sort_by: str = st.selectbox("Sort by", ["next_date", "easiness_factor"])
order: str = st.radio("Order", ["ascending", "descending"])

with Session(engine) as sess:
    stmt = select(AnkiCard)
    col = getattr(AnkiCard, sort_by)
    stmt = stmt.order_by(col.asc() if order == "ascending" else col.desc())
    cards: list[AnkiCard] = sess.exec(stmt).all()

    for card in cards:
        cols = st.columns([2, 2, 2, 2, 1])
        a: str = cols[0].text_input("Front", value=card.a_content, key=f"a_{card.id}")
        b: str = cols[1].text_input("Back", value=card.b_content, key=f"b_{card.id}")
        nd: date = cols[2].date_input(
            "Next Date", value=card.next_date, key=f"d_{card.id}"
        )
        ef: float = cols[3].number_input(
            "EF", value=card.easiness_factor, key=f"ef_{card.id}"
        )
        if cols[4].button("Save", key=f"save_{card.id}"):
            card.a_content, card.b_content, card.next_date, card.easiness_factor = (
                a,
                b,
                nd,
                ef,
            )
            sess.add(card)
            sess.commit()
            st.rerun()
        if cols[4].button("Delete", key=f"del_{card.id}"):
            sess.delete(card)
            sess.commit()
            st.rerun()
