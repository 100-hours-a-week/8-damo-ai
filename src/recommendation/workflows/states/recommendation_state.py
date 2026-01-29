from typing import TypedDict, Annotated, List
import operator
from datetime import datetime


class RecommendationState(TypedDict):
    user_ids: List[int]
    filtered_restaurants: List[dict]
    current_recommendation: dict
    personas: List[dict]

    status_message: Annotated[List[str], operator.add]
    iteration_count: int
    max_iterations: int
    user_satisfied: bool

    process_start_time: datetime
    process_time: float
