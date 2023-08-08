import os
import sys
import json

# run locally without install asynfed package
root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
# root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))))
sys.path.append(root)


# tensorflow 
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
from experiment.ember_dataset.ember_model import EmberModel
from data_preprocessing import *

import tensorflow as tf

with open('conf.json', 'r') as json_file:
    config = json.load(json_file)

data_folder = "/home/student02/thaile/working_with_ember_dataset/data"
i = 1
X, y= load_data(f'{data_folder}/chunk_{i}.pickle')
X_val, y_val = load_data(f'{data_folder}/test_set.pickle')
X = np.array(X)
y = np.array(y)
print('X shape:', X.shape, '-- y shape:', y.shape)
print('X val shape:', X_val.shape, '-- y val shape:', y_val.shape)

data_size = len(X)

train_ds = create_dataset(X, y)
test_ds = create_dataset(X_val, y_val)
        
epoch = 200
batch_size = 128

learning_rate_config = config.get('training_params').get('learning_rate_config', {}) 
if learning_rate_config == {}:
    learning_rate_config['fix_lr'] = False
    learning_rate_config['lr'] = 0.1
    learning_rate_config['decay_steps'] = data_size * epoch / batch_size

model = EmberModel(input_features= None, output_features= None, lr_config= learning_rate_config)
# Define framework

tensorflow_framework = TensorflowFramework(model=model,data_size=data_size, train_ds=train_ds, test_ds=test_ds, config=config)
for epoch in range(epoch):
    print(f"Enter epoch {epoch + 1}, learning rate = {tensorflow_framework.get_learning_rate()}")
    tensorflow_framework.model.train_loss.reset_states()
    tensorflow_framework.model.train_performance.reset_states()
    tensorflow_framework.model.test_loss.reset_states()
    tensorflow_framework.model.test_performance.reset_states()

    for images, labels in tensorflow_framework.train_ds:
         train_acc, train_loss= tensorflow_framework.fit(images, labels)
    for test_images, test_labels in tensorflow_framework.test_ds:
        test_acc, test_loss = tensorflow_framework.evaluate(test_images, test_labels)
    print("Epoch {} - Train Acc: {:.2f} -- Train Loss {} Test Acc {:.2f}  Test Loss {}".format(epoch+1,train_acc * 100,train_loss,test_acc * 100,test_loss))


