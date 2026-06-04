# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="E-mail")
    first_name = models.CharField(max_length=50, verbose_name="Nome")
    last_name = models.CharField(max_length=50, verbose_name="Sobrenome")
    
    # Controle de Acesso e Situação
    is_staff = models.BooleanField(default=False)
    
    # is_active = Controle Administrativo (Super Admin pode colocar como False para banir/bloquear)
    is_active = models.BooleanField(default=True, verbose_name="Ativo") 
    
    # email_verified = Controle do Sistema (Usuário só acessa se provar que o e-mail é dele)
    email_verified = models.BooleanField(default=False, verbose_name="E-mail Verificado")
    
    # Roteamento Inteligente
    default_workspace = models.ForeignKey(
        'tenants.Workspace',
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='default_users',
        verbose_name="Workspace Padrão"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"