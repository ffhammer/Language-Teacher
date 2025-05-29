import json

from src.config import LEVEL, SOURCE_LANGUAGE, TARGET_LANGUAGE
from src.llm import gemini_text_response, retry_n_times

from .plan import ExercisePlan, get_last_n_plans  # fix import


def represent_plans_as_json(plans: list[ExercisePlan]) -> str:
    res_list = []
    for plan in plans:
        as_dict = plan.model_dump(exclude=["id", "created_at"])
        as_dict["status"] = plan.status.__repr__()
        as_dict["tasks"] = [
            model.model_dump(exclude=["id", "excercise_plan_id"])
            for model in plan.dragging_tasks
        ] + [
            model.model_dump(exclude=["id", "excercise_plan_id"])
            for model in plan.fill_in_tasks
        ]
        res_list.append(as_dict)  # fix: append as_dict, not plan
    return json.dumps(res_list, indent=4)


SYSTEM_MESSAGE = f"""
You are an educational assistant helping a student learn {TARGET_LANGUAGE} using {SOURCE_LANGUAGE} as the instruction language.

The student's current proficiency level in {TARGET_LANGUAGE} is {LEVEL}.

You will receive the results of the student's recent exercise plans. Please provide a summary that includes:
- The overall proficiency and progress of the student.
- The topics and skills that were covered.
- An assessment of how well the student mastered each topic.
- Any recurring patterns or types of errors observed.
- Specific areas where the student needs improvement.
- Areas where the student performed particularly well.

Be clear, concise, and constructive in your feedback.

Now here are the last Results:
"""


def create_summaries_of_last_plans(
    n_plans: int = 3, n_retries: int = 3, model_name: str = "gemini-2.0-flash"
) -> str:
    plans = get_last_n_plans(n_plans=n_plans)

    if not plans:
        return "No plans found so far"

    contents = [represent_plans_as_json(plans=plans)]

    return retry_n_times(n=n_retries)(
        lambda: gemini_text_response(
            system_prompt=SYSTEM_MESSAGE, contents=contents, model_name=model_name
        )
    )
