import re

with open("shared/stream/service.py", "r") as f:
    content = f.read()

old_def = """    async def publish_ai_discussion_request(self, event: RecommendationRequestPayload, message: KafkaMessage):
        incoming_headers = dict(message.headers) if message.headers else {}
        
        # 키 값 안전하게 추출
        raw_key = message.raw_message.key
        display_key = raw_key.decode('utf-8', errors='ignore') if raw_key else 'None'
        
        data = DiscussionRequestData(
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

        payload = DiscussionRequestPayload(
            event_id=event.event_id,
            event_type=EventType.DISCUSSION_REQUEST.value,
            payload=data,
        )

        await self._discussion_request_publisher.publish(
            headers=incoming_headers, 
            message=payload, 
            key=raw_key
        )
        print(f"Service: Published ai discussion request for key {display_key}")"""

new_def = """    async def publish_ai_discussion_request(self, event_id: int, key: bytes, metadata: dict, data: DiscussionRequestData):
        incoming_headers = metadata if metadata else {}
        
        # 키 값 안전하게 추출
        display_key = key.decode('utf-8', errors='ignore') if key else 'None'

        payload = DiscussionRequestPayload(
            event_id=event_id,
            event_type=EventType.DISCUSSION_REQUEST.value,
            payload=data,
        )

        await self._discussion_request_publisher.publish(
            headers=incoming_headers, 
            message=payload, 
            key=key
        )
        print(f"Service: Published ai discussion request for key {display_key}")"""

content = content.replace(old_def, new_def)

with open("shared/stream/service.py", "w") as f:
    f.write(content)

print("Patched successfully")
