from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


###############################
# --------- MODELS ---------- #
# Define models that display database tables
###############################


class Status(models.Model):
    """
    Define different statuses for the user based on other user reports
    """

    status = models.CharField(max_length=40, null=False, blank=False)
    describe = models.CharField(max_length=200, null=False, blank=True)
    can_login = models.BooleanField(null=False, blank=False)

    class Meta:
        verbose_name = 'Status'
        verbose_name_plural = 'Statuses'

    def __str__(self):
        return self.status


class Profile(models.Model):
    """
    Additional information about user to complete user's pages
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=False, blank=False)
    verified = models.BooleanField(null=False, blank=False, default=False)
    bio = models.CharField(max_length=40, null=True, blank=True)
    status = models.OneToOneField(Status, on_delete=models.DO_NOTHING, default=None,
                                  null=True)  # TODO check on_delete field

    def __str__(self):
        return self.user.username


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
        (active_status, is_created) = Status.objects.get_or_create(
            status="ACTIVE",
            describe="Your account is active.",
            can_login=True
        )
        Profile.objects.create(user=instance, status=active_status)

    else:
        instance.profile.save()
