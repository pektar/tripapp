import os
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AbstractUser, PermissionsMixin, UserManager
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from enum import Enum, unique

from account.validators import UsernameValidator
from tripmedia.settings import BASE_DIR
from .strings.account import strings


###############################
# --------- MODELS ---------- #
# Define models that display database tables
###############################

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that idea taken from django user model in auth app
    """

    username_validator = UsernameValidator
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    email = models.EmailField(blank=True, unique=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.username.strip()

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)


class Status(models.Model):
    """
    Define different statuses for the user based on other user reports
    """

    status = models.CharField(max_length=40, null=False, blank=False)
    description = models.CharField(max_length=200, null=False, blank=True)
    can_login = models.BooleanField(null=False, blank=False)

    class Meta:
        verbose_name = 'status'
        verbose_name_plural = 'statuses'

    def __str__(self):
        return self.status

    @staticmethod
    def get_or_create_status(status):
        """
        Create and return status
        """
        (status_obj, created) = Status.objects.get_or_create(
            status=status.get('status'),
            description=status.get('description'),
            can_login=status.get('can_login')
        )
        return status_obj


class Profile(models.Model):
    """
    Additional information about user to complete user's page
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=False, blank=False)
    full_name = models.CharField(max_length=150, blank=True)
    email_verified = models.BooleanField(null=False, blank=False, default=False, editable=False)
    verified = models.BooleanField(null=False, blank=False, default=False)
    bio = models.CharField(max_length=40, null=True, blank=True)
    status = models.ForeignKey(Status, default=None, null=True, blank=True,
                               on_delete=models.SET_DEFAULT)  # TODO check on_delete field

    pic_url = models.ImageField(null=True, blank=True,
                                default=os.path.join(BASE_DIR, 'account\\static\\account\\default-avatar.jpg'))

    def __str__(self):
        return self.user.username.strip()

    def get_connection(self, connection_type=None):
        # return specific connection type from self
        if connection_type:
            return UserConnection.objects.filter(creator=self, type=connection_type.name)
        # return all connections from self
        else:
            return UserConnection.objects.all()

    def change_status(self, new_status):
        status = Status.get_or_create_status(new_status)
        self.objects.update(status=status)


@unique
class ConnectionType(Enum):
    BLOCK = "Block"
    FOLLOW = "Follow"
    REPORT = "Report"
    SPAM = "Spam"


class UserConnection(models.Model):
    """
    Relations between users with different type of connections
    """
    created = models.DateTimeField(auto_now_add=True, editable=False)
    creator = models.ForeignKey(Profile, related_name="creator", on_delete=models.CASCADE)
    target = models.ForeignKey(Profile, related_name="target", on_delete=models.CASCADE)
    type = models.CharField(max_length=30,
                            choices=[(connection.name, connection.value) for connection in ConnectionType])

    class Meta:
        unique_together = ('creator', 'target', 'type')

    def __str__(self):
        return " ".join({self.creator, ConnectionType[self.type], self.target})


################################
# --------- SIGNALS ---------- #
# Define functions that are sensitive to signals defined in Django
################################

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create profile for the registered user
    or
    Update user profile when user information changed
    """

    # Create profile and set ACTIVE status to account -- TODO : ACTIVE STATUS
    if created:
        Profile.objects.create(user=instance, status=Status.get_or_create_status(strings.ACTIVE_STATUS))

    else:
        instance.profile.save()
