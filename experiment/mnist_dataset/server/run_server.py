import os
import pause
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import dotenv
from time import sleep
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)
dotenv.load_dotenv()

from asynfed.server.server import Server
from asynfed.server.strategies import AsynFL


conf = {
    "server_id": "test_server_id",
    "bucket_name": "hellothisisnewbucket2",
    "queue_consumer": {
        "queue_exchange": 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_consumer',
        'routing_key': 'server.#',
        'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
    },
    "queue_producer": {
        "queue_exchange": 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_queue',
        'routing_key': 'client.#',
        'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
    }
}


scheduler = BackgroundScheduler()
strat = AsynFL()
server = Server(strat, conf)
server.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
