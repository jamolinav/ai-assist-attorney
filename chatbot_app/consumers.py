from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = f"user_{self.scope['user'].id}"
        print(f"[WebSocket] Conectando grupo: {self.group_name}")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def chat_progress(self, event):
        print(f"[WebSocket] Enviando mensaje al grupo {self.group_name}: {event['message']}")
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
