import re
from django.core import validators
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class UsernameValidator(validators.RegexValidator):
    regex = r'^[a-zA-Z]+[a-zA-Z0-9.]{2,}$'
    message = _(
        'Enter a valid username. This value may contain only English letters, '
        'numbers, and @/./_ characters.'
    )
    flags = re.ASCII
