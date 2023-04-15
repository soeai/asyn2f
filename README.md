# AsynFL
We develop an asynchronous federated learning framework ...

Link to AsynFed Diagrams.
```
https://drive.google.com/file/d/1LjL_asVqIZiBMvmlhExUakEMqmKHsQMr/view?usp=sharing
```

## Prerequisites
- Python 3.9
- Docker

## Setting up the development environment
1. Run the following command to start MinIO and RabbitMQ
```
docker-compose up -d
```
2. Install dependencies 
```
pip3 install -r requirements.txt
```
3. Install `mc` for working with MinIO (https://min.io/docs/minio/linux/reference/minio-mc.html). After installing `mc`, run the following command to configure it:
```
mc alias set minio http://localhost:9000 minioadmin minioadmin
```


