# -*- coding: utf-8 -*-
"""
Created on Fri Apr  9 21:31:56 2021

@author: Administrator
"""
#!/usr/bin/python
# -*- coding: UTF-8 -*-

from threading import Thread
from torch.autograd import Variable
import torch
import matplotlib.pyplot as plt
import torch.nn as nn
from torch import optim
from torch.nn import init
import torch.nn.functional as F
import torchvision
from torchvision import datasets, transforms
import glob,os
import numpy as np
import pandas as pd
from torch.utils.data import Dataset,DataLoader,TensorDataset
from sklearn.model_selection import StratifiedShuffleSplit
#from resnet import ResNet18
from torchvision.datasets import CIFAR10
import pickle as p

batch_size = 128
EPOCH=10
BATCH_SIZE=50
LR=0.01
DOWNLOAD_MNIST = True


def data_reader(file):
    df = pd.read_csv(file,index_col=None,encoding='utf-8')
    df = np.array(df)
    

    df = df[1:]
    Y_train=df[:,-1]
    X = df[:,:-2]
    data_size = X.shape[0]
    X = X.reshape(data_size,28,28)
    X=np.expand_dims(X,axis=1)
    X = X.astype(float)
    Y_train = Y_train.astype(int)
    print('data shape is',X.shape)
    
    x_train = torch.from_numpy(X)
    y_train = torch.from_numpy(Y_train)


    x_train = x_train.float()
    #x_train = x_train/255
    y_train = y_train.long()
    
    train_dataset = TensorDataset(x_train,y_train)
    train_loader = torch.utils.data.DataLoader(dataset=train_dataset,batch_size=batch_size,shuffle=True)
    return train_loader

def data_reader1(file):
    df = pd.read_csv(file,index_col=None,encoding='utf-8')
    df = np.array(df)
    

    df = df[1:]
    Y_train=df[:,-1]
    X = df[:,:-2]
    data_size = X.shape[0]
    X = X.reshape(data_size,28,28)
    X=np.expand_dims(X,axis=1)
    X = X.astype(float)
    Y_train = Y_train.astype(int)
    print('data shape is',X.shape)
    
    #test_file = glob.glob(os.path.join('/home/wu_server/zwd/HAFL_code/data/fashion_csv', "fashion_mnist_test.csv"))
    test_df = pd.read_csv("./fashion_csv/test.csv")
    test_df = np.array(df)
    test_data = test_df[1:]
    test_x = test_data[:,:-2]
    test_y = test_data[:,-1]
    test_data_size = test_x.shape[0]
    test_x = test_x.reshape(test_data_size,28,28)
    test_x = np.expand_dims(test_x,axis=1)
    test_x = test_x.astype(float)
    test_y = test_y.astype(int)
    
    sss=StratifiedShuffleSplit(n_splits=3,test_size=0.3,random_state=10)
    sss.get_n_splits(df,Y_train)
    for train_index,test_index in sss.split(X,Y_train):
        X_train,X_test = X[train_index],X[test_index]
        y_train,y_test = Y_train[train_index],Y_train[test_index]
       
    x_train = torch.from_numpy(X_train)
    #x_train = x_train
    y_train = torch.from_numpy(y_train)
    
    x_test = torch.from_numpy(test_x)
    y_test = torch.from_numpy(test_y)

    x_train = x_train.float()
    x_test = x_train.float()
    y_train = y_train.long()
    y_test = y_train.long()
    
    train_dataset = TensorDataset(x_train,y_train)
    test_dataset = TensorDataset(x_test,y_test)
    train_loader = torch.utils.data.DataLoader(dataset=train_dataset,batch_size=batch_size,shuffle=True)
    test_loader = torch.utils.data.DataLoader(dataset=test_dataset,batch_size=batch_size,shuffle=False)
    return train_loader,test_loader

############################################################################################################################################################################
def load_CIFAR_batch(filename):
    with open(filename,'rb')as f:
        datadict=p.load(f,encoding='latin1')
        x=datadict['data']
        y=datadict['labels']
        x=x.reshape(10000,3,32,32)
        y=np.array(y)
        return x,y
    
def cifar_10_load(file):
    x_train,y_train = load_CIFAR_batch(file)
    
    x_train=torch.from_numpy(x_train)
    y_train=torch.from_numpy(y_train)
    x_train = x_train.type(torch.FloatTensor)/255.
    y_train = y_train.long()
    train_dataset = TensorDataset(x_train,y_train)
    train_loader = torch.utils.data.DataLoader(dataset=train_dataset,batch_size=BATCH_SIZE,shuffle=True)
    #test_dataset = torchvision.datasets.CIFAR10(root='./cifar10/', train=False, transform=torchvision.transforms.ToTensor())
    #test_loader = torch.utils.data.DataLoader(dataset=test_dataset,batch_size=BATCH_SIZE,shuffle=False)
    return train_loader

    #return train_loader,test_loader

############################################################################################################################################################
def SVHN_load():
    train_dataset = torchvision.datasets.SVHN(root='./SVHN',split='train',download=False,transform=torchvision.transforms.ToTensor())
    test_dataset = torchvision.datasets.SVHN(root='./SVHN',split='test',download=False,transform=torchvision.transforms.ToTensor())
    train_loader = Data.DataLoader(dataset=train_dataset,shuffle=True,batch_size=Batch_size)
    test_loader = Data.DataLoader(dataset=test_dataset,shuffle=True,batch_size=Batch_size)
    
    return train_loader,test_loader 

#svhn_train,svhn_test = SVHN_load()
    
##################################################################################################################################################################
def fashion_mnist_read(file):
    transform = transforms.Compose([transforms.ToTensor(),transforms.Normalize((0.1307),(0.3081))])
    batch_size = 64
    #train_dataset = torchvision.datasets.MNIST(root='./data',train=True,transform=transforms.ToTensor(),download=True)
    #test_dataset = torchvision.datasets.MNIST(root='./data',train=False,transform=transforms.ToTensor())
    train_dataset = torchvision.datasets.FashionMNIST(root=file,train=True,download=False,transform=transform)
    test_dataset = torchvision.datasets.FashionMNIST(root=file,train=False,download=False,transform=transform)

    train_loader = torch.utils.data.DataLoader(dataset=train_dataset,batch_size=batch_size,shuffle=True)
    test_loader = torch.utils.data.DataLoader(dataset=test_dataset,batch_size=batch_size,shuffle=False)
    return train_loader,test_loader
################################################################################################################################################################
batch_size = 64
#train_loader, dataset_label, dataset_label_client, train_dataset_client = [], [], [], []
class Widar_Dataset(Dataset):
    def __init__(self,root_dir):
        self.root_dir = root_dir
        self.data_list = glob.glob(root_dir+'/*/*.csv')
        self.folder = glob.glob(root_dir+'/*/')
        self.category = {self.folder[i].split('/')[-2]:i for i in range(len(self.folder))}
        
    def __len__(self):
        return len(self.data_list)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
            
        sample_dir = self.data_list[idx]
        y = self.category[sample_dir.split('/')[-2]]
        x = np.genfromtxt(sample_dir, delimiter=',')
        
        # normalize
        x = (x - 0.0025)/0.0119
        
        # reshape: 22,400 -> 22,20,20
        x = x.reshape(22,20,20)
        # interpolate from 20x20 to 32x32
        # x = self.reshape(x)
        x = torch.FloatTensor(x)

        return x,y