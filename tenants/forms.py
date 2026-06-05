from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from .models import WorkspaceInvite, Role, AVAILABLE_PERMISSIONS


class GenesisSetupForm(forms.Form):
    first_name = forms.CharField(label=_('First name'), max_length=50)
    last_name = forms.CharField(label=_('Last name'), max_length=50)
    company_name = forms.CharField(label=_('Company name'), max_length=100)

    password = forms.CharField(
        label=_('Create your password'),
        widget=forms.PasswordInput,
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _("The passwords don't match."))
        return cleaned_data


class TeamInviteForm(forms.ModelForm):
    class Meta:
        model = WorkspaceInvite
        fields = ['email', 'role']
        labels = {
            'email': _('Member email'),
            'role': _('Role'),
        }

    def __init__(self, *args, **kwargs):
        # Capture the workspace passed from the view before building the form.
        workspace = kwargs.pop('workspace', None)
        super(TeamInviteForm, self).__init__(*args, **kwargs)

        # A role is mandatory: every membership needs one, so the invite must carry it.
        self.fields['role'].required = True

        if workspace:
            # Only show this workspace's roles. Security: exclude the system owner
            # role so nobody can accidentally invite another absolute owner.
            self.fields['role'].queryset = Role.objects.filter(
                workspace=workspace,
                is_system_owner=False,
            )
            self.fields['role'].empty_label = _("Select a role...")


class EmployeeSetupForm(forms.Form):
    first_name = forms.CharField(label=_('First name'), max_length=50)
    last_name = forms.CharField(label=_('Last name'), max_length=50)
    password = forms.CharField(
        label=_('Create your password'),
        widget=forms.PasswordInput,
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _("The passwords don't match."))
        return cleaned_data


class RoleForm(forms.ModelForm):
    # Turn the permissions list from the model into checkbox options.
    PERMISSION_CHOICES = [(perm, perm.replace('.', ' ').title()) for perm in AVAILABLE_PERMISSIONS]

    permissions = forms.MultipleChoiceField(
        choices=PERMISSION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Role permissions')
    )

    class Meta:
        model = Role
        fields = ['name', 'is_default']
        labels = {
            'name': _('Role name'),
            'is_default': _('Make this the default role for new invites?'),
        }

    def clean_permissions(self):
        # The form returns a list of strings, exactly what our JSONField expects.
        return self.cleaned_data.get('permissions', [])
