import pickle
import numpy as np
import torch
from torch.utils.data import Dataset,DataLoader,TensorDataset
from torchvision import transforms
from torch.nn import functional as F
from bs4 import BeautifulSoup
import requests
import csv

class CifarDataset(Dataset):
    def __init__(self, dataset, transform):
        self.dataset = dataset
        self.transform=transform
        self.datasize = dataset[0].shape[0]

    def __len__(self):
        return self.datasize

    def __getitem__(self, index):
        return self.transform(self.dataset[0][index]), F.one_hot(torch.tensor(self.dataset[1][index][0]), num_classes = 10).to(torch.float)

class EmberDataset(Dataset):
    def __init__(self, dataset, transform=None):
        self.dataset = dataset
        self.transform=transform
        self.datasize = dataset[0].shape[0]

    def __len__(self):
        return self.datasize

    def __getitem__(self, index):
        return self.dataset[0][index], self.dataset[1][index]


def get_file_id_in_csv(file_name, row_num):
    with open(file_name, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        next(csvreader)  # Skip the header row
        for i, row in enumerate(csvreader):
            if i == row_num:
                return row[1]
            

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

def custom_encoder(X):
    # Empty array for the labels
    labels = np.zeros_like(X)

    # Handle the specific values 0 and 1
    labels[X == 0] = 2
    labels[X == 1] = 257

    # Handle the range (-inf, -2**12]
    labels[(X <= -2**12)] = 0

    # Handle the range (-2048, 0)
    labels[(X > -2**12) & (X < 0)] = 1

    # Handle the range [0, 1] (excluding the values 0 and 1 themselves since they've been handled above)
    mask_0_1 = (X > 0) & (X < 1)
    labels[mask_0_1] = 2 + np.floor(X[mask_0_1] * 255).astype(int)

    # Handle the range (1, 2**12]
    labels[(X > 1) & (X <= 2**12)] = 258

    # Handle the range (2**12, inf)
    labels[X > 2**12] = 259

    input_dim = 259 + 1 + 1

    return labels, input_dim


def cifar_10_load_asyn2f(file, BATCH_SIZE=128):
    x_train,y_train = load_to_numpy_array(file)
    # x_train=torch.from_numpy(x_train)
    y_train=torch.from_numpy(y_train)
    # x_train = x_train.type(torch.FloatTensor)/255.
    y_train = y_train.long()
    train_dataset = CifarDataset((x_train,y_train),transform=transforms.ToTensor())
    train_loader = DataLoader(dataset=train_dataset,batch_size=BATCH_SIZE,shuffle=True)
    return train_loader


def ember_load_asyn2f(file, BATCH_SIZE=128):
    with open(file, "rb") as f:
        dataset = pickle.load(f)
        x_train = dataset[:, :-1]
        y_train = dataset[:, -1].reshape(-1,1)
        x_train, _ = custom_encoder(x_train)
        x_train=torch.from_numpy(x_train)
        y_train=torch.from_numpy(y_train)
        y_train = y_train.float()
        train_dataset = EmberDataset((x_train,y_train))
        train_loader = DataLoader(dataset=train_dataset,batch_size=BATCH_SIZE,shuffle=True)
        return train_loader