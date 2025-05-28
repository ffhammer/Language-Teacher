from src.tasks.dragging_task import DragAndDropTaskRow, DraggingTask

example_task = DraggingTask(
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
