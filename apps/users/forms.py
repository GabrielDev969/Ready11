from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput,
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _("The passwords don't match."))
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'autofocus': True})
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput,
    )


class ProfileForm(forms.ModelForm):
    """Edit the user's own basic info. Email is intentionally not editable here
    (changing it requires a re-verification flow)."""
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']
        labels = {
            'first_name': _('First name'),
            'last_name': _('Last name'),
        }


class LanguageForm(forms.ModelForm):
    language = forms.ChoiceField(
        label=_('Language'),
        choices=[('', _('Auto-detect (browser language)'))] + [
            (code, name) for code, name in settings.LANGUAGES
        ],
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = ['language']
