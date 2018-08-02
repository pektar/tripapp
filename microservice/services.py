import grpc
import os
from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.timezone import now

from account.models import User
from tripmedia import settings
from tripmedia.settings import BASE_DIR
from .message import server_api_pb2 as msg
from .rpc import server_api_pb2_grpc as rpc


#
# def request_wrapper(func):
#     def deco(*args, **kwargs):
#         # Before request handlers
#         print('Before request', func.__name__)
#
#         rtn = func(*args, **kwargs)
#
#         # After request handlers
#         print('After request')
#
#         return rtn
#
#     return deco
#
#
# def GrpcServerWrapper(cls,list_func=None):
#     class ClassWrapper(object):
#         def __init__(self, *args, **kwargs):
#             self.instance = cls(*args, **kwargs)
#
#         def __getattribute__(self, k):
#             try:
#                 v = super(ClassWrapper, self).__getattribute__(k)
#             except AttributeError:
#                 pass
#             else:
#                 return v
#             v = self.instance.__getattribute__(k)
#             if type(v) == type(self.__init__):
#                 print(list_func)
#                 return request_wrapper(v)
#             else:
#                 return v
#
#     return ClassWrapper


class ServerApi(rpc.ServerApiServicer):

    def signup(self, request, context):
        print(request)
        session_key = None

        # check username is available
        try:
            old_user = User.objects.get(username=request.username)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("username is not available.")
            return msg.SignupResp(session_key=session_key)
        except User.DoesNotExist:
            pass

        # check email is available
        try:
            old_user = User.objects.get(email=request.email)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("email already exist.")
            return msg.SignupResp(session_key=session_key)
        except User.DoesNotExist:
            pass

        email_validator = validate_email
        try:
            email_validator(request.email)
            new_user = User.objects.create_user(request.username, request.email, request.raw_password)
            if new_user:
                session_key = self._create_session()
        except ValidationError as e:
            print(e.message)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("please enter a valid email.")

        return msg.SignupResp(session_key=session_key)

    def is_logged_in(self, request, context):
        # # get user session key from metadata sent
        # session_key = dict(context.invocation_metadata()).get('session_key')
        #
        # # check meta key that represent user logged state
        # session = SessionStore(session_key)
        # if session['_auth_logged_in']:
        #     return msg.Empty(success=True)
        # print(context.peer_identity_key())
        return msg.Empty(success=True)

    # @log_errors
    def login(self, request, context):
        session_key = None

        user = authenticate(username=request.username, password=request.raw_password)
        if user:
            session_key = self._create_session()
        else:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Username or password is incorrect."
                                "\n"
                                "if you've forgotten your username or password, we can help you get back into your "
                                "account")

        return msg.LoginResp(session_key=session_key)

    def logout(self, request, context):
        # get session key from metadata sent
        session_key = dict(context.invocation_metadata()).get('session_key')

        # delete session from db
        self._delete_session(session_key)

        return msg.Empty()

    def is_username_available(self, request, context):
        try:
            user = User.objects.get(username=request.username)
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Username is not available.")
        except User.DoesNotExist:
            pass

        return msg.Empty()

    def is_email_available(self, request, context):
        try:
            user = User.objects.get(email=request.email)
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Email already exist.")
        except User.DoesNotExist:
            pass

        return msg.Empty()

    def get_file(self, request, context):
        file_path = os.path.join(BASE_DIR, "a.MP4")
        with open(file_path, 'rb') as file:
            # for chunk in file.read(64):
            yield msg.Chunk(blob=file.read())

    @classmethod
    def _create_session(cls):
        session = SessionStore()
        session['_auth'] = settings.AUTH_USER_META_VALUE
        session['_auth_logged_in'] = True
        session['_auth_last_login'] = now().timestamp()
        session['_auth_last_request'] = now().timestamp()
        session.create()
        return session.session_key

    @classmethod
    def _delete_session(cls, session_key):
        try:
            Session.objects.get(pk=session_key).delete()
            return True
        except Session.DoesNotExist:
            return False
