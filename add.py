from sqlmodel import Session, select
from tqdm import tqdm

from src.anki import AnkiCard, CardCategory
from src.audio import add_audios_inplance
from src.db import engine

cards = [
    {
        "a_content": "dar",
        "b_content": "geben",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): doy. Beispiel: *Yo doy regalos en Navidad.* (Ich gebe zu Weihnachten Geschenke.) Schlüsselformen: doy, das, da, damos, dais, dan.",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "ver",
        "b_content": "sehen",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): veo. Beispiel: *Veo una película esta noche.* (Ich sehe heute Abend einen Film.) Schlüsselformen: veo, ves, ve, vemos, veis, ven.",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "caber",
        "b_content": "passen (in einen Raum)",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): quepo. Beispiel: *No quepo en estos pantalones.* (Ich passe nicht in diese Hose.) Beispiel: *Todo cabe en la maleta.* (Alles passt in den Koffer.) Schlüsselformen: quepo, cabes, cabe, cabemos, cabéis, caben.",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "existir",
        "b_content": "existieren",
        "notes": "Regelmäßiges -ir Verb. Beispiel: *Los unicornios no existen.* (Einhörner existieren nicht.)",
        "category": CardCategory.regular_verb,
    },
    {
        "a_content": "mirar",
        "b_content": "ansehen, beobachten",
        "notes": "Regelmäßiges -ar Verb. Beispiel: *Miro la televisión por la noche.* (Ich sehe abends fern.)",
        "category": CardCategory.regular_verb,
    },
    {
        "a_content": "parecerse a",
        "b_content": "aussehen wie, ähneln (jemandem/etwas)",
        "notes": "Reflexives Verb. 'Parecer' (nicht reflexiv) bedeutet 'scheinen'. Beispiel: *Me parezco a mi madre.* (Ich sehe aus wie meine Mutter.) Beispiel: *Este perro se parece a un lobo.* (Dieser Hund sieht aus wie ein Wolf.)",
        "category": CardCategory.regular_verb,
    },
    {
        "a_content": "Verbs ending in -ecer, -ocer, -ucir (e.g., conocer, conducir)",
        "b_content": "Unregelmäßige 'yo'-Form im Indikativ Präsens (c -> zc)",
        "notes": "Viele Verben, die auf -ecer, -ocer oder -ucir enden (aber nicht alle, z.B. 'hacer', 'mecer'), ändern 'c' zu 'zc' in der 'yo'-Form des Indikativ Präsens. Beispiele: conocer -> conozco; conducir -> conduzco; agradecer -> agradezco; parecer -> parezco. Andere Formen sind bei diesem Muster normalerweise regelmäßig.",
        "category": CardCategory.grammar,
    },
    {
        "a_content": "conocer",
        "b_content": "kennen (Personen, Orte), vertraut sein mit",
        "notes": "Unregelmäßiges Verb (c -> zc in der 'yo'-Form: conozco). Beispiel: *Conozco a tu hermano.* (Ich kenne deinen Bruder.) *No conozco París.* (Ich kenne Paris nicht.) Unterscheiden von 'saber' (Fakten/Informationen wissen).",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "conducir",
        "b_content": "fahren, führen",
        "notes": "Unregelmäßiges Verb (c -> zc in der 'yo'-Form: conduzco). Beispiel: *Conduzco mi coche al trabajo.* (Ich fahre mein Auto zur Arbeit.) Stamm des Präteritums: conduj- (conduje, condujiste...).",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "leer",
        "b_content": "lesen",
        "notes": "Unregelmäßiges Verb im Präteritum (3. Person: leyó, leyeron) und Gerundium (leyendo). Indikativ Präsens ist regelmäßig (leo, lees, lee...). Beispiel: *Leo un libro cada semana.* (Ich lese jede Woche ein Buch.)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "poner",
        "b_content": "legen, stellen, setzen (Tisch decken)",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): pongo. Stamm des Präteritums: pus-. Beispiel: *Pongo los libros en la estantería.* (Ich lege die Bücher ins Regal.) *Pon la mesa, por favor.* (Deck den Tisch, bitte.)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "poner (la luz, la tele, la radio)",
        "b_content": "einschalten (das Licht, den Fernseher, das Radio)",
        "notes": "Spezifische Verwendung von 'poner'. Beispiel: *¿Puedes poner la música?* (Kannst du die Musik einschalten?) Das Gegenteil, 'ausschalten', ist 'apagar'.",
        "category": CardCategory.phrase,
    },
    {
        "a_content": "saber",
        "b_content": "wissen (Fakten, Informationen, wie man etwas macht)",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): sé. Stamm des Präteritums: sup-. Beispiel: *No sé la respuesta.* (Ich kenne die Antwort nicht.) *Sé nadar.* (Ich kann schwimmen / Ich weiß, wie man schwimmt.) Unterscheiden von 'conocer'.",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "traer",
        "b_content": "bringen",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): traigo. Stamm des Präteritums: traj-. Beispiel: *¿Puedes traer el postre?* (Kannst du das Dessert bringen?)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "hacer",
        "b_content": "tun, machen",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): hago. Stamm des Präteritums: hic- (él/ella/Ud: hizo). Beispiel: *Hago la tarea después de la escuela.* (Ich mache meine Hausaufgaben nach der Schule.)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "poder",
        "b_content": "können",
        "notes": "Unregelmäßiges Stammwechselverb (o:ue im Präsens, z.B. puedo, puedes, puede). Stamm des Präteritums: pud-. Beispiel: *Puedo ayudarte.* (Ich kann dir helfen.)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "caer",
        "b_content": "fallen",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): caigo. Präteritum (3. Person): cayó, cayeron. Gerundium: cayendo. Beispiel: *Las hojas caen en otoño.* (Die Blätter fallen im Herbst.) *Me caí de la bicicleta.* (Ich bin vom Fahrrad gefallen.)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "valer",
        "b_content": "wert sein, kosten",
        "notes": "Unregelmäßiges Verb. Indikativ Präsens (ich): valgo. Beispiel: *¿Cuánto vale este libro?* (Wie viel ist dieses Buch wert?) Häufige Redewendung: *Vale la pena.* (Es lohnt sich.)",
        "category": CardCategory.irregular_verb,
    },
    {
        "a_content": "cada",
        "b_content": "jeder, jede, jedes",
        "notes": "Adjektiv. Beispiel: *Cada día aprendo algo nuevo.* (Jeden Tag lerne ich etwas Neues.) *Cada estudiante recibió un premio.* (Jeder Schüler/jede Schülerin erhielt eine Auszeichnung.) 'Any' ist oft 'cualquier/cualquiera'.",
        "category": CardCategory.adjective,
    },
    {
        "a_content": "temprano",
        "b_content": "früh (Adverb)",
        "notes": "Adverb. Beispiel: *Me levanto temprano los lunes.* (Ich stehe montags früh auf.) 'Früher' ist 'más temprano'.",
        "category": CardCategory.adverb,
    },
    {
        "a_content": "entrenar",
        "b_content": "trainieren, üben (Sport, Fähigkeiten)",
        "notes": "Regelmäßiges -ar Verb. Beispiel: *Entreno para el maratón.* (Ich trainiere für den Marathon.) *Ella entrena piano dos horas al día.* (Sie übt täglich zwei Stunden Klavier.)",
        "category": CardCategory.regular_verb,
    },
    {
        "a_content": "después de",
        "b_content": "nach",
        "notes": "Präpositionale Phrase. Gefolgt von einem Nomen oder Infinitiv. Beispiel: *Después de la cena, vemos una película.* (Nach dem Abendessen sehen wir einen Film.) *Voy a llamarte después de terminar el trabajo.* (Ich rufe dich an, nachdem ich die Arbeit beendet habe.)",
        "category": CardCategory.preposition,
    },
    {
        "a_content": "cambiar",
        "b_content": "ändern, wechseln",
        "notes": "Regelmäßiges -ar Verb. Beispiel: *Necesito cambiar dólares a euros.* (Ich muss Dollar in Euro wechseln.) *El tiempo cambia constantemente.* (Das Wetter ändert sich ständig.)",
        "category": CardCategory.regular_verb,
    },
    {
        "a_content": "definitivamente",
        "b_content": "definitiv",
        "notes": "Adverb. Beispiel: *Definitivamente, este es el mejor pastel que he probado.* (Definitiv ist dies der beste Kuchen, den ich je probiert habe.)",
        "category": CardCategory.adverb,
    },
]
with Session(engine) as session:
    for c in tqdm(cards):
        # Try to find existing card by a_content and b_content
        # Delete all existing cards with same a_content and b_content
        stmt = select(AnkiCard).where(
            AnkiCard.a_content == c["a_content"],
        )
        for existing in session.exec(stmt).all():
            session.delete(existing)
        obj = AnkiCard(
            a_content=c["a_content"],
            b_content=c["b_content"],
            category=c["category"],
            notes=c["notes"],
        )
        add_audios_inplance(obj)
        session.add(obj)
    session.commit()
