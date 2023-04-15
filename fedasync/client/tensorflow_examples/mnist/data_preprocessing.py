
import tensorflow as tf
import numpy as np
import gzip

# Set the file paths for the MNIST digit dataset files
train_images_path = './mnist_data/train-images-idx3-ubyte.gz'
train_labels_path = './mnist_data/train-labels-idx1-ubyte.gz'
test_images_path = './mnist_data/t10k-images-idx3-ubyte.gz'
test_labels_path = './mnist_data/t10k-labels-idx1-ubyte.gz'



class TensorflowDataPreprocessing():
    def __init__(self, train_images_path, train_labels_path, batch_size = 32, shuffle_time = 10000, split = True, fract = 0.1, evaluate_images_path = None, evaluate_labels_path = None):
        self.train_ds = None
        self.test_ds = None
        self.evaluate_ds = None

        self.load_training_dataset(train_images_path, train_labels_path, batch_size, shuffle_time, split, fract = fract)
        if evaluate_images_path != None and evaluate_labels_path != None:
            self.load_evaluate_dataset(evaluate_images_path, evaluate_labels_path, batch_size)

    def load_training_dataset(self, train_images_path: str, train_labels_path: str, batch_size: int, shuffle_time: int, split: bool, fract):
        # Load the MNIST digit dataset files into numpy arrays
        with gzip.open(train_images_path, 'rb') as f:
            x = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, 28, 28)
        with gzip.open(train_labels_path, 'rb') as f:
            y = np.frombuffer(f.read(), np.uint8, offset=8)
        x = x / 255    
        # shape of x and y now: ((size, 28, 28), (size,))
        # Add a channels dimension
        x = x[..., tf.newaxis].astype("float32")
        # shape of x and y now: ((size, 28, 28, 1), (size,))

        # make it to be a smaller dataset
        # Take a portion of the whole dataset as a way to simulate various data owner behavior
        start = 0
        datasize = 10000
        x = x[start: start + datasize]
        y = y[start: start + datasize]
        
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
            x = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, 28, 28)
        with gzip.open(evaluate_labels_path, 'rb') as f:
            y = np.frombuffer(f.read(), np.uint8, offset=8)

        x = x / 255    
        # shape of x and y now: ((size, 28, 28), (size,))
        # Add a channels dimension
        x = x[..., tf.newaxis].astype("float32")
        # shape of x and y now: ((size, 28, 28, 1), (size,))
        self.evaluate_ds = tf.data.Dataset.from_tensor_slices((x, y)).batch(batch_size)


# data_preprocessing = TensorflowDataPreprocessing(train_images_path = train_images_path, train_labels_path= train_labels_path, batch_size= 64, split= True, fract= 0.2, evaluate_images_path= test_images_path, evaluate_labels_path= test_labels_path)
# print(type(data_preprocessing.train_ds))
# print(type(data_preprocessing.test_ds))
# print(type(data_preprocessing.evaluate_ds))



