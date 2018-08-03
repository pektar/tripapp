import grpc
import logging
from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.timezone import now

from account.models import User
from account.validators import UsernameValidator
from tripmedia import settings
from .message import server_api_pb2 as msg
from .rpc import server_api_pb2_grpc as rpc

logger = logging.getLogger(__name__)


class ServerApi(rpc.ServerApiServicer):
    username_validator = UsernameValidator()
    email_validator = validate_email

    def signup(self, request, context):
        session_key = None

        # clean data
        username = str.lower(request.username)
        email = str.lower(request.email)
        raw_password = request.raw_password

        # check username
        try:
            self._validate_username(username=username)
        except ValidationError as e:
            context.set_code(e.code)
            context.set_details(e.message)
            return msg.SignupResp(session_key=None)

        # check email
        try:
            self._validate_email(email=email)
        except ValidationError as e:
            context.set_code(e.code)
            context.set_details(e.message)
            return msg.SignupResp(session_key=None)

        # register new user
        user = User.objects.create_user(request.username, request.email, raw_password)
        if user:
            session_key = self._create_session()
            logger.debug("Successfully user created, User:%s" % user.username)

        return msg.SignupResp(session_key=session_key)

    def init_profile(self, request, context):
        user = self._get_user(context)

        # clean data
        full_name = request.full_name
        bio = request.bio

        # update user profile
        if user:
            profile = user.profile
            profile.save(full_name=full_name, bio=bio)
            return msg.ResultBool(success=True)
        else:
            msg.ResultBool(success=False)

    def login(self, request, context):
        session_key = None

        if self._session_is_active(context):
            # clean data
            username = str.lower(request.username)
            raw_password = request.raw_password

            # create new session for user
            user = authenticate(username=username, password=raw_password)
            if user:
                session_key = self._create_session()
            else:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Username or password is incorrect."
                                    "\n"
                                    "if you've forgotten your username or password, we can help you get back into your "
                                    "account")
        else:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("This account is already logged in from another device.")

        return msg.LoginResp(session_key=session_key)

    def logout(self, request, context):

        # delete active session
        if self._session_is_active(context):
            self._delete_session(context)
            return msg.ResultBool(success=True)
        else:
            return msg.ResultBool(success=False)

    def is_logged_in(self, request, context):
        return msg.ResultBool(success=self._session_is_active(context))

    def is_username_available(self, request, context):
        username = str.lower(request.username)

        # check username
        try:
            self._validate_username(username=username)
            return msg.ResultBool(success=True)

        except ValidationError as e:
            context.set_code(e.code)
            context.set_details(e.message)

        return msg.ResultBool(success=False)

    def is_email_available(self, request, context):
        email = str.lower(request.email)

        # check email
        try:
            self._validate_email(email=email)
            return msg.ResultBool(success=True)
        except ValidationError as e:
            context.set_code(e.code)
            context.set_details(e.message)

        return msg.ResultBool(success=False)

    def change_username(self, request, context):
        user = self._get_user(context)

        # clean data
        username = str.lower(request.username)

        try:
            self._validate_username(username=username)
            user.save(username=username)
            return msg.ResultBool(success=True)

        except ValidationError as e:
            context.set_code(e.code)
            context.set_details(e.message)

        return msg.ResultBool(success=False)

    # def get_file(self, request, context):
    #     file_path = os.path.join(BASE_DIR, "a.MP4")
    #     with open(file_path, 'rb') as file:
    #         # for chunk in file.read(64):
    #         yield msg.Chunk(blob=file.read())

    @classmethod
    def _get_user(cls, context):
        auth_meta_keys = settings.auth_meta_keys
        metadata = dict(context.invocation_metadata)
        session_key = metadata[auth_meta_keys["auth_session_key"]]

        session = Session.objects.get(pk=session_key)
        data = session.get_decoded()

        return User.objects.get(pk=data[auth_meta_keys.get("auth_user_key")])

    @classmethod
    def _create_session(cls, user=None):
        auth_meta_keys = settings.auth_meta_keys
        client_meta_keys = settings.client_meta_key
        session = SessionStore()
        session[auth_meta_keys.get("auth_key")] = \
            auth_meta_keys.get("auth_value") if user else auth_meta_keys.get("anonymous_value")
        if user:
            session[auth_meta_keys.get("auth_user_key")] = user.id
            session[auth_meta_keys.get("auth_client_state")] = True
        session[client_meta_keys.get("client_last_seen")] = now().timestamp()
        session.create()
        return session.session_key

    @classmethod
    def _delete_session(cls, context):
        metadata = dict(context.invocation_metadata)
        session_key = metadata[settings.auth_meta_keys.get("auth_session_key")]
        Session.objects.get(pk=session_key).delete()

    @classmethod
    def _session_is_active(cls, context):
        metadata = dict(context.invocation_metadata)
        auth_meta_keys = settings.auth_meta_keys

        session_key = metadata[auth_meta_keys.get("auth_session_key")]
        session = Session.objects.get(pk=session_key)
        data = session.get_decoded()

        return data[auth_meta_keys.get("auth_client_state")]

    @classmethod
    def _validate_username(cls, username):
        # check validation username
        try:
            cls.username_validator(username)
        except ValidationError as e:
            raise ValidationError(e.message, grpc.StatusCode.FAILED_PRECONDITION)

        # check username is available
        try:
            old_user = User.objects.get(username=username)
            raise ValidationError(message="Username is not available.", code=grpc.StatusCode.ALREADY_EXISTS)
        except User.DoesNotExist:
            pass

    @classmethod
    def _validate_email(cls, email):
        # check validation email
        try:
            cls.email_validator(email)
        except ValidationError as e:
            raise ValidationError(e.message, grpc.StatusCode.FAILED_PRECONDITION)

        # check email is available
        try:
            old_user = User.objects.get(email=email)
            raise ValidationError(message="Email is not available.", code=grpc.StatusCode.ALREADY_EXISTS)
        except User.DoesNotExist:
            pass
