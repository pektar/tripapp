import grpc
import time
from concurrent import futures
from contextlib import contextmanager
from django.core.management.commands.runserver import BaseRunserverCommand

from account.api.account import account_pb2_grpc, account_service

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


@contextmanager
def serve_forever():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    account_pb2_grpc.add_AccountServiceServicer_to_server(account_service.AccountService(), server)
    server.add_insecure_port('localhost:8585')
    server.start()
    yield
    server.stop(0)


class Command(BaseRunserverCommand):
    help = 'api server'

    def handle(self, *args, **options):
        # for i in range(10000, 10050):
        #     user = User(username='username%d' % i, first_name='First%d' % i, last_name='Last%d' % i,
        #                 password='asdfghjkl%d' % i,
        #                 last_login=datetime.datetime.now(),
        #                 is_active=True, is_staff=1, is_superuser=0)
        #     user.save()
        #     print(User.objects.get(username='username%d' % i))

        with serve_forever():
            self.stdout.write(self.style.SUCCESS('Successfully started grpc server '))
            try:
                while True:
                    time.sleep(_ONE_DAY_IN_SECONDS)
            except KeyboardInterrupt:
                pass
