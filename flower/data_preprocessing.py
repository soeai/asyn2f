
import tensorflow as tf
import numpy as np
import pickle
from keras.preprocessing.image import ImageDataGenerator

def load_to_numpy_array(dataset_path: str, height: int = 32, width: int = 32, channels: int = 3):
 # Load the cifar digit dataset files into numpy arrays
    with open(dataset_path, "rb") as f:
        dataset = pickle.load(f)
    
    x = []
    y = []

    for sample in dataset:
        label = sample[-1]
        image = sample[: -1]
        # x = x.reshape(width, height, channels) 
        x.append(image.reshape(width, height, channels))
        y.append([label])

    x = np.array(x)
    y = np.array(y)
    return x, y


def preprocess_dataset(dataset_path):
    x, y = load_to_numpy_array(dataset_path= dataset_path)
    x = x / 255
    data_size = len(x)
    y = tf.keras.utils.to_categorical(y, 10)

    return x, y, data_size

def get_datagen():
    def custom_preprocessing(images):
        padding = 4
        image_size = 32
        target_size = image_size + padding * 2

        images = tf.image.pad_to_bounding_box(images, padding, padding, target_size, target_size)
        images = tf.image.random_crop(images, (image_size, image_size, 3))
        
        return images

    # Create an ImageDataGenerator with the custom_preprocessing function
    datagen = ImageDataGenerator(preprocessing_function=custom_preprocessing,
                                horizontal_flip=True)

    return datagen
