import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))
from asynfed.commons.conf import Config
from asynfed.server.server import Server
# from asynfed.server.strategies import Strategy
from asynfed.server.strategies.AsynFL import AsynFL
from dotenv import load_dotenv

load_dotenv()
# queue
Config.QUEUE_URL = os.getenv("queue_url")
# storage
Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")

print(os.getenv("access_key"))
print(os.getenv("secret_key"))

# local saving directories
# Config.TMP_LOCAL_MODEL_FOLDER = os.getenv("local_model_folder")
# Config.TMP_GLOBAL_MODEL_FOLDER = os.getenv("global_model_folder")
# Config.LOG_PATH = os.getenv("log_path")

if os.getenv("bucket_name"):
    bucket_name = os.getenv("bucket_name")
else:
    bucket_name= 'test-client-tensorflow-mnist'

strategy = AsynFL()
fedasync_server = Server(strategy, t=60, test = True, bucket_name= bucket_name)
fedasync_server.run()
