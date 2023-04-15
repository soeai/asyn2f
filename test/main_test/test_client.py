import sys
print('Python %s on %s' % (sys.version, sys.platform))
sys.path.extend(['/home/vtn_ubuntu/ttu/spring23/working_project/AsynFL'])

from fedasync.client.client_tensorflow import ClientTensorflow
import numpy as np
import tensorflow as tf
from tensorflow import keras

# Define a simple tensorflow model
model = tf.keras.Sequential([
    keras.layers.Dense(512, activation='relu', input_shape=(784,)),
    keras.layers.Dropout(0.2),
    keras.layers.Dense(10)
])
# Sample X_train
x_train = np.random.rand(320, 32, 32)
tf_client = ClientTensorflow(model=model, x_train=x_train, y_train=None, batch_size=32)
tf_client.run()
