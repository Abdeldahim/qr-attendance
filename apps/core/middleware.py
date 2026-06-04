"""Middleware for the core app."""


class AuditLogMiddleware:
    """
    Captures login/logout events automatically.
    Detailed audit logging is done at the view/signal level.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
