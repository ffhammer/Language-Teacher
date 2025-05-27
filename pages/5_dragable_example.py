from src.tasks.dragging_task import DragAndDropTaskRow, DraggingTasks, dragging_task

example_task = DraggingTasks(
    title="Arrastra las palabras correctas",
    text_under_title="Completa las frases con la palabra correcta.",
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
    text_task_title="¡Bien hecho si completas todas correctamente!",
)

dragging_task(example_task, unique_task_key="spanish_a1_example")
