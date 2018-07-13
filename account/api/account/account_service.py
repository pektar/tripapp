from django.contrib.auth import authenticate

from . import account_pb2_grpc
from .account_pb2 import *


class AccountService(account_pb2_grpc.AccountServiceServicer):
    def login(self, request, context):
        print(request)

        # login with username
        if request.username:
            user = authenticate(username=request.username, password=request.password)

            # user isn't available
            if user is None:
                result = RawMessage(success=False, message='username or password is wrong.')
                return LoginResp(result=result, user=None, token=None)

            # user is available
            else:
                result = RawMessage(success=True, message='login is successfully')
                user_summary = UserSummary(user_id=user.id, username=user.username,
                                           full_name='%s %s' % (user.first_name, user.last_name))
                return LoginResp(result=result, user_summary=user_summary)
        # login with email

        # request isn't valid
        result = RawMessage(success=False, message='request is not valid')
        return LoginResp(result=result)

    def signup(self, request, context):
        return super().signup(request, context)

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
