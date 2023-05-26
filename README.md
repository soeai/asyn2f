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
- Install dependencies
```
python3 setup.py install
```

## Run as server
- create .env file in the root dir of the process following the guide in .env_template for appropriate usage
- direct to dir training_process/server
```
cd training_process/server
```
- in the python file run_server, define Config.QUEUE_URL to be the url of your remote (or local) rabbitMQ server
- Choose your prefer aggregated strategy and specify the params. Strategies can be found at asynfed/server/strategies 
- run the file
```
python3 run_server.py
```

## Run as client
- create .env file in the root dir of the process following the guide in .env_template for appropriate usage
- direct to dir training_process/client
```
cd training_process/client
```
- in the python file run_client, define Config.QUEUE_URL to be the url of your remote (or local) rabbitMQ server
- then, define Config.TRAINING_EXCHANGE (or you can parse it using --training_exchange argument when running the run_client py)
- choose your prefer training algorithm, platform provided strategies can be found at the folder asynfed/client/algorithms
- define your own model to be trained in our platform. Sample and instructions are included in asyncfed/client/frameworks folder, you can see how we define a tensorflow model in the folder tensorflow within this directory
- after that, your model are ready to be trained
```
python3 run_client.py
```

## run client docker file
- must create .env file within the same folder as docker-compose file (or modify the docker-compose to define the location of the .env file)
- in the .env file, define at least profile_path and the profile.json must be created before runtime 
