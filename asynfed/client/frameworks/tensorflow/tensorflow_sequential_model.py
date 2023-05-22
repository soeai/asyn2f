from abc import abstractmethod
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Flatten, Conv2D, AveragePooling2D


# This abstract class is intended to help user 
# how to create their own tensorflow sequential model
# that can run on our flatform

# 

# sample of how to create a tensorflow sequential can be found at target_user/client/Lenet.py
class TensorflowSequentialModel(Model):
    # def __init__(self):
    def __init__(self, input_features, output_features):
        super().__init__()
        self.create_model(input_features, output_features)
        # loss
        self.loss_object = self.create_loss_object()
        # optimizer
        self.optimizer = self.create_optimizer()
        # metric
        self.train_performance, self.train_loss = self.create_train_metric()
        self.test_performance, self.test_loss = self.create_test_metric()


    @abstractmethod
    def create_model(self, input_features, output_features):
        # a sequential tensorflow model consists of multiple layers 
        # each layer is an instance of class tensorflow.keras.layers.Layer
        # it can be the already defined layer as Dense, Flatten, Conv2D
        # or a custom layered defined by user
        # input_features variable is the input for the first layer
        # output_features variable is the output for the last layer
        # a non return function
        pass

    @abstractmethod
    def call(self, x):
        # define the order of layers in which we pass the input feature (x) 
        # from the first layer toward the last one
        pass
    

    @abstractmethod
    def create_loss_object(self):
        # must return a loss object
        # several loss objects can be found in tf.keras.losses 
        # or can be a customized one
        # below is how to use Categorical Crossentropy loss object defined by tensorflow
        # self.loss_object = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
        pass 
    
    @abstractmethod
    def create_optimizer(self):
        # must return an optimizer object
        # optimizers in tf.keras.optimizers
        # or define a personalized one
        # below is how to use Adam optimizer defined by tensorflow
        # self.optimizer = tf.keras.optimizers.Adam()
        pass

    @abstractmethod
    def create_train_metric(self):
        # must return a train_performance object and a train_loss object correspondingly 
        # metric in tf.keras.metrics
        # or can be self defined
        # below is how to use Mean loss and Categorical Accuracy object provided by tensorflow
        # self.train_loss = tf.keras.metrics.Mean(name='train_loss')
        # self.train_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy')
        pass

    @abstractmethod
    def create_test_metric(self):
        # if there is a test dataset
        # must return a test_performance object and a test_loss object correspondingly 
        pass 

    @abstractmethod
    def get_train_performance(self):
        # return a float number
        pass

    @abstractmethod
    def get_train_loss(self):
        # return a float number
        pass

    @abstractmethod
    def get_test_performance(self):
        # return a float number
        pass

    @abstractmethod
    def get_test_loss(self):
        # return a float number
        pass


