import os
import sys
root = os.path.dirname(os.getcwd())
sys.path.append(root)


import tensorflow as tf
from resnet18 import Resnet18

import numpy as np

tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[0], 'GPU')

def get_mean_and_std(images):
    """Compute the mean and std value of dataset."""
    mean = np.mean(images, axis=(0, 1, 2))
    std = np.std(images, axis=(0, 1, 2))
    return mean, std

def normalize(images, mean, std):
    """Normalize data with mean and std."""
    return (images - mean) / std

(x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
data_size = len(x_train)

mean, std = get_mean_and_std(x_train)
x_train = normalize(x_train, mean, std)
x_test = normalize(x_test, mean, std)


from data_preprocessing import get_datagen

datagen = get_datagen()
datagen.fit(x_train)

y_train = tf.keras.utils.to_categorical(y_train, 10)
y_test = tf.keras.utils.to_categorical(y_test, 10)

epoch = 200
batch_size = 128
decay_steps = epoch * data_size / batch_size
learning_rate = 0.1
lambda_value = 5e-4


model = Resnet18(num_classes= 10)

# Set the learning rate and decay steps
learning_rate_fn = tf.keras.experimental.CosineDecay(learning_rate, decay_steps=decay_steps)

# Create the SGD optimizer with L2 regularization
optimizer = tf.keras.optimizers.SGD(learning_rate=learning_rate_fn, momentum=0.9)


def custom_loss_with_l2_reg(y_true, y_pred):
    # def loss(y_true, y_pred):
    l2_loss = tf.add_n([tf.nn.l2_loss(w) for w in model.trainable_weights])
    return tf.keras.losses.categorical_crossentropy(y_true, y_pred) + lambda_value * l2_loss


# Build the model
model.build(input_shape=(None, 32, 32, 3))

# Compile the model
model.compile(optimizer=optimizer, loss=custom_loss_with_l2_reg, metrics=['accuracy'],
            loss_weights=None, weighted_metrics=None, run_eagerly=None,
            steps_per_execution=None)


# # Apply L2 regularization to applicable layers
# for layer in model.layers:
#     if isinstance(layer, tf.keras.layers.Conv2D) or isinstance(layer, tf.keras.layers.Dense):
#         layer.kernel_regularizer = regularizer
#     if hasattr(layer, 'bias_regularizer') and layer.use_bias:
#         layer.bias_regularizer = regularizer

from keras.callbacks import EarlyStopping

es = EarlyStopping(patience= 200, restore_best_weights=True, monitor="val_acc")
#I did not use cross validation, so the validate performance is not accurate.
STEPS = len(x_train) / batch_size

history = model.fit(datagen.flow(x_train, y_train, batch_size = batch_size), steps_per_epoch=STEPS, batch_size = batch_size, epochs=200, validation_data=(x_test, y_test),callbacks=[es])