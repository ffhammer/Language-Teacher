import streamlit as st
from datetime import date
from sqlmodel import Session, select
from src.db import engine
from src.anki import AnkiCard, CardCategorie

st.title("Edit Anki Cards")
category_options = ["All"] + [c.value for c in CardCategorie]
selected_category = st.selectbox("Select Card Category", category_options)
sort_by: str = st.selectbox("Sort by", ["next_date", "easiness_factor"])
order: str = st.radio("Order", ["ascending", "descending"])

with Session(engine) as sess:
    stmt = select(AnkiCard)
    col = getattr(AnkiCard, sort_by)
    stmt = stmt.order_by(col.asc() if order == "ascending" else col.desc())
    if selected_category != "All":
        stmt = stmt.where(AnkiCard.category == selected_category)
    cards: list[AnkiCard] = sess.exec(stmt).all()

    for card in cards:
        cols = st.columns([2, 2, 1, 2, 1, 1])
        a: str = cols[0].text_input("Front", value=card.a_content, key=f"a_{card.id}")
        b: str = cols[1].text_input("Back", value=card.b_content, key=f"b_{card.id}")
        nd: date = cols[2].date_input(
            "Next Date", value=card.next_date, key=f"d_{card.id}"
        )
        category: CardCategorie = cols[3].selectbox(
            "Category",
            CardCategorie,
            index=list(CardCategorie).index(card.category),
            key=f"cat_{card.id}",
        )
        ef: float = cols[4].number_input(
            "EF", value=card.easiness_factor, key=f"ef_{card.id}"
        )
        if cols[5].button("Save", key=f"save_{card.id}"):
            (
                card.a_content,
                card.b_content,
                card.next_date,
                card.easiness_factor,
                card.category,
            ) = (a, b, nd, ef, category)
            sess.add(card)
            sess.commit()
            st.rerun()
        if cols[5].button("Delete", key=f"del_{card.id}"):
            sess.delete(card)
            sess.commit()
            st.rerun()
