from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import WorkspaceInvite

class GenesisSetupForm(forms.Form):
    first_name = forms.CharField(label='Nome', max_length=50)
    last_name = forms.CharField(label='Sobrenome', max_length=50)
    company_name = forms.CharField(label='Nome da Empresa', max_length=100)
    
    password = forms.CharField(
        label='Crie sua Senha',
        widget=forms.PasswordInput,
        validators=[validate_password]
    )

class TeamInviteForm(forms.ModelForm):
    class Meta:
        model = WorkspaceInvite
        fields = ['email', 'is_tenant_admin']
        labels = {
            'email': 'E-mail do Funcionário',
            'is_tenant_admin': 'Dar poderes de Administrador (Dono)?'
        }

class EmployeeSetupForm(forms.Form):
    first_name = forms.CharField(label='Nome', max_length=50)
    last_name = forms.CharField(label='Sobrenome', max_length=50)
    password = forms.CharField(
        label='Crie sua Senha',
        widget=forms.PasswordInput,
        validators=[validate_password]
    )