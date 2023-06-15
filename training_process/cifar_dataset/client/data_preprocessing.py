
import tensorflow as tf
import numpy as np

import pickle


class TensorflowImageDataPreprocessing():
    def __init__(self, train_dataset_path: str, height: int = 32, width: int = 32, batch_size: int = 128, shuffle_time = 100, fract = 0.1):
        self.train_ds = None
        self.test_ds = None
        self.evaluate_ds = None
        self.height = height
        self. width = width

        self.load_training_dataset(train_dataset_path, batch_size, shuffle_time, fract = fract)


    def load_training_dataset(self, train_images_path: str, batch_size: int = 128, shuffle_time: int = 100, split: bool = True, fract: float = 0.1):
        # Load the MNIST digit dataset files into numpy arrays
        with open(train_images_path, "rb") as f:
            dataset = pickle.load()
        
        x = []
        y = []

        for sample in dataset:
            label = sample[-1]
            image = sample[: -1]
            x.append(image)
            y.append(label)

        x = np.array(x)
        y = np.array(y)


        x = x / 255    
        y = y.reshape(-1)
        # shape of x and y now: ((size, 32, 32, 3), (size,))
        # already be ready for the training process
        

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

