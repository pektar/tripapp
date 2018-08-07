import grpc
from django.contrib.sessions.models import Session

from tripmedia import settings


def grpc_require_auth(rpc_method):
    def check_session(*args, **kwargs):
        session = None
        session_key = ''

        request = args[1]
        context = args[2]
        metadata = dict(context.invocation_metadata())

        auth_meta_keys = settings.auth_meta_keys

        # get session key from header if exists
        if auth_meta_keys.get("auth_session_key") in metadata:
            session_key = metadata[auth_meta_keys.get("auth_session_key")]
        else:
            session_key = ''
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Access dined!")
            return

        # get request session
        try:
            session = Session.objects.get(pk=session_key)
            data = session.get_decoded()
            if all([
                data[auth_meta_keys.get("auth_key")] ==
                auth_meta_keys.get("anonymous_value") or auth_meta_keys.get("auth_value"),
            ]):
                return rpc_method(*args, **kwargs)
        except Session.DoesNotExist:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Access dined!")

        return

    return check_session


def grpc_check_user_state(rpc_method):
    def has_active_session(*args, **kwargs):
        context = args[2]
        metadata = dict(context.invocation_metadata())
        auth_meta_keys = settings.auth_meta_keys
        session_key = metadata.get(auth_meta_keys.get("auth_session_key"))

        # check if session key is set in header
        if auth_meta_keys.get("auth_session_key") in metadata \
                and isinstance(metadata.get(auth_meta_keys.get("auth_session_key")), str):
            try:
                session = Session.objects.get(pk=session_key)
                data = session.get_decoded()
                if data[auth_meta_keys.get("auth_client_state")]:
                    context.abort(grpc.StatusCode.ALREADY_EXISTS, "Another device is logged in with this user.")
                    return
                else:
                    session.delete()
                    context.abort(grpc.StatusCode.UNAUTHENTICATED, "Access dined!")
                    return
            except Session.DoesNotExist as key:
                # ignore session key in header
                return rpc_method(*args, **kwargs)

        return rpc_method(*args, **kwargs)

    return has_active_session
