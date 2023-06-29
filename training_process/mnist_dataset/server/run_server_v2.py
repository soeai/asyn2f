import os
import pause
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import dotenv
from time import sleep
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)
dotenv.load_dotenv()

from asynfed.server.server_v2 import Server
from asynfed.server.strategies import AsynFL
from asynfed.commons.conf import Config


conf = {
    "server_id": "test_server_id",
    "bucket_name": "test_bucket",
    "queue_consumer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_consumer',
        'routing_key': 'server.#',
        'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
    },
    "queue_producer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_queue',
        'routing_key': 'client.#',
        'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
    }
}
Config.STORAGE_ACCESS_KEY = os.getenv("access_key")
Config.STORAGE_SECRET_KEY = os.getenv("secret_key")

scheduler = BackgroundScheduler()
strat = AsynFL()
server = Server(strat, conf)
server.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
