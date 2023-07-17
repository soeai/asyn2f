import os
import sys
import argparse

# run locally without install asynfed package
# root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)


# tensorflow 
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from resnet18 import Resnet18
from utils import *


# Create an argument parser
parser = argparse.ArgumentParser()
# Add arguments
parser.add_argument('--batch_size', dest='batch_size', type=int, help='specify the batch_size of the training process')
parser.add_argument('--epoch', dest='epoch', type=int, help='specify the epoch of the training process')
parser.add_argument('--patience', dest='patience', type=int, help='specify the patience step in early stopping of the training process')
parser.add_argument('--gpu_index', dest='gpu_index', type=int, help='specify the gpu uses of the training process')
# Parse the arguments
args = parser.parse_args()

print("*" * 20)
if args.gpu_index is not None:
   print(f"config gpu_index: {args.gpu_index}")
   gpu_index = args.gpu_index
else:
   print("no gpu index set, set default as 0")
   gpu_index = 0
print("*" * 20)

print("*" * 20)
print("*" * 20)
if tf.config.list_physical_devices('GPU'):
    tf.config.set_visible_devices(tf.config.list_physical_devices('GPU')[gpu_index], 'GPU')
    print("config tensorflow using gpu successfully")
else:
    print("There is no gpu or your tensorflow is not built in with gpu support")
print("*" * 20)
print("*" * 20)


print("*" * 20)
if args.batch_size:
   print(f"config batch_size: {args.batch_size}")
   batch_size = args.batch_size
else:
  print("no batch_size set, set default as 128")
  batch_size = 128

if args.epoch:
   print(f"config epoch: {args.epoch}")
   epoch = args.epoch
else:
  print("no epoch set, set default as 200")
  epoch = 200

if args.patience:
   print(f"config patience: {args.patience}")
   patience = args.patience
else:
  print("no patience set, set default as 2000")
  patience = 2000
print("*" * 20)


print('==> Preparing data...')
train_images, train_labels, test_images, test_labels = get_dataset()
data_size = len(train_images)

mean, std = get_mean_and_std(train_images)
train_images = normalize(train_images, mean, std)
test_images = normalize(test_images, mean, std)

train_ds = dataset_generator(train_images, train_labels, batch_size)
test_ds = tf.data.Dataset.from_tensor_slices((test_images, test_labels)).\
        batch(batch_size).prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

# define model
model = Resnet18(input_features = (32, 32, 3), output_features = 10, lr=1e-1, decay_steps=int(epoch * data_size / batch_size))
# define framework
tensorflow_framework = TensorflowFramework(model = model, epoch= 200, data_size= data_size, train_ds= train_ds, test_ds= test_ds, regularization='l2', delta_time= 10000, qod= 0.45)


# Initialize variables for early stopping check
best_val_loss = float("inf")
# Number of epochs to wait before stopping training when performance worsens
# already set patience above
waiting = 0
# training with 200 epoch or early stopping
print("*" * 20)
print("*" * 20)
print(f"Training for the total number of epoch {epoch} with batch_size {batch_size} for datasize of {data_size}")
print("*" * 20)
print("*" * 20)
for epoch in range(epoch):
    tensorflow_framework.model.train_loss.reset_states()
    tensorflow_framework.model.train_performance.reset_states()
    tensorflow_framework.model.test_loss.reset_states()
    tensorflow_framework.model.test_performance.reset_states()

    for images, labels in tensorflow_framework.train_ds:
        train_acc, train_loss= tensorflow_framework.fit(images, labels)

    for test_images, test_labels in tensorflow_framework.test_ds:
        test_acc, test_loss = tensorflow_framework.evaluate(test_images, test_labels)

    print("Epoch {} - Train Acc: {:.2f} -- Train Loss {} Test Acc {:.2f}  Test Loss {}".format(epoch+1,
                                                                                       train_acc * 100,
                                                                                       train_loss,
                                                                                       test_acc * 100,
                                                                                       test_loss))
    
    # After each epoch, check the validation loss
    if test_loss < best_val_loss:
        best_val_loss = test_loss
        waiting = 0
    else:
        waiting += 1

    if waiting >= patience:
        print("Early stopping triggered - ending training.")
        break


# save weights
save_location = "weights.pkl"
weights = model.get_weights()
with open(save_location, 'wb') as f:
    import pickle
    pickle.dump(weights, f)