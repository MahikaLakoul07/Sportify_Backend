import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import ChatGroup, ChatGroupMember, ChatMessage, DirectChat, DirectMessage


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope["url_route"]["kwargs"]["group_id"]
        self.room_group_name = f"group_chat_{self.group_id}"
        self.user = self.scope["user"]

        print("\n========== GROUP WS CONNECT START ==========")
        print("group_id:", self.group_id)
        print("user:", self.user)
        print("user.pk:", getattr(self.user, "pk", None))

        if not self.user or self.user.is_anonymous:
            print("WS rejected: anonymous user")
            await self.close(code=4001)
            return

        allowed = await self.user_is_member(self.group_id, self.user.pk)
        print("membership allowed:", allowed)

        if not allowed:
            print("WS rejected: user is not a member")
            await self.close(code=4003)
            return

        active = await self.group_is_active(self.group_id)
        print("group active:", active)

        if not active:
            print("WS rejected: group inactive/expired")
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print("WS accepted successfully")
        print("========== GROUP WS CONNECT END ==========\n")

    async def disconnect(self, close_code):
        print("\n========== GROUP WS DISCONNECT ==========")
        print("group_id:", getattr(self, "group_id", None))
        print("close_code:", close_code)
        print("=========================================\n")

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        print("\n========== GROUP WS RECEIVE ==========")
        print("raw text_data:", text_data)

        data = json.loads(text_data)
        message = (data.get("message") or "").strip()

        if not message:
            print("Empty message ignored")
            return

        saved = await self.save_message(self.group_id, self.user.pk, message)
        print("saved payload:", saved)

        if not saved:
            print("Message save failed")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "group_chat_message",
                **saved,
            },
        )
        print("Broadcast sent")
        print("=====================================\n")

    async def group_chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def user_is_member(self, group_id, user_pk):
        exists = ChatGroupMember.objects.filter(group_id=group_id, user_id=user_pk).exists()
        print(f"user_is_member -> group_id={group_id}, user_pk={user_pk}, exists={exists}")
        return exists

    @database_sync_to_async
    def group_is_active(self, group_id):
        try:
            group = ChatGroup.objects.get(pk=group_id)
        except ChatGroup.DoesNotExist:
            print("group_is_active -> group not found")
            return False

        group.refresh_status()
        print(f"group_is_active -> group_id={group_id}, is_active={group.is_active}")
        return group.is_active

    @database_sync_to_async
    def save_message(self, group_id, user_pk, message):
        try:
            group = ChatGroup.objects.get(pk=group_id)
        except ChatGroup.DoesNotExist:
            print("save_message -> group not found")
            return None

        group.refresh_status()
        if not group.is_active:
            print("save_message -> group inactive")
            return None

        if not ChatGroupMember.objects.filter(group=group, user_id=user_pk).exists():
            print("save_message -> user not member")
            return None

        msg = ChatMessage.objects.create(
            group=group,
            sender_id=user_pk,
            message=message,
        )

        print("save_message -> created message id:", msg.id)

        return {
            "id": msg.id,
            "message": msg.message,
            "sender_id": msg.sender_id,
            "sender_name": getattr(msg.sender, "username", "User"),
            "created_at": msg.created_at.isoformat(),
            "is_mine": False,
        }


class DirectChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.room_group_name = f"direct_chat_{self.chat_id}"
        self.user = self.scope["user"]

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        allowed = await self.user_is_direct_member(self.chat_id, self.user.pk)
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = (data.get("message") or "").strip()
        if not message:
            return

        saved = await self.save_direct_message(self.chat_id, self.user.pk, message)
        if not saved:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "direct_chat_message",
                **saved,
            },
        )

    async def direct_chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def user_is_direct_member(self, chat_id, user_pk):
        try:
            chat = DirectChat.objects.get(pk=chat_id, is_active=True)
        except DirectChat.DoesNotExist:
            return False
        return chat.user1_id == user_pk or chat.user2_id == user_pk

    @database_sync_to_async
    def save_direct_message(self, chat_id, user_pk, message):
        try:
            chat = DirectChat.objects.get(pk=chat_id, is_active=True)
        except DirectChat.DoesNotExist:
            return None

        if chat.user1_id != user_pk and chat.user2_id != user_pk:
            return None

        msg = DirectMessage.objects.create(
            chat=chat,
            sender_id=user_pk,
            message=message,
        )

        return {
            "id": msg.id,
            "message": msg.message,
            "sender_id": msg.sender_id,
            "sender_name": getattr(msg.sender, "username", "User"),
            "created_at": msg.created_at.isoformat(),
            "is_mine": False,
        }