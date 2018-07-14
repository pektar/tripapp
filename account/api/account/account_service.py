from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from . import account_pb2_grpc
from .account_pb2 import *


class AccountService(account_pb2_grpc.AccountServiceServicer):
    def login(self, request, context):

        # check with email
        try:
            validate_email(request.username_email)
            user = authenticate(email=request.username_email, password=request.password)
            print(user)
            print("e",request.username_email)

        # check with username
        except ValidationError:
            user = authenticate(username=request.username_email, password=request.password)
            print("u",request.username_email)

        # user isn't available
        if user is None:
            result = RawMessage(succuss=False, message='username or password is wrong.')
            return LoginResp(result=result, user=None, token=None)

        # user is available
        else:
            result = RawMessage(succuss=True, message='login is successfully')
            user_summary = UserSummary(user_id=user.id, username=user.username,
                                       full_name='%s %s' % (user.first_name, user.last_name))
            return LoginResp(result=result, user=user_summary)

    def signup(self, request, context):
        # check username is available
        print(request)
        try:
            old_user = User.objects.get(username=request.username)
            result = RawMessage(succuss=False, message='username is already registered')
            return SignupResp(result=result)
        except User.DoesNotExist:
            pass

        # check email is available
        try:
            old_user = User.objects.get(email=request.email)
            result = RawMessage(succuss=False, message='email is already existed')
            return SignupResp(result=result)
        except User.DoesNotExist:
            pass

        # username and email is available for signup
        # new_user = User(username=request.username,
        #                 email=request.email,
        #                 first_name=request.first_name,
        #                 last_name=request.last_name,
        #                 is_active=True)
        # new_user.set_password(request.password)
        # new_user.save()

        new_user = User.objects.create_user(request.username, request.email, request.password)

        if new_user is not None:
            result = RawMessage(succuss=True, message='welcome user!')
            user_summary = UserSummary(user_id=new_user.id, username=new_user.username,
                                       full_name='%s %s' % (new_user.first_name, new_user.last_name),
                                       pic_url=str(new_user.profile.pic_url))
            return SignupResp(result=result, user=user_summary)

        return SignupResp(result=RawMessage(succuss=False, message='something wrong!'))

    def get_user(self, request, context):
        return super().get_user(request, context)

    def get_account(self, request, context):
        return super().get_account(request, context)

    def get_followers(self, request, context):
        return super().get_followers(request, context)

    def get_following(self, request, context):
        return super().get_following(request, context)

    def change_user(self, request, context):
        return super().change_user(request, context)

    def change_profile(self, request, context):
        return super().change_profile(request, context)

    def follow(self, request, context):
        return super().follow(request, context)

    def unfollow(self, request, context):
        return super().unfollow(request, context)
