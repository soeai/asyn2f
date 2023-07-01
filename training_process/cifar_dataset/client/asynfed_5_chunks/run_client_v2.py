
import os
import sys
import pause
from apscheduler.schedulers.background import BackgroundScheduler
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)

from asynfed.client_v2.algorithms.client_asyncfL import ClientAsyncFl
from asynfed.client_v2.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from asynfed.commons.conf import Config
from training_process.cifar_dataset.client.resnet18 import Resnet18
from data_preprocessing import preprocess_dataset

from dotenv import load_dotenv
load_dotenv()
scheduler = BackgroundScheduler()

config = {
    "client_id": "002",
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
    "training_params": {
        "qod": 0.45,
        "batch_size": 128,
        "epoch": 10,
        "gpu_index": 0,
        "chunk_index": 0,
        "dataset": "cifar10",
        "model": "resnet18",
        "tracking_point": 1000,
        "sleeping_time": 10,
        "learning_rate": 1e-3,
        "delta_time": 0.1,
        "regularization": "l2",
        "lambda_value": 1e-4,
    }
}

# ------------oOo--------------------
# Preprocessing data
default_training_dataset_path = "../../../data/cifar_data/5_chunks/chunk_2.pickle"
default_testing_dataset_path = "../../../data/cifar_data/test_set.pickle"
training_dataset_path = f"../../../data/cifar_data/5_chunks/chunk_5.pickle"
# if os.getenv("cifar_train_dataset_path"):
#     training_dataset_path = os.getenv("cifar_train_dataset_path")
# else:
#     training_dataset_path = default_training_dataset_path
    

# train_ds, data_size = preprocess_dataset(training_dataset_path, training = True)
# test_ds, _ = preprocess_dataset(testing_dataset_path, training = False)
train_ds, data_size = preprocess_dataset(training_dataset_path, batch_size = 128, training = True)
test_ds, _ = preprocess_dataset(default_testing_dataset_path, training = False)
# train_ds, data_size = preprocess_dataset("training_process/data/cifar_data/5_chunks/chunk_2.pickle", training = True)
# test_ds, _ = preprocess_dataset("training_process/data/cifar_data/test_set.pickle", training = False)
# ------------oOo--------------------

print("-" * 20)
print("-" * 20)
print(f"Begin training proceess with data size of {data_size}")
print("-" * 20)
print("-" * 20)

# Define model
model = Resnet18(input_features= (32, 32, 3), 
                 output_features= 10,
                 lr=config['training_params']['learning_rate'],
                 decay_steps=int(Config.EPOCH * data_size / Config.BATCH_SIZE))
# Define framework
tensorflow_framework = TensorflowFramework(model=model, 
                                           data_size= data_size, 
                                           train_ds= train_ds, 
                                           test_ds= test_ds, 
                                           config=config)


tf_client = ClientAsyncFl(model=tensorflow_framework,config=config)
tf_client.start()
scheduler.start()
pause.days(1) # or it can anything as per your need
