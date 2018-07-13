import grpc
import time
from concurrent import futures
from contextlib import contextmanager
from django.apps import AppConfig

from account.api.account.account_service import AccountService, account_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


@contextmanager
def serve_forever():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    account_pb2_grpc.add_AccountServiceServicer_to_server(AccountService(), server)
    server.add_insecure_port('localhost:50051')
    server.start()
    yield
    server.stop(0)


class AccountConfig(AppConfig):
    name = 'account'

    # def __init__(self, app_name, app_module):
    #     super().__init__(app_name, app_module)
    #     self.style = None
    #
    # def ready(self):
    #     with serve_forever():
    #         try:
    #             while True:
    #                 time.sleep(_ONE_DAY_IN_SECONDS)
    #         except KeyboardInterrupt:
    #             pass
