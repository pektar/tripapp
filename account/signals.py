################################
# --------- SIGNALS ---------- #
# Define functions that are sensitive to signals defined in Django
################################
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from account.models import User, UserConnection


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


@receiver(pre_save, sender=UserConnection)
def check_user_connections(sender, instance, **kwargs):
    print(instance.type)
    if instance.type == ConnectionType.BLOCK.name:
        if instance.user.following(one=instance.one) or instance.one.following(one=instance.user):
            instance.user.unfollow(one=instance.one)
            instance.one.unfollow(one=instance.user)
    elif instance.type == ConnectionType.FOLLOW.name:
        print(instance.one)
        if instance.one.blocking(instance.user):
            raise Exception("user is blocked by one")
