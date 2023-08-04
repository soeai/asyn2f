import numpy as np
import tensorflow as tf

import pickle 

def load_data(path):
    with open(path, "rb") as f:
        dataset = pickle.load(f)
    X = dataset[:, :-1]
    y = dataset[:, -1]
    return X, y

# Assume X and y are your features and labels, loaded as NumPy arrays
# X shape: (num_samples, num_features)
# y shape: (num_samples,)

# Ensure y has the right shape
# y = y.reshape(-1, 1)

# Create TensorFlow dataset
def create_dataset(X, y, batch_size=128):
    ds = tf.data.Dataset.from_tensor_slices((X, y))
    ds = ds.shuffle(len(X)).batch(batch_size)
    ds = ds.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    return ds

# # Example usage
# train_ds = create_dataset(X_train, y_train)
# test_ds = create_dataset(X_test, y_test)
