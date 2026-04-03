import json
import traceback

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from .models import ChatGroup, ChatGroupMember, ChatMessage, DirectChat, DirectMessage


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.group_id = self.scope["url_route"]["kwargs"]["group_id"]
            self.room_group_name = f"group_chat_{self.group_id}"
            self.user = self.scope.get("user", AnonymousUser())

            print("\n========== GROUP WS CONNECT START ==========")
            print("group_id:", self.group_id)
            print("user:", self.user)
            print("user.pk:", getattr(self.user, "pk", None))

            if not self.user or self.user.is_anonymous:
                print("WS rejected: anonymous user")
                await self.accept()
                await self.close(code=4001)
                return

            allowed = await self.user_is_member(self.group_id, self.user.pk)
            print("membership allowed:", allowed)

            if not allowed:
                print("WS rejected: user is not a member")
                await self.accept()
                await self.close(code=4003)
                return

            active = await self.group_is_active(self.group_id)
            print("group active:", active)

            if not active:
                print("WS rejected: group inactive/expired")
                await self.accept()
                await self.close(code=4004)
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            print("WS accepted successfully")
            print("========== GROUP WS CONNECT END ==========\n")

        except Exception as e:
            print("GROUP WS CONNECT ERROR:", str(e))
            traceback.print_exc()
            await self.close()

    async def disconnect(self, close_code):
        print("\n========== GROUP WS DISCONNECT ==========")
        print("group_id:", getattr(self, "group_id", None))
        print("close_code:", close_code)
        print("=========================================\n")

        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            print("\n========== GROUP WS RECEIVE ==========")
            print("raw text_data:", text_data)

            if not text_data:
                return

            data = json.loads(text_data)
            message = (data.get("message") or "").strip()

            if not message:
                print("Empty message ignored")
                return

            saved = await self.save_group_message(self.group_id, self.user.pk, message)
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

        except Exception as e:
            print("GROUP WS RECEIVE ERROR:", str(e))
            traceback.print_exc()

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

        if hasattr(group, "refresh_status"):
            group.refresh_status()
            group.refresh_from_db()

        print(f"group_is_active -> group_id={group_id}, is_active={group.is_active}")
        return group.is_active

    @database_sync_to_async
    def save_group_message(self, group_id, user_pk, message):
        try:
            group = ChatGroup.objects.get(pk=group_id)
        except ChatGroup.DoesNotExist:
            print("save_message -> group not found")
            return None

        if hasattr(group, "refresh_status"):
            group.refresh_status()
            group.refresh_from_db()

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
        try:
            self.chat_id = int(self.scope["url_route"]["kwargs"]["chat_id"])
            self.room_group_name = f"direct_chat_{self.chat_id}"
            self.user = self.scope.get("user", AnonymousUser())

            print("\n========== DIRECT WS CONNECT START ==========")
            print("chat_id:", self.chat_id)
            print("user:", self.user)
            print("user.pk:", getattr(self.user, "pk", None))

            if not self.user or self.user.is_anonymous:
                print("Direct WS rejected: anonymous user")
                await self.accept()
                await self.close(code=4001)
                return

            allowed = await self.user_is_direct_member(self.chat_id, int(self.user.pk))
            print("direct membership allowed:", allowed)

            if not allowed:
                print("Direct WS rejected: user not in direct chat")
                await self.accept()
                await self.close(code=4003)
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            print("Direct WS accepted successfully")
            print("========== DIRECT WS CONNECT END ==========\n")

        except Exception as e:
            print("DIRECT WS CONNECT ERROR:", str(e))
            traceback.print_exc()
            await self.close()

    async def disconnect(self, close_code):
        print("\n========== DIRECT WS DISCONNECT ==========")
        print("chat_id:", getattr(self, "chat_id", None))
        print("close_code:", close_code)
        print("==========================================\n")

        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            print("\n========== DIRECT WS RECEIVE ==========")
            print("raw text_data:", text_data)

            if not text_data:
                return

            data = json.loads(text_data)
            message = (data.get("message") or "").strip()

            if not message:
                print("Empty direct message ignored")
                return

            saved = await self.save_direct_message(self.chat_id, int(self.user.pk), message)
            print("direct saved payload:", saved)

            if not saved:
                print("Direct message save failed")
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "direct_chat_message",
                    **saved,
                },
            )

        except Exception as e:
            print("DIRECT WS RECEIVE ERROR:", str(e))
            traceback.print_exc()

    async def direct_chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def user_is_direct_member(self, chat_id, user_pk):
        try:
            chat = DirectChat.objects.get(pk=chat_id, is_active=True)
        except DirectChat.DoesNotExist:
            print(f"user_is_direct_member -> chat {chat_id} not found or inactive")
            return False

        user1_id = int(chat.user1_id)
        user2_id = int(chat.user2_id)
        user_pk = int(user_pk)

        allowed = (user1_id == user_pk) or (user2_id == user_pk)

        print(
            f"user_is_direct_member -> chat_id={chat_id}, "
            f"user1_id={user1_id}, user2_id={user2_id}, "
            f"user_pk={user_pk}, allowed={allowed}"
        )
        return allowed

    @database_sync_to_async
    def save_direct_message(self, chat_id, user_pk, message):
        try:
            chat = DirectChat.objects.get(pk=chat_id, is_active=True)
        except DirectChat.DoesNotExist:
            print("save_direct_message -> chat not found/inactive")
            return None

        user1_id = int(chat.user1_id)
        user2_id = int(chat.user2_id)
        user_pk = int(user_pk)

        if user1_id != user_pk and user2_id != user_pk:
            print("save_direct_message -> user not part of chat")
            return None

        msg = DirectMessage.objects.create(
            chat=chat,
            sender_id=user_pk,
            message=message,
        )

        print("save_direct_message -> created message id:", msg.id)

        return {
            "id": msg.id,
            "message": msg.message,
            "sender_id": msg.sender_id,
            "sender_name": getattr(msg.sender, "username", "User"),
            "created_at": msg.created_at.isoformat(),
            "is_mine": False,
        }