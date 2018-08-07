import grpc
import logging
from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.timezone import now

from account.models import User, UserConnection, ConnectionType
from account.validators import UsernameValidator
from microservice.decorators import grpc_require_auth, grpc_check_user_state
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
            session_key = self._create_session(user=user)
            user_summary = msg.UserSummary(user_id=user.id, username=user.username)
            logger.debug("Successfully user created, User:%s" % user.username)
            return msg.SignupResp(session_key=session_key, user_summary=user_summary)

        return msg.SignupResp(session_key=session_key)

    @grpc_require_auth
    def init_profile(self, request, context):
        user = self._get_user(context)

        # clean data
        full_name = request.full_name
        bio = request.bio

        # update user profile
        if user:
            profile = user.profile
            profile.full_name = full_name
            profile.bio = bio
            profile.save()
            return msg.ResultBool(success=True)
        else:
            msg.ResultBool(success=False)

    @grpc_check_user_state
    def login(self, request, context):
        session_key = None

        #  clean data
        username = str.lower(request.username)
        raw_password = request.raw_password

        # create new session for user
        user = authenticate(username=username, password=raw_password)
        if user:
            session_key = self._create_session(user=user)
        else:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Username or password is incorrect."
                                "\n"
                                "if you've forgotten your username or password, we can help you get back into your "
                                "account")

        return msg.LoginResp(session_key=session_key)

    @grpc_require_auth
    def logout(self, request, context):
        # delete active session
        if self._session_is_active(context):
            self._delete_session(context)
            return msg.ResultBool(success=True)
        else:
            return msg.ResultBool(success=False)

    @grpc_require_auth
    def is_logged_in(self, request, context):
        return msg.ResultBool(success=self._session_is_active(context))

    @grpc_require_auth
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

    @grpc_require_auth
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

    @grpc_require_auth
    def change_username(self, request, context):
        user = self._get_user(context)

        # clean data
        username = str.lower(request.username)

        try:
            self._validate_username(username=username)
            user.username = username
            user.save()
            return msg.ResultBool(success=True)

        except ValidationError as e:
            context.set_code(e.code)
            context.set_details(e.message)

        return msg.ResultBool(success=False)

    @grpc_require_auth
    def change_profile(self, request, context):
        user = self._get_user(context)

        # clean_data
        full_name = request.full_name
        bio = request.bio

        # change user profile
        if user:
            profile = user.profile
            profile.full_name = full_name
            profile.bio = bio
            profile.save()
            return msg.ResultBool(success=True)
        else:
            return msg.ResultBool(sucess=False)

    @grpc_require_auth
    def get_user(self, request, context):
        user = self._get_user(context)

        # clean data
        target_id = request.user_id

        # check user is self
        if user.id == target_id:
            target = user
            is_self = True
        else:
            try:
                target = User.objects.get(pk=target_id)
                is_self = False
            except User.DoesNotExist:
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details("User profile is not exist.")
                return msg.GetUserResp()

        # set data to response
        username = target.username
        full_name = target.profile.full_name
        bio = target.profile.bio
        # get counts
        counts = msg.Count(followers=target.profile.count_followers(), following=target.profile.count_following(),
                           posts=10)
        return msg.GetUserResp(is_self=is_self, user_id=target.id, username=username, full_name=full_name,
                               bio=bio, counts=counts)

    @grpc_require_auth
    def get_follower(self, request, context):
        user = self._get_user(context)
        target_id = request.user_id
        for relation in UserConnection.objects.filter(one__user_id=target_id,
                                                      type=ConnectionType.FOLLOW.name).iterator(20):
            yield msg.GetFollowerResp(
                follower=msg.UserSummary(user_id=relation.user.user.id, username=relation.user.user.username))

    @grpc_require_auth
    def get_following(self, request, context):
        user = self._get_user(context)
        user_id = user.id
        for relation in UserConnection.objects.filter(user_id=user_id,
                                                      type=ConnectionType.FOLLOW.name).iterator(20):
            yield msg.GetFollowerResp(
                follower=msg.UserSummary(user_id=relation.user.user.id, username=relation.user.user.username))

    # def get_file(self, request, context):
    #     file_path = os.path.join(BASE_DIR, "a.MP4")
    #     with open(file_path, 'rb') as file:
    #         # for chunk in file.read(64):
    #         yield msg.Chunk(blob=file.read())

    @classmethod
    def _get_user(cls, context):
        auth_meta_keys = settings.auth_meta_keys
        metadata = dict(context.invocation_metadata())
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
        metadata = dict(context.invocation_metadata())
        session_key = metadata[settings.auth_meta_keys.get("auth_session_key")]
        Session.objects.get(pk=session_key).delete()

    @classmethod
    def _session_is_active(cls, context):
        metadata = dict(context.invocation_metadata())
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
