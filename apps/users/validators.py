import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrictPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(_("The password must be at least 8 characters long."))
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("The password must contain at least one uppercase letter."))
        if not re.search(r'[a-z]', password):
            raise ValidationError(_("The password must contain at least one lowercase letter."))
        if not re.search(r'[0-9]', password):
            raise ValidationError(_("The password must contain at least one number."))
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_("The password must contain at least one special character."))

    def get_help_text(self):
        return _("Your password must be at least 8 characters long and include uppercase, lowercase, numbers and symbols.")
