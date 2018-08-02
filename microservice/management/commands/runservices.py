import grpc
import os
import time
from concurrent import futures
from contextlib import contextmanager
from django.core.management import BaseCommand

from microservice import services
from microservice.interceptors import AuthenticateInterceptor, LoggingInterceptor
from microservice.rpc import server_api_pb2_grpc as rpc
from tripmedia.settings import BASE_DIR


class Command(BaseCommand):
    help = "Starts the GRPC server"

    @contextmanager
    def serve_forever(self, **kwargs):
        authenticate_validate = AuthenticateInterceptor(['signup', 'login', 'get_file'])
        logging_interceptor = LoggingInterceptor()
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=5),
                             interceptors=(authenticate_validate,))

        rpc.add_ServerApiServicer_to_server(services.ServerApi(), server)
        server.add_insecure_port("localhost:{}".format(8585))
        server.start()
        yield
        server.stop(0)

    def handle(self, *args, **options):
        with self.serve_forever():
            self.stdout.write("Running GRPC server on localhost:{}".format(8585))
            try:
                while True:
                    time.sleep(60 * 60 * 24)
            except KeyboardInterrupt:
                pass
