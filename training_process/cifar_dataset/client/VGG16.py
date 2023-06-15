

import tensorflow as tf
from tensorflow.keras.layers import Model, Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from asynfed.client.frameworks.tensorflow.tensorflow_sequential_model import TensorflowSequentialModel

class VGG16(TensorflowSequentialModel):
# class VGG16(Model):
    def __init__(self, input_features=(32, 32, 3), output_features=10):
        super().__init__(input_features= input_features, output_features= output_features)

    def create_model(self, input_features, output_features):
        # First block
        self.conv1_1 = Conv2D(64, (3, 3), activation='relu', padding='same', input_shape= input_features)
        self.conv1_2 = Conv2D(64, (3, 3), activation='relu', padding='same')
        self.pool1 = MaxPooling2D((2, 2))

        # Second block
        self.conv2_1 = Conv2D(128, (3, 3), activation='relu', padding='same')
        self.conv2_2 = Conv2D(128, (3, 3), activation='relu', padding='same')
        self.pool2 = MaxPooling2D((2, 2))

        # Third block
        self.conv3_1 = Conv2D(256, (3, 3), activation='relu', padding='same')
        self.conv3_2 = Conv2D(256, (3, 3), activation='relu', padding='same')
        self.conv3_3 = Conv2D(256, (3, 3), activation='relu', padding='same')
        self.pool3 = MaxPooling2D((2, 2))

        # Fourth block
        self.conv4_1 = Conv2D(512, (3, 3), activation='relu', padding='same')
        self.conv4_2 = Conv2D(512, (3, 3), activation='relu', padding='same')
        self.conv4_3 = Conv2D(512, (3, 3), activation='relu', padding='same')
        self.pool4 = MaxPooling2D((2, 2))

        # Fifth block
        self.conv5_1 = Conv2D(512, (3, 3), activation='relu', padding='same')
        self.conv5_2 = Conv2D(512, (3, 3), activation='relu', padding='same')
        self.conv5_3 = Conv2D(512, (3, 3), activation='relu', padding='same')
        self.pool5 = MaxPooling2D((2, 2))

        # Dense layers
        self.flatten = Flatten()
        self.fc1 = Dense(4096, activation='relu')
        self.fc2 = Dense(4096, activation='relu')
        self.fc3 = Dense(output_features, activation='softmax')
        
        # Dense layers
        self.flatten = Flatten()
        self.fc1 = Dense(512, activation='relu')
        # randomly drop some nodes
        self.dropout1 = Dropout(0.4)
        self.fc2 = Dense(256, activation='relu')
        # randomly drop some nodes
        self.dropout2 = Dropout(0.4)
        self.fc3 = Dense(output_features, activation='softmax')
        

    def call(self, x):
        # first block
        x = self.conv1_1(x)
        x = self.conv1_2(x)
        x = self.pool1(x)

        # second block
        x = self.conv2_1(x)
        x = self.conv2_2(x)
        x = self.pool2(x)

        # third block
        x = self.conv3_1(x)
        x = self.conv3_2(x)
        x = self.conv3_3(x)
        x = self.pool3(x)

        # fourth block
        x = self.conv4_1(x)
        x = self.conv4_2(x)
        x = self.conv4_3(x)
        x = self.pool5(x)

        # fifth block
        x = self.conv5_1(x)
        x = self.conv5_2(x)
        x = self.conv5_3(x)
        x = self.pool5(x)

        # dense block
        x = self.flatten(x)
        x = self.fc1(x)
        x = self.dropout1(x)
        x = self.fc2(x)
        x = self.dropout2(x)
        
        return self.fc3(x)

    def create_loss_object(self):
        return tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

    def create_optimizer(self):
        return tf.keras.optimizers.SGD(learning_rate=0.001, momentum=0.9)

    def create_train_metric(self):
        return tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy'), tf.keras.metrics.Mean(name='train_loss')

    def create_test_metric(self):
        return tf.keras.metrics.SparseCategoricalAccuracy(name='test_accuracy'), tf.keras.metrics.Mean(name='test_loss')

    def get_train_performance(self):
        return float(self.train_performance.result())

    def get_train_loss(self):
        return float(self.train_loss.result())
    
    def get_test_performance(self):
        return float(self.test_performance.result())

    def get_test_loss(self):
        return float(self.test_loss.result())
