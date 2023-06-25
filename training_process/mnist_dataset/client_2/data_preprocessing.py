
import tensorflow as tf
import numpy as np
import gzip

def preprocess_dataset(images_path: str, labels_path: str,
                       height: int = 28, width: int = 28, shuffle_time = 1000,
                          batch_size: int = 128, training = True):
    
    # Load the MNIST digit dataset files into numpy arrays
    with gzip.open(images_path, 'rb') as f:
        x = np.frombuffer(f.read(), np.uint8, offset=16).reshape(-1, height, width)

    with gzip.open(labels_path, 'rb') as f:
        y = np.frombuffer(f.read(), np.uint8, offset=8)
    x = x / 255    
    # shape of x and y now: ((size, 28, 28), (size,))
    # Add a channels dimension
    x = x[..., tf.newaxis].astype("float32")
    # shape of x and y now: ((size, 28, 28, 1), (size,))

    # make it to be a smaller dataset
    # Take a portion of the whole dataset as a way to simulate various data owner behavior
    start = 0
    datasize = 1000
    x = x[start: start + datasize]
    y = y[start: start + datasize]

    data_size = len(x)
    # create ready datasets for training process
    # train_ds and test_ds type: tensorflow.python.data.ops.batch_op._BatchDataset
    if training:
        ds = tf.data.Dataset.from_tensor_slices((x, y)).shuffle(shuffle_time).batch(batch_size)
    else:
        ds = tf.data.Dataset.from_tensor_slices((x, y)).shuffle(shuffle_time).batch(len(x))

    return ds, data_size
