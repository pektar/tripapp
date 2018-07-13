"""
WSGI config for tripmedia project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import grpc
import os
import time
from concurrent import futures
from contextlib import contextmanager
from django.core.wsgi import get_wsgi_application
from sys import stdout

from account.api.account import account_pb2_grpc
from account.api.account.account_service import AccountService

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tripmedia.settings")

application = get_wsgi_application()

