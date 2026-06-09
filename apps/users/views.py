import base64
import io
import secrets
import urllib.parse

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.tenants.models import WorkspaceMembership
from apps.tenants.utils import effective_workspace, workspace_home_url

from .forms import LanguageForm, LoginForm, ProfileForm, RegisterForm

User = get_user_model()


def _redirect_authenticated_home(request):
    """
    Send an authenticated user to their workspace home, or to the notifications
    hub if they don't belong to any workspace yet (where pending invites live).
    """
    workspace = effective_workspace(request.user)
    if workspace:
        url = workspace_home_url(request, workspace)
        if url:
            return redirect(url)
    return redirect('notifications')


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

                # 2FA: if the user has a confirmed TOTP device, require verification
                # before creating the session.
                if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                    request.session['_2fa_user_id'] = user.pk
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url and url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    ):
                        request.session['_2fa_next'] = next_url
                    return redirect('2fa_verify')

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


def profile_view(request):
    """
    The user's own profile: edit basic info and change password. Works on any
    host (the user is global). Two forms on one page, distinguished by 'action'.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    language_form = LanguageForm(instance=request.user)
    totp_device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    static_device = StaticDevice.objects.filter(user=request.user, confirmed=True).first()
    backup_codes_count = static_device.token_set.count() if static_device else 0

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'profile':
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, _("Profile updated."))
                return redirect('profile')

        elif action == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Keep the user logged in after the password change.
                update_session_auth_hash(request, user)
                messages.success(request, _("Password changed."))
                return redirect('profile')

        elif action == 'language':
            language_form = LanguageForm(request.POST, instance=request.user)
            if language_form.is_valid():
                language_form.save()
                messages.success(request, _("Language preference saved."))
                return redirect('profile')

    return render(request, 'users/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'language_form': language_form,
        'totp_enabled': bool(totp_device),
        'backup_codes_count': backup_codes_count,
    })


def settings_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    totp_device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    static_device = StaticDevice.objects.filter(user=request.user, confirmed=True).first()
    return render(request, 'users/settings.html', {
        'totp_enabled': bool(totp_device),
        'backup_codes_count': static_device.token_set.count() if static_device else 0,
    })


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


def password_reset_request_view(request):
    if request.user.is_authenticated:
        return _redirect_authenticated_home(request)

    if request.method == 'POST':
        form = DjangoPasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject_template_name='users/email/password_reset_subject.txt',
                email_template_name='users/email/password_reset_body.txt',
            )
        # Always redirect — never reveal whether the email exists in our system.
        return redirect('password_reset_done')

    return render(request, 'users/password_reset_request.html', {'form': DjangoPasswordResetForm()})


def password_reset_done_view(request):
    return render(request, 'users/password_reset_done.html')


def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    valid = user is not None and default_token_generator.check_token(user, token)
    if not valid:
        return render(request, 'users/password_reset_confirm.html', {'invalid_link': True})

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            return redirect('password_reset_complete')
    else:
        form = SetPasswordForm(user)

    return render(request, 'users/password_reset_confirm.html', {'form': form})


def password_reset_complete_view(request):
    return render(request, 'users/password_reset_complete.html')


# ============================================================
# Two-factor authentication (TOTP)
# ============================================================

def verify_2fa_view(request):
    """Step 2 of login when the user has 2FA enabled. Not yet authenticated."""
    if request.user.is_authenticated:
        return _redirect_authenticated_home(request)

    user_id = request.session.get('_2fa_user_id')
    if not user_id:
        return redirect('login')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        del request.session['_2fa_user_id']
        return redirect('login')

    if request.method == 'POST':
        token = request.POST.get('token', '').strip().replace(' ', '')
        device = None

        for dev in TOTPDevice.objects.filter(user=user, confirmed=True):
            if dev.verify_token(token):
                device = dev
                break

        if device is None:
            for dev in StaticDevice.objects.filter(user=user, confirmed=True):
                if dev.verify_token(token):
                    device = dev
                    break

        if device is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            otp_login(request, device)
            next_url = request.session.pop('_2fa_next', None)
            request.session.pop('_2fa_user_id', None)
            if next_url:
                return redirect(next_url)
            return _redirect_authenticated_home(request)

        messages.error(request, _('Invalid code. Please try again.'))

    return render(request, 'users/2fa_verify.html')


def setup_2fa_view(request):
    """Enable TOTP 2FA: show QR code and confirm the first token."""
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user

    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return redirect('profile')

    if request.method == 'GET':
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.objects.create(user=user, name='Authenticator app', confirmed=False)
    else:
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if device is None:
            return redirect('2fa_setup')

        token = request.POST.get('token', '').strip().replace(' ', '')
        if device.verify_token(token):
            device.confirmed = True
            device.save()

            StaticDevice.objects.filter(user=user).delete()
            static_device = StaticDevice.objects.create(user=user, name='Backup codes', confirmed=True)
            backup_codes = []
            for _ in range(8):
                raw = secrets.token_hex(4).upper()
                code = f'{raw[:4]}-{raw[4:]}'
                StaticToken.objects.create(device=static_device, token=code)
                backup_codes.append(code)

            request.session['_backup_codes'] = backup_codes
            messages.success(request, _('Two-factor authentication enabled.'))
            return redirect('2fa_backup_codes')

        messages.error(request, _('Invalid code. Make sure your device clock is correct and try again.'))

    secret_b32 = base64.b32encode(device.bin_key).decode()
    label = urllib.parse.quote(f'Ready11:{user.email}')
    qs = urllib.parse.urlencode({
        'secret': secret_b32,
        'issuer': 'Ready11',
        'algorithm': 'SHA1',
        'digits': 6,
        'period': 30,
    })
    otpauth_url = f'otpauth://totp/{label}?{qs}'

    factory = qrcode.image.svg.SvgPathImage
    qr_obj = qrcode.QRCode(image_factory=factory, box_size=10, border=4)
    qr_obj.add_data(otpauth_url)
    qr_obj.make(fit=True)
    buf = io.BytesIO()
    qr_obj.make_image().save(buf)
    qr_svg = buf.getvalue().decode()

    secret_display = ' '.join(secret_b32[i:i + 4] for i in range(0, len(secret_b32), 4))

    return render(request, 'users/2fa_setup.html', {
        'qr_svg': qr_svg,
        'secret_display': secret_display,
    })


def backup_codes_view(request):
    """Show backup codes once after setup, or remaining count on repeat visits."""
    if not request.user.is_authenticated:
        return redirect('login')

    backup_codes = request.session.pop('_backup_codes', None)
    static_device = StaticDevice.objects.filter(user=request.user, confirmed=True).first()
    remaining = static_device.token_set.count() if static_device else 0

    return render(request, 'users/2fa_backup_codes.html', {
        'backup_codes': backup_codes,
        'remaining': remaining,
    })


def disable_2fa_view(request):
    """Disable 2FA after password confirmation."""
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user

    if not TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        return redirect('profile')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        if authenticate(request, username=user.email, password=password):
            TOTPDevice.objects.filter(user=user).delete()
            StaticDevice.objects.filter(user=user).delete()
            messages.success(request, _('Two-factor authentication disabled.'))
            return redirect('profile')
        messages.error(request, _('Incorrect password.'))

    return render(request, 'users/2fa_disable.html')
