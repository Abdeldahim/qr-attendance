"""
WebSocket consumers for real-time attendance updates.

Phase 1: Stubs — accept connections, reply with placeholder.
Phase 5: Full implementation with live attendance push.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AttendanceSessionConsumer(AsyncWebsocketConsumer):
    """
    Lecturer-facing consumer.
    Pushes real-time attendance updates to the lecturer's dashboard
    as students scan QR codes.
    """

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'session_{self.session_id}'

        # Add to group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': f'Connected to session {self.session_id}',
        }))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass  # Lecturer channel is receive-only

    async def attendance_update(self, event):
        """Receive broadcast from channel layer and forward to WebSocket."""
        await self.send(text_data=json.dumps(event))


class StudentAttendanceConsumer(AsyncWebsocketConsumer):
    """
    Student-facing consumer.
    Receives confirmation when attendance is recorded.
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'student_{self.user.pk}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def attendance_confirmed(self, event):
        await self.send(text_data=json.dumps(event))
