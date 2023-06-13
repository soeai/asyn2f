import tensorflow as tf


from tensorflow.keras.layers import Dense, Flatten, Conv2D, AveragePooling2D

from asynfed.client.frameworks.tensorflow.tensorflow_sequential_model import TensorflowSequentialModel

class LeNet(TensorflowSequentialModel):
    def __init__(self, input_features= (32, 32, 1), output_features =10):
        super().__init__(input_features= input_features, output_features= output_features)

    def create_model(self, input_features, output_features):
        self.conv1 = Conv2D(6, kernel_size=(5, 5), strides=(1, 1), activation='tanh', input_shape= input_features,
                            padding="valid")
        self.avgpool1 = AveragePooling2D(pool_size=(2, 2), strides=(2, 2), padding='valid')
        self.conv2 = Conv2D(16, kernel_size=(5, 5), strides=(1, 1), activation='tanh', padding='valid')
        self.avgpool2 = AveragePooling2D(pool_size=(2, 2), strides=(2, 2), padding='valid')
        self.flatten = Flatten()
        self.dense1 = Dense(120, activation='tanh')
        self.dense2 = Dense(84, activation='tanh')
        self.dense3 = Dense(output_features, activation='softmax')

    def call(self, x):
        x = self.conv1(x)
        x = self.avgpool1(x)
        x = self.conv2(x)
        x = self.avgpool2(x)
        x = self.flatten(x)
        x = self.dense1(x)
        x = self.dense2(x)
        x = self.dense3(x)
        return x
    
    def create_loss_object(self):
        loss_object = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
        return loss_object
    
    def create_optimizer(self):
        optimizer = tf.keras.optimizers.Adam()
        return optimizer

    def create_train_metric(self):
        train_performance = tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy')
        train_loss = tf.keras.metrics.Mean(name='train_loss')
        return train_performance, train_loss
    
    def create_test_metric(self):
        test_performance = tf.keras.metrics.SparseCategoricalAccuracy(name='test_accuracy')
        test_loss = tf.keras.metrics.Mean(name='test_loss')
        return test_performance, test_loss
    
    def get_train_performance(self):
        return float(self.train_performance.result())

    def get_train_loss(self):
        return float(self.train_loss.result())
    
    def get_test_performance(self):
        return float(self.train_performance.result())

    def get_test_loss(self):
        return float(self.test_loss.result())

