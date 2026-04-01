from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from jwt import decode as jwt_decode
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from rest_framework_simplejwt.tokens import UntypedToken

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        print("\n========== WS MIDDLEWARE START ==========")
        print("raw query_string:", query_string)

        params = parse_qs(query_string)
        token = params.get("token", [None])[0]
        print("token found:", bool(token))

        scope["user"] = await self.get_user(token)
        print("resolved user:", scope["user"])
        print("========== WS MIDDLEWARE END ==========\n")

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token):
        if not token:
            print("No token provided")
            return AnonymousUser()

        try:
            UntypedToken(token)
            decoded = jwt_decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            print("decoded payload:", decoded)

            user_id = decoded.get("user_id")
            if not user_id:
                print("user_id missing in token")
                return AnonymousUser()

            return User.objects.get(pk=user_id)
        except (InvalidTokenError, ExpiredSignatureError, User.DoesNotExist, Exception) as e:
            print("JWT middleware error:", str(e))
            return AnonymousUser()