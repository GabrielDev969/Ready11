import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class StrictPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(_("A senha deve ter no mínimo 8 caracteres."))
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("A senha deve conter pelo menos uma letra maiúscula."))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_("A senha deve conter pelo menos uma letra minúscula."))
        if not re.search(r'[0-9]', password):
            raise ValidationError(_("A senha deve conter pelo menos um número."))
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_("A senha deve conter pelo menos um caractere especial."))

    def get_help_text(self):
        return _("Sua senha deve ter no mínimo 8 caracteres, contendo maiúsculas, minúsculas, números e símbolos.")