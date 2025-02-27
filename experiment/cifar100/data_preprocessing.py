
import tensorflow as tf
import numpy as np
import pickle
import requests
from bs4 import BeautifulSoup
import csv



def one_hot(train_labels, num_classes, dtype=np.float32):
    """Create a one-hot encoding of labels of size num_classes."""
    return np.array(train_labels == np.arange(num_classes), dtype)


def normalize(images):
    """Normalize data with mean and std."""
    mean = np.array([0.49139968, 0.48215841, 0.4465309])
    std = np.array([0.24703223, 0.24348513, 0.26158784])
    return (images - mean) / std


def augment(images, labels):
    padding = 4
    image_size = 32
    target_size = image_size + padding * 2

    images = tf.image.pad_to_bounding_box(images, padding, padding, target_size, target_size)
    images = tf.image.random_crop(images, (image_size, image_size, 3))
    images = tf.image.random_flip_left_right(images)
    return images, labels



def training_dataset_generator(images, labels, batch_size):
    ds = tf.data.Dataset.from_tensor_slices((images, labels))
    ds = ds.map(augment, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    ds = ds.shuffle(len(images)).batch(batch_size)
    ds = ds.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    return ds


def load_to_numpy_array(dataset_path: str, height: int = 32, width: int = 32, channels: int = 3):
 # Load the MNIST digit dataset files into numpy arrays
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


def preprocess_dataset(dataset_path: str, height: int = 32, width: int = 32, 
                          channels: int = 3, num_classes: int =  100,
                          batch_size: int = 128, training = True):
   
    x, y = load_to_numpy_array(dataset_path, height, width, channels)
    data_size = len(x)

    # scale pixel value to be within 0 and 1
    x = x / 255   
    # one hot encoding for y
    y = one_hot(train_labels= y, num_classes = num_classes)
    # shape of x and y now: ((size, 32, 32, 3), (size,))
    # already be ready for the training process
    # perform normalize for x
    x = normalize(x)
    if training:
        # create ready datasets for training process
        # applying augmentation technique
        ds = training_dataset_generator(x, y, batch_size)
    else:
        # create testing data set
        ds = tf.data.Dataset.from_tensor_slices((x, y)).\
            batch(batch_size).prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    return ds, data_size



def download_file_from_google_drive(file_id: str, destination: str):
    """
    Download file from Google Drive using the shared link.
    
    Parameters:
    - url: The shared link URL of the Google Drive file.
    - destination: Path to save the downloaded file.
    """
    session = requests.Session()
    base_url = "https://drive.google.com/uc?export=download"

    response = session.get(base_url, params={'id': file_id}, stream=True)
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find("form", {"id": "download-form"})
    if not form:
        print("Error: Unable to find the download form. The file may not be public.")
        return

    form_action = form.get("action")
    if not form_action.startswith("http"):
        form_action = "https://drive.usercontent.google.com" + form_action

    payload = {}
    for input_tag in form.find_all("input"):
        name = input_tag.get("name")
        value = input_tag.get("value", "")
        if name:
            payload[name] = value

    response = session.get(form_action, params=payload, stream=True)
    if 'text/html' in response.headers.get('Content-Type', ''):
        return 
    with open(destination, "wb") as f:
        for chunk in response.iter_content(32768):
            if chunk:
                f.write(chunk)

def get_file_id_in_csv(file_name, row_num):
    with open(file_name, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        next(csvreader)  # Skip the header row
        for i, row in enumerate(csvreader):
            if i == row_num:
                return row[1]
