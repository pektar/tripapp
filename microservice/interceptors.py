"""Interceptor that authenticate users."""

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

            if 'session-key' in metadata:
                session_key = metadata['session-key']

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
            logger.debug("session-key is not available")

        # method_name = str.split(handler_call_details.method, '/')[-1:][0]
        method_name = continuation(handler_call_details).unary_unary.__name__

        if method_name in self._ignored_method:
            return continuation(handler_call_details)

        return self._terminator


class LoggingInterceptor(grpc.ServerInterceptor):

    def intercept_service(self, continuation, handler_call_details):
        called_method = handler_call_details.method
        metadata = dict(handler_call_details.invocation_metadata)

        logger.debug("client call %s" % called_method)

        # logging request
        try:
            logger.debug("%s" % metadata["user-agent"])
            logger.info("%s SK/%s" % (called_method, metadata["session-key"]))
        except Exception as key:
            logger.error("request has no %s in its header" % key)

        return continuation(handler_call_details)
