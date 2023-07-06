
import os
import sys
from dotenv import load_dotenv
import pause
from apscheduler.schedulers.background import BackgroundScheduler

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)

from asynfed.client.algorithms import ClientAsyncFl
from asynfed.client.frameworks.tensorflow import TensorflowFramework

from experiment.cifar_dataset.client.resnet18 import Resnet18
from experiment.cifar_dataset.client.data_preprocessing import preprocess_dataset

load_dotenv()
scheduler = BackgroundScheduler()

config = {
    "client_id": "tester",
    "role": "test",
    "queue_consumer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_queue',
        'routing_key': 'client.#',
        'end_point': 'amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu'
    },
    "queue_producer": {
        'exchange_name': 'asynfl_exchange',
        'exchange_type': 'topic',
        'queue_name': 'server_consumer',
        'routing_key': 'server.#',
        'end_point': "amqps://gocktdwu:jYQBoATqKHRqXaV4O9TahpPcbd8xjcaw@armadillo.rmq.cloudamqp.com/gocktdwu"
    },
    "testing_params": {
        # setup differently for different device
        "gpu_index": 0,
        "batch_size": 128,
    }

}

import tensorflow as tf
print("*" * 20)
if tf.config.list_physical_devices('GPU'):
    tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[config["testing_params"]['gpu_index']], 'GPU')
    print("Using GPU: ", tf.config.list_physical_devices('GPU')[config["testing_params"]['gpu_index']])
else:
    print("Using CPU")
print("*" * 20)

# ------------oOo--------------------
# Preprocessing data
default_testing_dataset_path = "../../../data/cifar_data/test_set.pickle"
test_ds, data_size = preprocess_dataset(default_testing_dataset_path, training = False)
# ------------oOo--------------------

print("-" * 20)
print("-" * 20)
print(f"Tester with datasize of {data_size}")
print("-" * 20)
print("-" * 20)

# Define model
model = Resnet18(input_features= (32, 32, 3), 
                 output_features= 10)
                #  decay_steps=int(Config.EPOCH * data_size / Config.BATCH_SIZE))
# Define framework
tensorflow_framework = TensorflowFramework(model=model, 
                                           data_size= data_size, 
                                           train_ds= None, 
                                           test_ds= test_ds, 
                                           role= "test",
                                           config=config)


# tf_client = ClientAsyncFl(model=tensorflow_framework,config=config)
tf_client = ClientAsyncFl(model=tensorflow_framework, config=config, save_log=False)

tf_client.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
