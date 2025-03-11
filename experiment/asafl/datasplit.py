#!/usr/bin/python
# -*- coding: UTF-8 -*-
import copy 
import math
import csv
import random
from torch.autograd import Variable
import torch
import torch.nn as nn
from torch import optim
from torch.autograd._functions import tensor
from torch.nn import init
import torch.nn.functional as F
import torchvision
from torchvision import datasets, transforms
import numpy as np

def dirichlet_split_noniid(train_labels, alpha, n_clients):
    '''
    The Dirichlet distribution with parameter alpha divides the data index into subsets of n_clients
    '''
    n_classes = train_labels.max()+1
    #print("alpha=",[alpha]*n_clients)
    label_distribution = np.random.dirichlet([alpha]*n_clients, n_classes)
    # The category label distribution matrix X of (K, N) records how much each client occupies in each category.

    class_idcs = [np.argwhere(train_labels==y).flatten() 
           for y in range(n_classes)]
    # Record the sample index corresponding to each K category

    client_idcs = [[] for _ in range(n_clients)]
    #Record the indexes of N clients corresponding to the sample collection.
    for c, fracs in zip(class_idcs, label_distribution):
        # np.split divides the samples of category k into N subsets according to the proportion
        # for i, idcs is the index of traversing the sample collection corresponding to the i-th client
        for i, idcs in enumerate(np.split(c, (np.cumsum(fracs)[:-1]*len(c)).astype(int))):
            client_idcs[i] += [idcs]

    client_idcs = [np.concatenate(idcs) for idcs in client_idcs]
    return client_idcs
