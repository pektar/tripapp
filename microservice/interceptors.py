"""Interceptor that authenticate users."""

import grpc
import logging

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

    def __init__(self):
        self._terminator = _unary_unary_rpc_terminator(grpc.StatusCode.INVALID_ARGUMENT, "Wrong header!")

    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        auth_meta_keys = settings.auth_meta_keys

        # get session key from header if exists
        if auth_meta_keys.get("auth_session_key") in metadata:
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
            logger.info("%s SK/%s" % (called_method, metadata[settings.auth_meta_keys.get("auth_session_key")]))
        except Exception as key:
            logger.error("request has no %s in its header" % key)

        return continuation(handler_call_details)
