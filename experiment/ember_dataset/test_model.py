import json
import pandas as pd
import numpy as np
import pickle
import tensorflow as tf
from keras.layers import Dense, Conv1D, Activation, GlobalMaxPooling1D, Input, Embedding, Multiply
from keras.models import Model
from keras import backend as K
from keras import metrics
from keras.optimizers import SGD
import math
from sklearn.model_selection import train_test_split
import pickle

import os, sys
root = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.append(root)
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from experiment.ember_dataset.ember_model import EmberModel

def load_data(path):
    with open(path, "rb") as f:
        data = pickle.load(f)
    X, y = data[:, :-1], data[:, -1]
    return X, y


def generator(X, y, batch_size=128, shuffle=True):
    num_samples = len(X)
    indices = np.arange(num_samples)

    while True:
        if shuffle:
            np.random.shuffle(indices)
        for start in range(0, num_samples, batch_size):
            end = min(start + num_samples, batch_size)
            batch_indices = indices[start:end]
            batch_X = X[batch_indices]
            batch_y = y[batch_indices]
            yield batch_X, batch_y

def create_dataset(X, y, batch_size=128):
    ds = tf.data.Dataset.from_tensor_slices((X, y))
    ds = ds.shuffle(len(X)).batch(batch_size)
    ds = ds.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    return ds


if __name__ == '__main__':
    batch_size = 128
    epoch = 10

    train_path = "/home/student02/thaile/working_with_ember_dataset/data/chunk_0.pickle"
    test_path = "/home/student02/thaile/working_with_ember_dataset/data/test_set.pickle"
    X_train, y_train = load_data(train_path)
    X_test, y_test = load_data(test_path)
    train_ds = create_dataset(X_train, y_train, batch_size)
    test_ds = create_dataset(X_test, y_test, batch_size)
    data_size = len(X_train)

    with open('conf.json', 'r') as f:
        config = json.load(f)
    learning_rate_config = config.get('training_params').get('learning_rate_config', {}) 
    if learning_rate_config == {}:
        learning_rate_config['fix_lr'] = False
        learning_rate_config['lr'] = 0.1
        learning_rate_config['decay_steps'] = data_size * epoch / batch_size

    model = EmberModel(input_features= None, output_features= None, lr_config= learning_rate_config)
    tensorflow_framework = TensorflowFramework(model=model, data_size=data_size, train_ds=train_ds, test_ds=test_ds, config=config)

    for epoch in range(epoch):
        print(f"Enter epoch {epoch + 1}, learning rate = {tensorflow_framework.get_learning_rate()}")
        tensorflow_framework.model.train_loss.reset_states()
        tensorflow_framework.model.train_performance.reset_states()
        tensorflow_framework.model.test_loss.reset_states()
        tensorflow_framework.model.test_performance.reset_states()

        for images, labels in tensorflow_framework.train_ds:
            print(images.shape, labels.shape)
            train_acc, train_loss= tensorflow_framework.fit(images, labels)
        for test_images, test_labels in tensorflow_framework.test_ds:
            test_acc, test_loss = tensorflow_framework.evaluate(test_images, test_labels)
        print("Epoch {} - Train Acc: {:.2f} -- Train Loss {} Test Acc {:.2f}  Test Loss {}".format(epoch+1,train_acc * 100, train_loss,test_acc * 100,test_loss))




