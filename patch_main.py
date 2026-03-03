import re

with open("gateway/main.py", "r") as f:
    content = f.read()

old_def = """    await service.publish_ai_discussion_request(event, message)"""

new_def = """    from shared.schemas.stream_schema import DiscussionRequestData
    discussion_data = DiscussionRequestData(
        dining_data=event.payload.dining_data,
        user_ids=event.payload.user_ids,
        filtered_restaurant=[
            "6976b54010e1fa815903d4ce",
            "6976b57f10e1fa815903d4cf",
            "6976b58610e1fa815903d4d0",
            "6976b8b9fb8d6fe1764695b6",
            "6976b8bafb8d6fe1764695b7",
            "6976b8bafb8d6fe1764695b8",
            "6976b8bafb8d6fe1764695b9",
            "6976b8bafb8d6fe1764695ba",
            "6976b8bafb8d6fe1764695bb",
            "6976b8bafb8d6fe1764695bc",
            "6976b8bafb8d6fe1764695bd",
            "6976b8bafb8d6fe1764695be",
            "6976b8bafb8d6fe1764695bf",
            "6976b8bafb8d6fe1764695c0",
            "6976b8bafb8d6fe1764695c1",
            "6976b8bafb8d6fe1764695c2",
            "6976b8bafb8d6fe1764695c3",
        ],
        vote_result_list=[],
    )
    incoming_headers = dict(message.headers) if message.headers else {}
    raw_key = message.raw_message.key

    await service.publish_ai_discussion_request(
        event_id=event.event_id,
        key=raw_key,
        metadata=incoming_headers,
        data=discussion_data
    )"""

content = content.replace(old_def, new_def)

with open("gateway/main.py", "w") as f:
    f.write(content)

print("Patched successfully")
