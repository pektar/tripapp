from django.contrib import admin

from account.models import Status, Profile, UserConnection

admin.site.register(Profile)
admin.site.register(Status)
admin.site.register(UserConnection)
