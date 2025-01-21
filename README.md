# Asyn2F
We develop an asynchronous federated learning framework, named Asyn2F, with bidirectional model aggregation. 
By bidirectional model aggregation, on one hand, allows the server to asynchronously aggregate multiple local models and generate a new global model. 
On the other hand, it allows the training workers to aggregate the new version of the global model into the local model, which is being trained even in the middle of a training epoch. 
We develop Asyn2F considering the practical implementation requirements such as using cloud services for model storage and message queuing protocols for communications.

Link to Asyn2F Diagrams.
```
https://drive.google.com/file/d/1LjL_asVqIZiBMvmlhExUakEMqmKHsQMr/view?usp=sharing
```

## Prerequisites
- Python 3.9
- Docker
- Tensorflow 2.x

## Setting up the development environment
- Install dependencies
```
python3 setup.py install
```

