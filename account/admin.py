from django.contrib import admin

from account.models import Status, Profile

admin.site.register(Profile)
admin.site.register(Status)
