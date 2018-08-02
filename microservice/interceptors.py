"""Interceptor that authenticate users."""

import datetime
import grpc
import logging
from django.contrib.sessions.backends.cached_db import SessionStore
from django.contrib.sessions.models import Session
from django.utils.timezone import now

from tripmedia import settings

logger = logging.getLogger(__name__)


def _unary_unary_rpc_terminator(code, details):
    def terminate(ignored_request, context):
        context.abort(code, details)

    return grpc.unary_unary_rpc_method_handler(terminate)


class AuthenticateInterceptor(grpc.ServerInterceptor):
    """
    Check header of each coming request and check session_key header key in metadata.
    if session_key exist in db and has access to send request, this client is authenticated
    """

    def __init__(self, ignored_method):
        self._ignored_method = ignored_method
        self._terminator = _unary_unary_rpc_terminator(grpc.StatusCode.UNAUTHENTICATED, "Access dined!")

    def intercept_service(self, continuation, handler_call_details):
        # check session data and check user login state
        try:
            session_key = ''
            metadata = dict(handler_call_details.invocation_metadata)
            print(metadata)
            if 'session_key' in metadata:
                session_key = metadata['session_key']

            print(session_key)
            session = Session.objects.get(pk=session_key)

            data = session.get_decoded()
            if all([data['_auth'] == settings.AUTH_USER_META_VALUE,
                    data['_auth_logged_in'],
                    ]):
                # update last seen date in session
                session_store = SessionStore(session_key)
                session_store['_auth_last_request'] = now().timestamp()
                session_store.save()

                return continuation(handler_call_details)

        except Session.DoesNotExist:
            print("Session does not exist")

        # method_name = str.split(handler_call_details.method, '/')[-1:][0]
        method_name = continuation(handler_call_details).unary_unary.__name__

        if method_name in self._ignored_method:
            return continuation(handler_call_details)

        return self._terminator


def log_errors(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kw):
        metadata = {'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
        servicer_context = args[2]
        metadata.update(dict(servicer_context.invocation_metadata()))
        print(metadata)
        try:
            result = func(*args, **kw)
        except Exception as e:
            logger.error(e, exc_info=True, extra=metadata)
            if servicer_context:
                servicer_context.set_details(str(e))
                servicer_context.set_code(grpc.StatusCode.UNKNOWN)
            # TODO: need to return an appropriate response type here
            # Currently this will raise a serialization error on the server-side
            return None
        else:
            return result

    return wrapper


class LoggingInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        print("Initializing logging interceptor")

    def intercept_service(self, continuation, handler_call_details):
        return continuation(handler_call_details)
