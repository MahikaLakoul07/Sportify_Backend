from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token):
    if not token:
        print("No token provided")
        return AnonymousUser()

    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)

        print("validated token user:", user)
        return user
    except Exception as e:
        print("JWT middleware error:", str(e))
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()

        print("\n========== WS MIDDLEWARE START ==========")
        print("raw query_string:", query_string)

        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        print("token found:", bool(token))

        scope["user"] = await get_user_from_token(token)

        print("resolved user:", scope["user"])
        print("========== WS MIDDLEWARE END ==========\n")

        return await super().__call__(scope, receive, send)