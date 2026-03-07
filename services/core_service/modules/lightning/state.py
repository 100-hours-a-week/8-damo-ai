from typing import TypedDict, List

class LightningState(TypedDict):
    # INPUT
    user_id: str
    x: str
    y: str
    # OUTPUT
    filtered_restaurant: List[dict]
    status_message: str
    error_message: str