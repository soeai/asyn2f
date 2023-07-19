import os, sys
import pause
from apscheduler.schedulers.background import BackgroundScheduler
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)

from asynfed.client.client import Client
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from asynfed.client.algorithms.client_asyncfL import ClientAsyncFl
from data_preprocessing import *
from Lenet import LeNet
from dotenv import load_dotenv
load_dotenv()


scheduler = BackgroundScheduler()
config = {
    "client_id": "002",
    "queue_consumer": {
        "queue_exchange": 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_queue',
        'routing_key': 'client.#',
        'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
    },
    "queue_producer": {
        "queue_exchange": 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_consumer',
        'routing_key': 'server.#',
        'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
    }
}
print(root, os.getenv("mnist_x_train_path"))
train_images_path = os.path.join(root, os.getenv("mnist_x_train_path"))
train_labels_path = os.path.join(root, os.getenv("mnist_y_train_path"))
test_images_path = os.path.join(root, os.getenv("mnist_x_test_path"))
test_labels_path = os.path.join(root, os.getenv("mnist_y_test_path"))



# preprocessing data to be ready for low level tensorflow training process
train_ds, data_size = preprocess_dataset(images_path= train_images_path, labels_path= train_labels_path, training= True)
test_ds, _ = preprocess_dataset(images_path= test_images_path, labels_path= test_labels_path, training= False)
# ------------oOo--------------------
# define model
model = LeNet()
# define framework
tensorflow_framework = TensorflowFramework(model = model, epoch= 200, data_size= data_size, train_ds= train_ds, test_ds= test_ds, delta_time= 10000, qod= 0.45)

tf_client = ClientAsyncFl(model=tensorflow_framework, config=config)
tf_client.start()
#
# class NewClient(Client):
#     def train(self):
#         pass
# client = NewClient(config)
# client.start()
#
scheduler.start()
pause.days(1) # or it can anything as per your need
