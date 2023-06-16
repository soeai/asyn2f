
import tensorflow as tf
import numpy as np

import pickle



def load_training_dataset(train_dataset_path: str, height: int = 32, width: int = 32, channels: int = 3, batch_size: int = 128, shuffle_time: int = 100, fract: float = 0.1):
    # Load the MNIST digit dataset files into numpy arrays
    with open(train_dataset_path, "rb") as f:
        dataset = pickle.load(f)
    
    x = []
    y = []

    for sample in dataset:
        label = sample[-1]
        image = sample[: -1]
        # x = x.reshape(width, height, channels) 
        x.append(image.reshape(width, height, channels))
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
    train_ds = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(shuffle_time).batch(batch_size)
    test_ds = tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(batch_size)
    return train_ds, test_ds

