"""
Custom authentication class that reads JWT from HTTP-only cookies.

This allows browsers to authenticate without exposing the token
in localStorage (which is vulnerable to XSS).
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """
    Extends JWTAuthentication to read the access token from
    an HTTP-only cookie named 'access_token'.

    Falls back to the Authorization header if cookie is absent,
    so API clients using Bearer tokens still work.
    """

    def authenticate(self, request):
        # Try cookie first
        cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            # Fall back to Authorization header
            return super().authenticate(request)

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None

        try:
            user = self.get_user(validated_token)
        except Exception:
            return None

        return user, validated_token
