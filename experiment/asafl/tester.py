import torchvision
from torchvision import datasets, transforms
from load_splited_data import load_to_numpy_array, cifar_10_load_asyn2f
import os

chunk_folder = "non_iid"
chunk_filename = f"chunk_{1}.pickle"
training_dataset_path = os.path.join(chunk_folder, chunk_filename)
x_train,y_train = load_to_numpy_array(training_dataset_path)
print(x_train.shape)
# train_loader.append(cifar_10_load_asyn2f(training_dataset_path))

test_dataset = torchvision.datasets.CIFAR10(root='./cifar10', train=False,transform=transforms.ToTensor())
print(test_dataset.data.shape)

train_dataset = cifar_10_load_asyn2f(training_dataset_path)

# print(train_dataset.dataset)
dataiter = iter(train_dataset)
images, labels = dataiter.next()
print(images.shape)