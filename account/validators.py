import re
from django.core import validators
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class UsernameValidator(validators.RegexValidator):
    regex = r'^[a-zA-Z]{1}[a-zA-Z0-9.]{2,29}$'
    message = _(
        'Enter a valid username. This value may contain only English letters, '
        'numbers, and @/./_ characters.'
        'username must be at least 3 and at most 30 character.'
    )
    flags = re.ASCII
