import tensorflow as tf
import numpy as np
import gzip


import os
import sys
from dotenv import load_dotenv
load_dotenv()


root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
sys.path.append(root)




class TensorflowImageDataPreprocessing():
    def __init__(self, train_images_path: str, train_labels_path: str, height: int, width: int, batch_size = 32, shuffle_time = 10000, split = True, fract = 0.1, evaluate_images_path = None, evaluate_labels_path = None):
        self.train_ds = None
        self.test_ds = None
        self.evaluate_ds = None
        self.height = height
        self. width = width

        self.load_training_dataset(train_images_path, train_labels_path, batch_size, shuffle_time, split, fract = fract)
        if evaluate_images_path != None and evaluate_labels_path != None:
            self.load_evaluate_dataset(evaluate_images_path, evaluate_labels_path, batch_size)

    def load_training_dataset(self, train_images_path: str, train_labels_path: str, batch_size: int, shuffle_time: int, split: bool, fract):
        # Load the MNIST digit dataset files into numpy arrays
        with gzip.open(train_images_path, 'rb') as f:
            x = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, self.height, self.width)

        with gzip.open(train_labels_path, 'rb') as f:
            y = np.frombuffer(f.read(), np.uint8, offset=8)
        x = x / 255    
        # shape of x and y now: ((size, 28, 28), (size,))
        # Add a channels dimension
        x = x[..., tf.newaxis].astype("float32")
        # shape of x and y now: ((size, 28, 28, 1), (size,))

        # make it to be a smaller dataset
        # Take a portion of the whole dataset as a way to simulate various data owner behavior
        # start = 0
        # datasize = 3000
        # x = x[start: start + datasize]
        # y = y[start: start + datasize]
        
        if split:
            # split training dataset into train set and test set (user may not choose this option if its training dataset is too small)
            # Divide into training and testing set
            datasize = len(x)
            break_point = int(datasize * (1 - fract)) 
            x_train = x[: break_point]
            x_test = x[break_point: ]
            y_train = y[: break_point]
            y_test = y[break_point: ]

            # create ready datasets for training process
            # train_ds and test_ds type: tensorflow.python.data.ops.batch_op._BatchDataset
            self.train_ds = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(shuffle_time).batch(batch_size)
            self.test_ds = tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(batch_size)

        else:
            # create a ready dataset for training process
            # train_ds type: tensorflow.python.data.ops.batch_op._BatchDataset
            self.train_ds = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(shuffle_time).batch(batch_size)


    def load_evaluate_dataset(self, evaluate_images_path: str, evaluate_labels_path: str, batch_size: int):
        with gzip.open(evaluate_images_path, 'rb') as f:
            x = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, self.height, self.width)
        with gzip.open(evaluate_labels_path, 'rb') as f:
            y = np.frombuffer(f.read(), np.uint8, offset=8)

        x = x / 255    
        # shape of x and y now: ((size, 28, 28), (size,))
        # Add a channels dimension
        x = x[..., tf.newaxis].astype("float32")
        # shape of x and y now: ((size, 28, 28, 1), (size,))
        self.evaluate_ds = tf.data.Dataset.from_tensor_slices((x, y)).batch(batch_size)


from abc import abstractmethod, ABC


class ModelWrapper(ABC):
    # model, data_size, train_ds is require
    # test_ds is optional

    def __int__(self, model, data_size, qod, train_ds, test_ds):
        pass

    @abstractmethod
    # input: a list of several numpy arrays (corresponding to several layers)
    # expected result: set it to be the weights of the model
    def set_weights(self, weights):
        pass

    # output: return weights as a list of numpy array
    @abstractmethod
    def get_weights(self):
        pass

    # output: performance and loss
    @abstractmethod
    def fit(self, x, y):
        pass

    # output: precision and loss
    @abstractmethod
    def evaluate(self, x, y):
        pass


from tensorflow.keras import Model

'''
    - This is a reference of how user can defined a tensorflow model
        that can be used in our platform
    - users can use our abstract class to define their own model
        or they can design one by themselves
        as long as it is inherited from class ModelWarapper
        and satify all the requirements (at least provide data_size, train_ds, and 
        implement of all abstract functions)
    - more frameworks can be found at asynfed/client/frameworks directory
'''

class TensorflowFramework(ModelWrapper):
    # Tensorflow Model must be an inheritant of class tensorflow.keras.Model
    # model, data_size, train_ds is required
    # test_ds is optional
    def __init__(self, model: Model, data_size: int = 10, qod: float = 0.9, train_ds = None, test_ds = None):
        super().__init__()
        '''
        - model must have an optimizer, a loss object, and trainining metric 
            model.optimizer
            model.loss_object
            model.train_performance
            model.train_loss
        - if there is a test_ds, must define testing metrics 
            similar as the way we define training metrics
        - model must have function to get train_performanced and train_loss as numerical data
            model.get_train_performanced()
            model.get_train_loss()
        - if there is a test_ds, must define similar functions 
            to get test_performanced and train_performanced as numerical data
        - detail instruction on how to create a sequential model 
            for tensorflow framework can be found at tensorflow_sequential_model.py
        '''
        self.model = model
        self.data_size = data_size
        self.qod = qod
        self.train_ds = train_ds
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

from abc import abstractmethod
from tensorflow.keras import Model

'''
- This abstract class is intended to help user on
    how to create their own tensorflow sequential model
    that can run on our flatform
    you can also create your tensorflow model 
    in you own way

- sample of how to create a specific tensorflow sequential model 
    can be found at project_dir/training_process/client/Lenet.py
'''
class TensorflowSequentialModel(Model):
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
        '''
        - a sequential tensorflow model consists of multiple layers 
            each layer is an instance of class tensorflow.keras.layers.Layer
        - it can be the already defined layer as Dense, Flatten, Conv2D
            or a custom layered defined by user
        - input_features variable is the input for the first layer
        - output_features variable is the output of the last layer
        - a non return function
        '''
        pass

    @abstractmethod
    def call(self, x):
        '''
        - must return x
        - define the order of layers in which we pass the input feature (x) 
            from the first layer toward the last one
        '''
        pass
    

    @abstractmethod
    def create_loss_object(self):
        '''
        - must return a loss object
        - several loss objects can be found in tf.keras.losses 
            or can be a customized one
        - below is how to use Categorical Crossentropy loss object defined by tensorflow
            self.loss_object = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
        '''
        pass 
    
    @abstractmethod
    def create_optimizer(self):
        '''
        - must return an optimizer object
        - optimizers in tf.keras.optimizers
            or define a personalized one
        - below is how to use Adam optimizer defined by tensorflow
            self.optimizer = tf.keras.optimizers.Adam()
        '''
        pass

    @abstractmethod
    def create_train_metric(self):
        '''
        - must return a train_performance object 
            and a train_loss object correspondingly 
        - metric in tf.keras.metrics
            or can be self defined
        - below is how to use Mean loss and Categorical Accuracy object provided by tensorflow
            self.train_loss = tf.keras.metrics.Mean(name='train_loss')
            self.train_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy')
        '''
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


from tensorflow.keras.layers import Dense, Flatten, Conv2D, AveragePooling2D


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


# ------------oOo--------------------
# Preprocessing data
# mnist dataset
# Set the file paths for the MNIST digit dataset files
train_images_path = os.path.join(root, os.getenv("x_train_path"))
train_labels_path = os.path.join(root, os.getenv("y_train_path"))
test_images_path = os.path.join(root, os.getenv("x_test_path"))
test_labels_path = os.path.join(root, os.getenv("y_test_path"))


batch_size = 128

# preprocessing data to be ready for low level tensorflow training process
data_preprocessing = TensorflowImageDataPreprocessing(train_images_path=train_images_path, train_labels_path=train_labels_path, 
                                                      height = 28, width = 28, batch_size= batch_size, split=True, fract=0.2,
                                                      evaluate_images_path=test_images_path, evaluate_labels_path=test_labels_path)
# define dataset
train_ds = data_preprocessing.train_ds
test_ds = data_preprocessing.test_ds
evaluate_ds = data_preprocessing.evaluate_ds
# ------------oOo--------------------



# define model
lenet = LeNet(input_features = (32, 32, 1), output_features = 10)
# define framework
model = TensorflowFramework(model = lenet, data_size= 10000, qod= 0.5, train_ds= train_ds, test_ds= test_ds)


EPOCHS = 5
tf.debugging.set_log_device_placement(True)


print("*" * 10)
print(tf.test.is_built_with_cuda())
print("*" * 10)

tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[0], 'GPU')


for epoch in range(EPOCHS):
  for images, labels in train_ds:
    train_acc, train_loss = model.fit(images, labels)

  for test_images, test_labels in test_ds:
    test_acc, test_loss = model.evaluate(test_images, test_labels)

  print(
    f'Epoch {epoch + 1}, '
    # f'Loss: {model.train_loss.result()}, '
    f'Train Accuracy: {train_acc * 100}, '
    f'Train Loss: {train_loss}, '
    f'Test Accuracy: {test_acc * 100}'
    f'Test Loss: {test_loss}, '
  )