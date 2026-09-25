"""Security headers Django 5.2 does not set itself (docs/architecture.md §10.3, ASVS V3).

Scripts only from our own origin (no inline script, no eval); inline styles stay allowed because the admin and the
dashboard signal use style attributes. Django already sets X-Frame-Options, nosniff and Referrer-Policy.
"""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
PERMISSIONS = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


class SecurityHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", PERMISSIONS)
        return response
