# Introduction

In this work, we design and develop ASYN2F, an asynchronous federated learning framework. We propose a novel method for the server to aggregate the local models obtained from the workers and update the global model at a fine-grained level. Whenever a worker completes its local training and updates the server with the new local model, the server will immediately update the global model and notify other workers. The other workers will take the updated global model into the current training even if they are in the middle of a training epoch. This helps to avoid the obsolete information problem in which a local model trained by a worker may become obsolete for the server due to late submission


# General Framework Architecture

We aim to design our framework as generic as possible so that it can integrate any model aggregation strategies. The general architecture of ASYN2F is as follow:
![GitHub Logo](/images/asyn2f_architecture.png)


# Guide


# Experiments
# Datasets

We use Cifar10 dataset and split into 20 sub-datasets. Data is non-iid with small imbalanced of label. All sub-datasets and test dataset are then normalized by mean and standard deviation of 50K original train images.
![GitHub Logo](/images/cifar10_distribution.png)


# Publications
Tien-Dung Cao, Nguyen T. Vuong, Thai Q. Le, Hoang V.N. Dao, Tram Truong-Huu Senior Member, IEEE

