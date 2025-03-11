# ASAFL

########### Abstract #############

Federated learning (FL) trains machine learning models using distributed user devices without exposing their data in Internet of Things (IoT). 
However, resource heterogeneity and data distribution variability among devices cause communication bottleneck, staleness and Non-IID issues in FL. 
We propose ASAFL, an Asynchronous Federated Learning with Adaptive Scheduling Strategy, to mitigate these challenges. 
Specifically, we quantify the potential contribution of client models relative to the server model and design a client upload strategy accordingly to reduce the uploading of redundant models with low contribution. Additionally, we propose a server model update method based on the contributions to address model divergence caused by staleness and Non-IID data.
Our theoretical analysis confirms ASAFL’s convergence, and experiments show it reduces communication overhead by over 70% compared to traditional asynchronous FL.




1、Requirement：
pytorch 1.12.0 and cuda 11.3 in ubuntu 20.04.
pip install copy,random,numpy


2、 Run
!run ASAFL.py
