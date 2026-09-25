"""One correlation id per request, returned in the `X-Correlation-ID` header so an incident can be traced."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from tenderer.apps.audit.api import correlated


class CorrelationMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        actor = user.pk if user is not None and user.is_authenticated else None
        with correlated(actor) as cid:
            response = self.get_response(request)
        response["X-Correlation-ID"] = cid
        return response
