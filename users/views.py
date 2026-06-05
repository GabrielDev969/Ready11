from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext as _
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.http import HttpResponse
from .forms import RegisterForm, LoginForm
from django.contrib import messages
from tenants.models import WorkspaceMembership
from tenants.utils import effective_workspace, workspace_home_url

User = get_user_model()


def _redirect_authenticated_home(request):
    """
    Send an authenticated user to their workspace home, or to the public landing
    page if they don't belong to any workspace yet.
    """
    workspace = effective_workspace(request.user)
    if workspace:
        url = workspace_home_url(request, workspace)
        if url:
            return redirect(url)
    return redirect('landing')


def register_view(request):
    # Already logged in? No reason to show the signup screen.
    if request.user.is_authenticated:
        return _redirect_authenticated_home(request)

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Persist the user, but don't log them in yet.
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = True
            user.email_verified = False  # Starts unverified until they confirm by email.
            user.save()

            # Encode the user id and a signed token into the verification URL.
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Build the absolute link (honors http/https automatically).
            link = request.build_absolute_uri(
                reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
            )

            subject = _("Verify your email to access your workspace")
            message = _("Hi %(name)s,\n\nClick the link below to verify your account:\n\n%(link)s") % {
                'name': user.first_name,
                'link': link,
            }
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # Show the "check your email" screen.
            return render(request, 'users/register_success.html')
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    """Endpoint the user reaches by clicking the verification link in the email."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save()
        return HttpResponse(
            "<h1>{}</h1><p>{}</p>".format(
                _("Email verified successfully!"),
                _("You can now log in."),
            )
        )
    return HttpResponse("<h1>{}</h1>".format(_("Invalid or expired link.")), status=400)


def login_view(request):
    # Already logged in? Send them straight to their workspace instead of the login form.
    if request.user.is_authenticated:
        return _redirect_authenticated_home(request)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=email, password=password)

            if user is not None:
                # Golden rule: was the email verified?
                if not getattr(user, 'email_verified', False):
                    messages.error(request, _("Please verify your email before accessing the system."))
                    return render(request, 'users/login.html', {'form': form})

                # Was the account disabled by an administrator?
                if not user.is_active:
                    messages.error(request, _("Your account has been disabled by an administrator."))
                    return render(request, 'users/login.html', {'form': form})

                # All good: start the session.
                login(request, user)

                # Honor a validated ?next= (e.g. returning to accept an invite),
                # guarded against open redirects to untrusted hosts/schemes.
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)

                # Smart routing: take the user to their workspace home (with a safe
                # fallback if the default workspace no longer exists).
                return _redirect_authenticated_home(request)
            else:
                messages.error(request, _("Invalid email or password."))
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """Log the user out and return to the public landing page."""
    logout(request)
    return redirect('landing')


def set_default_workspace(request, workspace_id):
    """Set the user's default workspace (only if they're a member of it)."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return redirect('landing')

    is_member = WorkspaceMembership.objects.filter(
        user=request.user, workspace_id=workspace_id
    ).exists()
    if is_member:
        request.user.default_workspace_id = workspace_id
        request.user.save(update_fields=['default_workspace'])
        messages.success(request, _("Default workspace updated."))
    else:
        messages.error(request, _("You don't have access to that workspace."))

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('landing')
