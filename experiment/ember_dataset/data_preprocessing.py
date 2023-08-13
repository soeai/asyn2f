import numpy as np
import pickle
import tensorflow as tf


import requests
from bs4 import BeautifulSoup


import csv


class DataLoader:
    def __init__(self, path, batch_size=128):
        self.path = path
        self.batch_size = batch_size    # <-- Define batch_size here
        self.X, self.y = self.load_data()
        self.indices = np.arange(len(self.X))

    def load_data(self):
        with open(self.path, "rb") as f:
            dataset = pickle.load(f)
        X = dataset[:, :-1]
        y = dataset[:, -1]
        return X, y

    def data_generator(self):
        np.random.shuffle(self.indices)
        num_batches = len(self.X) // self.batch_size
        for batch_num in range(num_batches):
            start_index = batch_num * self.batch_size
            end_index = (batch_num + 1) * self.batch_size
            batch_indices = self.indices[start_index:end_index]
            X_batch = self.X[batch_indices]
            y_batch = self.y[batch_indices]
            yield X_batch, y_batch

        # Handle remaining data
        if len(self.X) % self.batch_size != 0:
            batch_indices = self.indices[num_batches * self.batch_size:]
            X_batch = self.X[batch_indices]
            y_batch = self.y[batch_indices]
            yield X_batch, y_batch

    def get_dataset_size(self) -> int:
        return len(self.X)

    def get_class_weight(self) -> list:
      # calculate class weight for imbalanced dataset
      unique, counts = np.unique(self.y, return_counts=True)
      total_samples = len(self.y)
      class_frequencies = counts / total_samples

      class_weight = [1/class_frequencies[0], 1/class_frequencies[1]]

      return class_weight

    def get_num_input_features(self) -> int:
      return self.X.shape[1]


    def create_tensorflow_dataset(self):
        # Convert the generator to TensorFlow dataset
        dataset = tf.data.Dataset.from_generator(
            self.data_generator,
            output_signature=(
                tf.TensorSpec(shape=(None, self.X.shape[1]), dtype=tf.float32),
                tf.TensorSpec(shape=(None,), dtype=tf.float32)
            )
        )
        dataset = dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
        return dataset


def download_file_from_google_drive(file_id: str, destination: str):
    """
    Download file from Google Drive using the shared link.
    
    Parameters:
    - url: The shared link URL of the Google Drive file.
    - destination: Path to save the downloaded file.
    """

    download_prefix = "https://drive.google.com/uc?export=download"
    url = f"{download_prefix}&id={file_id}"
    session = requests.Session()
    response = session.get(url, stream=True)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract necessary parameters from the page
    form_action = soup.find("form", {"id": "download-form"}).get("action")
    confirm_token = form_action.split("confirm=")[1].split("&")[0]

    # Perform POST request to download the file
    response = session.post(form_action, data={'confirm': confirm_token}, stream=True)

    # Save the content to the destination file
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

