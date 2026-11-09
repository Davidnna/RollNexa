import secrets
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.utils.crypto import constant_time_compare
from django.views.decorators.http import require_POST, require_http_methods

from .forms import AdminCreateAccountForm, AdminUpdateAccountForm, InitialAdminSetupForm
from .models import UserProfile

User = get_user_model()


def system_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, "accounts/access_denied.html", status=403)
        return view_func(request, *args, **kwargs)
    return wrapped


@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect("admin_dashboard")

    profile = request.user.profile
    if profile.role == UserProfile.ROLE_LECTURER:
        return redirect("lecturer_dashboard")
    if profile.role == UserProfile.ROLE_STUDENT:
        return redirect("student_dashboard")
    return render(request, "accounts/access_denied.html", status=403)


@system_admin_required
def admin_dashboard(request):
    context = {
        "student_count": UserProfile.objects.filter(role=UserProfile.ROLE_STUDENT).count(),
        "lecturer_count": UserProfile.objects.filter(role=UserProfile.ROLE_LECTURER).count(),
        "active_count": User.objects.filter(is_active=True, is_superuser=False).count(),
        "inactive_count": User.objects.filter(is_active=False, is_superuser=False).count(),
        "recent_users": (
            User.objects.filter(is_superuser=False)
            .select_related("profile")
            .order_by("-date_joined")[:6]
        ),
    }
    return render(request, "accounts/admin_dashboard.html", context)


@login_required
def student_dashboard(request):
    if request.user.is_superuser or request.user.profile.role != UserProfile.ROLE_STUDENT:
        return render(request, "accounts/access_denied.html", status=403)
    return render(request, "accounts/student_dashboard.html")


@login_required
def lecturer_dashboard(request):
    if request.user.is_superuser or request.user.profile.role != UserProfile.ROLE_LECTURER:
        return render(request, "accounts/access_denied.html", status=403)
    return render(request, "accounts/lecturer_dashboard.html")


@system_admin_required
def user_list(request):
    users = (
        User.objects.filter(is_superuser=False)
        .select_related("profile", "profile__department", "profile__programme")
        .order_by("last_name", "first_name", "username")
    )

    search = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(profile__institutional_id__icontains=search)
            | Q(profile__department__name__icontains=search)
            | Q(profile__programme__name__icontains=search)
        )

    if role in {UserProfile.ROLE_STUDENT, UserProfile.ROLE_LECTURER}:
        users = users.filter(profile__role=role)

    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)

    page_obj = Paginator(users, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "accounts/user_list.html",
        {
            "page_obj": page_obj,
            "search": search,
            "selected_role": role,
            "selected_status": status,
        },
    )


@system_admin_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    form = AdminCreateAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        temporary_password = secrets.token_urlsafe(14)
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                first_name=form.cleaned_data["first_name"].strip(),
                last_name=form.cleaned_data["last_name"].strip(),
                password=temporary_password,
            )
            profile = user.profile
            profile.role = form.cleaned_data["role"]
            profile.institutional_id = form.cleaned_data["institutional_id"].strip()
            profile.phone_number = form.cleaned_data["phone_number"].strip()
            if form.cleaned_data["role"] == UserProfile.ROLE_STUDENT:
                profile.programme = form.cleaned_data.get("programme")
                profile.department = profile.programme.department if profile.programme else None
                profile.current_level = form.cleaned_data.get("current_level") or ""
            else:
                profile.department = form.cleaned_data.get("department")
                profile.programme = None
                profile.current_level = ""
            profile.must_change_password = True
            profile.created_by = request.user
            profile.save()

        # Keep the one-time credential briefly in the server-side Django session,
        # then redirect (POST/Redirect/GET) to avoid duplicate account creation
        # if the administrator refreshes the confirmation page.
        request.session["rollnexa_new_user_credentials"] = {
            "user_id": user.pk,
            "temporary_password": temporary_password,
            "created_at": timezone.now().timestamp(),
        }
        return redirect("user_created")

    return render(request, "accounts/user_create.html", {"form": form})


@system_admin_required
@require_http_methods(["GET", "POST"])
def user_edit(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id, is_superuser=False)
    form = AdminUpdateAccountForm(request.POST or None, user=target)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            target.first_name = form.cleaned_data["first_name"].strip()
            target.last_name = form.cleaned_data["last_name"].strip()
            target.email = form.cleaned_data["email"].strip().lower()
            target.save(update_fields=["first_name", "last_name", "email"])
            profile = target.profile
            profile.institutional_id = form.cleaned_data["institutional_id"].strip()
            profile.phone_number = form.cleaned_data["phone_number"].strip()
            if profile.role == UserProfile.ROLE_STUDENT:
                profile.programme = form.cleaned_data.get("programme")
                profile.department = profile.programme.department if profile.programme else None
                profile.current_level = form.cleaned_data.get("current_level") or ""
            elif profile.role == UserProfile.ROLE_LECTURER:
                profile.department = form.cleaned_data.get("department")
                profile.programme = None
                profile.current_level = ""
            profile.save()
        messages.success(request, f"The account for {target.get_username()} has been updated.")
        return redirect("user_list")
    return render(request, "accounts/user_edit.html", {"form": form, "target_user": target})


@system_admin_required
def user_created(request):
    credentials = request.session.pop("rollnexa_new_user_credentials", None)
    if not credentials:
        return redirect("user_list")

    # The temporary credential is retrievable for five minutes only.
    if timezone.now().timestamp() - credentials.get("created_at", 0) > 300:
        return redirect("user_list")

    created_user = get_object_or_404(User, pk=credentials["user_id"])
    response = render(
        request,
        "accounts/user_created.html",
        {
            "created_user": created_user,
            "temporary_password": credentials["temporary_password"],
        },
    )
    add_never_cache_headers(response)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@system_admin_required
@require_POST
def toggle_account_status(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)

    if target.is_superuser or target.pk == request.user.pk:
        messages.error(request, "This administrator account cannot be changed here.")
        return redirect("user_list")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    state = "activated" if target.is_active else "deactivated"
    messages.success(request, f"The account for {target.get_username()} has been {state}.")
    return redirect("user_list")


class RollNexaPasswordChangeView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = "/accounts/password-change/done/"

    def form_valid(self, form):
        response = super().form_valid(form)
        profile = self.request.user.profile
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password", "updated_at"])
        messages.success(self.request, "Your password has been updated.")
        return response


@require_http_methods(["GET", "POST"])
def initial_admin_setup(request):
    # This one-time route is unavailable unless a token is configured and
    # no superuser exists. Remove the token from Render after setup.
    if not settings.BOOTSTRAP_ADMIN_TOKEN:
        raise Http404
    if User.objects.filter(is_superuser=True).exists():
        raise Http404

    form = InitialAdminSetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        supplied_token = form.cleaned_data["bootstrap_token"]
        if not constant_time_compare(supplied_token, settings.BOOTSTRAP_ADMIN_TOKEN):
            form.add_error("bootstrap_token", "The setup token is incorrect.")
        else:
            with transaction.atomic():
                # Re-check immediately before creation in case another request
                # completed the one-time setup concurrently.
                if User.objects.filter(is_superuser=True).exists():
                    raise Http404
                administrator = User.objects.create_superuser(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    first_name=form.cleaned_data["first_name"].strip(),
                    last_name=form.cleaned_data["last_name"].strip(),
                )
                profile = administrator.profile
                profile.role = UserProfile.ROLE_ADMIN
                profile.must_change_password = False
                profile.save(update_fields=["role", "must_change_password", "updated_at"])

            login(request, administrator)
            messages.success(request, "Your RollNexa system administrator account is ready.")
            return redirect("admin_dashboard")

    response = render(request, "accounts/initial_admin_setup.html", {"form": form})
    add_never_cache_headers(response)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
