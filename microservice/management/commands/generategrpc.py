import os
import shutil
from django.core.management import BaseCommand
from flashtext import KeywordProcessor
from grpc_tools import protoc

from tripmedia.settings import BASE_DIR


class Command(BaseCommand):
    help = "collect proto files and compile those"

    def handle(self, *args, **options):
        proto_files = {}
        # app_list = list(apps.all_models)

        # collect path of proto files
        self.stderr.write("Collect proto files...")
        protos_path = os.path.join(BASE_DIR, "microservice", "protos", "microservice")
        if os.path.exists(protos_path):
            for proto in os.listdir(protos_path):
                proto_files[protos_path] = os.path.join(protos_path, proto)
                self.stderr.write("\t✓ {} found.".format(proto))

        # create python path for messages
        python_out_path = os.path.join(BASE_DIR, "microservice", "message")
        if not os.path.exists(python_out_path):
            os.makedirs(python_out_path)
        else:
            shutil.rmtree(python_out_path)
            os.makedirs(python_out_path)

        # create grpc path for rpc
        grpc_path_out = os.path.join(BASE_DIR, "microservice", "rpc")
        if not os.path.exists(grpc_path_out):
            os.makedirs(grpc_path_out)
        else:
            shutil.rmtree(grpc_path_out)
            os.makedirs(grpc_path_out)

        # compile proto files
        self.stderr.write("Generate...")
        for proto_path, proto_file in proto_files.items():
            command = [
                          "grpc_tools.protoc",
                          "-I={}".format(proto_path),
                          "--python_out={}".format(python_out_path),
                          "--grpc_python_out={}".format(grpc_path_out),
                      ] + [proto_file]
            if protoc.main(command) != 0:
                self.stderr.write("Failed to generate {}".format(proto_file))
            else:
                self.stderr.write("\t✓ compiled {}".format(proto_file))

        self.stderr.write("✓ Generate completed")

        # correct "import" message in rpc files
        rpc_paths = {}
        for rpc in os.listdir(grpc_path_out):
            rpc_paths[rpc] = os.path.join(grpc_path_out, rpc)

        for rpc_name, rpc_file in rpc_paths.items():
            app_name = "_".join(rpc_name.split('_')[:-2])

            keyword_processor = KeywordProcessor()
            # keyword_processor.add_keyword(<unclean name>, <standardised name>)
            keyword_processor.add_keyword(
                'import {} as {}'
                    .format(app_name + "_pb2", app_name.replace("_", "__") + "__pb2"),
                'from microservice.message import {} as {}'
                    .format(app_name + "_pb2", app_name.replace("_", "__") + "__pb2"))

            with open(rpc_file, 'r') as old_file:
                new_code = keyword_processor.replace_keywords(old_file.read())
            with open(rpc_file, 'w') as new_file:
                new_file.write(new_code)
