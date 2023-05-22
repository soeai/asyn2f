import tensorflow as tf
# from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Flatten, Conv2D, AveragePooling2D
from .tensorflow_sequential_model import TensorflowSequentialModel

# from fedasync.client.ModelWrapper import ModelWrapper
from ...ModelWrapper import ModelWrapper

class TensorflowFramework(ModelWrapper):
    # Tensorflow Model must be an inheritant of class tensorflow.keras.Model
    # model, data_size, train_ds is required
    # test_ds is optional
    def __init__(self, model: TensorflowSequentialModel, data_size, train_ds, test_ds):
        super().__init__()
        self.model = model
        # model must have an optimizer, a loss object, and trainining metric 
            # model.optimizer
            # model.loss_object
            # model.train_performance
            # model.train_loss
        # if there is a test_ds, must define testing metrics 
        # similar as the way we define training metrics
        # model must have function to get train_performanced and train_loss as numerical data
        # model.get_train_performanced()
        # model.get_train_loss()
        # if there is a test_ds, must define similar functions 
        # to get test_performanced and train_performanced as numerical data
        # model detail instruction on how to create a sequential model 
        # for tensorflow framework can be found at tensorflow_sequential_model.py
        self.data_size = data_size
        self.train_ds = train_ds
        if test_ds:
            self.test_ds = test_ds

    def set_weights(self, weights):
        return self.model.set_weights(weights)
    
    def get_weights(self):
        return self.model.get_weights()
    
    def fit(self, x, y):
        self.train_step(x, y)
        return self.model.get_train_performance(), self.model.get_train_loss()
    
    def evaluate(self, x, y):
        self.test_step(x, y)
        return self.model.get_test_performance(), self.model.get_test_loss()

    @tf.function
    def train_step(self, images, labels):
        with tf.GradientTape() as tape:
            # training=True is only needed if there are layers with different
            # behavior during training versus inference (e.g. Dropout).
            predictions = self.model(images, training=True)
            loss = self.model.loss_object(labels, predictions)
        gradients = tape.gradient(loss, self.model.trainable_variables)
        self.model.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))
        self.model.train_loss(loss)
        self.model.train_performance(labels, predictions)


    @tf.function
    def test_step(self, images, labels):
    # training=False is only needed if there are layers with different
    # behavior during training versus inference (e.g. Dropout).
        predictions = self.model(images, training=False)
        t_loss = self.model.loss_object(labels, predictions)
        self.model.test_loss(t_loss)
        self.model.test_performance(labels, predictions)


    # def set_pretrained_weights(self, weights, train_ds):
    #     num_of_layers = len(self.model.get_weights())
    #     if num_of_layers < len(weights):
    #         for images, labels in train_ds:
    #             self.train_step(images, labels)
    #             break
    #     self.set_weights(weights)
