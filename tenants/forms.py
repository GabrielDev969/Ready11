from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import WorkspaceInvite, Role, AVAILABLE_PERMISSIONS

class GenesisSetupForm(forms.Form):
    first_name = forms.CharField(label='Nome', max_length=50)
    last_name = forms.CharField(label='Sobrenome', max_length=50)
    company_name = forms.CharField(label='Nome da Empresa', max_length=100)

    password = forms.CharField(
        label='Crie sua Senha',
        widget=forms.PasswordInput,
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "As senhas não coincidem.")
        return cleaned_data

class TeamInviteForm(forms.ModelForm):
    class Meta:
        model = WorkspaceInvite
        fields = ['email', 'role']
        labels = {
            'email': 'E-mail do Funcionário',
            'role': 'Cargo na Empresa'
        }

    def __init__(self, *args, **kwargs):
        # Capturamos o workspace que enviamos lá na view antes de iniciar o formulário
        workspace = kwargs.pop('workspace', None)
        super(TeamInviteForm, self).__init__(*args, **kwargs)
        
        if workspace:
            # Filtra os cargos para mostrar apenas os da empresa logada.
            # DICA DE SEGURANÇA: Excluímos o cargo is_system_owner para garantir 
            # que ninguém possa convidar um novo "Dono Absoluto" por acidente.
            self.fields['role'].queryset = Role.objects.filter(
                workspace=workspace, 
                is_system_owner=False
            )
            self.fields['role'].empty_label = "Selecione um cargo..."

class EmployeeSetupForm(forms.Form):
    first_name = forms.CharField(label='Nome', max_length=50)
    last_name = forms.CharField(label='Sobrenome', max_length=50)
    password = forms.CharField(
        label='Crie sua Senha',
        widget=forms.PasswordInput,
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "As senhas não coincidem.")
        return cleaned_data

class RoleForm(forms.ModelForm):
    # Transforma a lista do models em opções para os checkboxes
    PERMISSION_CHOICES = [(perm, perm.replace('.', ' ').title()) for perm in AVAILABLE_PERMISSIONS]
    
    permissions = forms.MultipleChoiceField(
        choices=PERMISSION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Permissões do Cargo"
    )

    class Meta:
        model = Role
        fields = ['name', 'is_default']
        labels = {
            'name': 'Nome do Cargo',
            'is_default': 'Tornar este o cargo padrão para novos convites?'
        }

    def clean_permissions(self):
        # O formulário retorna uma lista de strings, que é exatamente o que o nosso JSONField espera!
        return self.cleaned_data.get('permissions', [])