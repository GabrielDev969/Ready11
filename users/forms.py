from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput,
        validators=[validate_password] # Aplica a regra de 8 dígitos, símbolos, etc.
    )
    confirm_password = forms.CharField(
        label='Confirmar Senha',
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
            self.add_error('confirm_password', "As senhas não coincidem.")
        return cleaned_data