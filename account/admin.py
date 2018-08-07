from django.contrib import admin

from account.models import Status, Profile, User, UserConnection

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Status)
admin.site.register(UserConnection)
