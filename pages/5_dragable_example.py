from src.tasks.dragging_task import DragAndDropTaskRow, DraggingTask
from src.tasks.sentence_order import SentenceOrderTask

example = SentenceOrderTask(
    title="Ordne den Satz",
    subtitle="Ordne die Wörter, um den Satz auf Spanisch zu bilden.",
    source_sentence="Ich gehe heute ins Kino",
    target_sentence="Hoy voy al cine",
    distractor_words=["mañana", "ella", "nosotros", "libro"],
)
task = example.to_task()
print(task.rows[0].sentence)
task.id = 5
task.display()


example_task = DraggingTask(
    id=2,
    title="Arrastra las palabras correctas",
    suptitle="Completa las frases con la palabra correcta.",
    rows=[
        DragAndDropTaskRow(
            sentence="Yo $soy$ estudiante.", distractions=["eres", "es"]
        ),
        DragAndDropTaskRow(
            sentence="¿$Dónde$ vives?", distractions=["Cuándo", "Quién"]
        ),
        DragAndDropTaskRow(
            sentence="Ella $tiene$ un libro.", distractions=["tengo", "tenemos"]
        ),
        DragAndDropTaskRow(
            sentence="Nosotros $hablamos$ español.", distractions=["habla", "hablo"]
        ),
    ],
    text_below_task="¡Bien hecho si completas todas correctamente!",
)

example_task.display()
