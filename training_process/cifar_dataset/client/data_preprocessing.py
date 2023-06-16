
import tensorflow as tf
import tensorflow_addons as tfa

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
    test_ds = tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(len(x_test))
    return train_ds, test_ds, datasize


# aug = ImageDataGenerator(
#     rotation_range=20, 
#     zoom_range=0.15, 
#     width_shift_range=0.2, 
#     height_shift_range=0.2, 
#     shear_range=0.15,
#     horizontal_flip=True, 
#     fill_mode="nearest")
 
def augment(image, label):
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_flip_up_down(image)
    
    image = tf.image.random_brightness(image, max_delta=0.15) # Random brightness
    image = tf.image.random_contrast(image, lower=0.85, upper=1.15) # Random contrast

    # To add rotation, TensorFlow Addons (tfa) library can be used.
    # Here's how to perform a random rotation:
    image = tfa.image.rotate(image, 
                             tf.random.uniform(shape=[], minval=-0.33, maxval=0.33),
                             fill_mode='nearest')
    
    # Shear transformation is not directly available in TensorFlow. If needed, it can be 
    # implemented using other transformations (like affine_transform), but it may not be straightforward.
    # The rest of the transformations like zoom and shift can be performed with affine transformations, 
    # but require more complex code to handle.

    return image, label


def generate_augmented_data(tensor_ds, batch_size: int, augmentations_per_image: int = 10):
    augmented_images = []
    augmented_labels = []

    for images, labels in tensor_ds:
        for _ in range(augmentations_per_image):
            for image, label in zip(images, labels):
                augmented_image, _ = augment(image, None)
                augmented_images.append(augmented_image)
                augmented_labels.append(label)

    # Drop the last batch if it's smaller than the batch size.
    total_batches = len(augmented_images) // batch_size
    augmented_images = augmented_images[:total_batches * batch_size]
    augmented_labels = augmented_labels[:total_batches * batch_size]

    # print(len(augmented_image), len(augmented_labels))

    return tf.data.Dataset.from_tensor_slices((augmented_images, augmented_labels)).batch(batch_size)



