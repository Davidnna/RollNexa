from django.shortcuts import redirect


class ForcePasswordChangeMiddleware:
    """
    Require administrator-created accounts to change their temporary password
    before using the rest of AttendIQ.
    """

    allowed_url_names = {"password_change", "logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = getattr(request, "resolver_match", None)
        # Clear a pending one-time password if the administrator navigates
        # away from its confirmation page.
        if request.session.get("attendiq_new_user_credentials") and (
            not match or match.url_name != "user_created"
        ):
            request.session.pop("attendiq_new_user_credentials", None)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or user.is_superuser:
            return None

        profile = getattr(user, "profile", None)
        if not profile or not profile.must_change_password:
            return None

        match = getattr(request, "resolver_match", None)
        if match and match.url_name in self.allowed_url_names:
            return None

        return redirect("password_change")
