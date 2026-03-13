from django.contrib import admin
from .models import ChatGroup, ChatGroupMember, ChatMessage

admin.site.register(ChatGroup)
admin.site.register(ChatGroupMember)
admin.site.register(ChatMessage)