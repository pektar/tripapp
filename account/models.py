import os
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from tripmedia.settings import BASE_DIR
from .strings.account import strings


###############################
# --------- MODELS ---------- #
# Define models that display database tables
###############################


class Status(models.Model):
    """
    Define different statuses for the user based on other user reports
    """

    status = models.CharField(max_length=40, null=False, blank=False)
    description = models.CharField(max_length=200, null=False, blank=True)
    can_login = models.BooleanField(null=False, blank=False)

    class Meta:
        verbose_name = 'Status'
        verbose_name_plural = 'Statuses'

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
    verified = models.BooleanField(null=False, blank=False, default=False)
    bio = models.CharField(max_length=40, null=True, blank=True)
    status = models.ForeignKey(Status, default=None, null=True, blank=True,
                               on_delete=models.SET_DEFAULT)  # TODO check on_delete field

    pic_url = models.ImageField(null=True, blank=True,
                                default=os.path.join(BASE_DIR, 'account\\static\\account\\default-avatar.jpg'))

    def __str__(self):
        return self.user.username

    def change_status(self, new_status):
        status = Status.get_or_create_status(new_status)
        self.objects.update(status=status)


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
