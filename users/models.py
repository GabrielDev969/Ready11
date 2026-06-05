# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name=_("Email"))
    first_name = models.CharField(max_length=50, verbose_name=_("First name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last name"))

    # Access control and status
    is_staff = models.BooleanField(default=False)

    # is_active = administrative control (a super admin can set it to False to ban/block)
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    # email_verified = system control (the user only gets in after proving the email is theirs)
    email_verified = models.BooleanField(default=False, verbose_name=_("Email verified"))

    # Smart routing
    default_workspace = models.ForeignKey(
        'tenants.Workspace',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_users',
        verbose_name=_("Default workspace")
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
